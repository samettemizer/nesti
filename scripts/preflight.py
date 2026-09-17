#!/usr/bin/env python3
"""
scripts/preflight.py – verify every external dependency before a live run.

Prints one line per check and exits non-zero on the first HARD failure, so a
live run is never started against a half-configured environment.  Checks are
ordered cheapest-first: configuration, then GitLab Issues, then the GitLab
repository, then the paid LLM call, then the local Docker/corpus state.

Usage:
    python scripts/preflight.py                 # everything
    python scripts/preflight.py --skip-llm      # no paid Anthropic call
    python scripts/preflight.py --skip-docker   # no Docker daemon needed
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

# scripts/ is sys.path[0] when run as a file; the project modules live one up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from dotenv import load_dotenv

load_dotenv()

import skill_catalog  # noqa: E402  (after load_dotenv, like the orchestrator)
from gitlab_issues_client import GitLabIssuesClient  # noqa: E402

_REQUEST_TIMEOUT = 15
_PLACEHOLDER_MARKERS = ("your_", "_here", "changeme", "xxx")

_REQUIRED_VARS = (
    "GITLAB_URL",
    "GITLAB_TOKEN",
    "GITLAB_PROJECT_PATH",
    "ANTHROPIC_API_KEY",
)

_SANDBOX_IMAGE_VARS = (
    ("DOCKER_SANDBOX_PHP_IMAGE", "nesti-sandbox-php"),
    ("DOCKER_SANDBOX_NODE_IMAGE", "nesti-sandbox-node"),
    ("DOCKER_SANDBOX_E2E_IMAGE", "nesti-sandbox-e2e"),
)

# GitLab access levels: 30 = Developer, the floor for pushing a branch.
_MIN_PUSH_ACCESS_LEVEL = 30

_failures = 0
_warnings = 0


def _ok(label: str, detail: str = "") -> None:
    print(f"  OK    {label}" + (f" – {detail}" if detail else ""))


def _warn(label: str, detail: str = "") -> None:
    global _warnings
    _warnings += 1
    print(f"  WARN  {label}" + (f" – {detail}" if detail else ""))


def _fail(label: str, detail: str = "") -> None:
    """Report a hard failure and abort: a live run must not start half-broken."""
    global _failures
    _failures += 1
    print(f"  FAIL  {label}" + (f" – {detail}" if detail else ""))
    print(f"\nPREFLIGHT FAILED at: {label}")
    sys.exit(1)


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def check_configuration() -> None:
    print("\n── Configuration ──")
    for name in _REQUIRED_VARS:
        value = os.environ.get(name, "")
        if not value.strip():
            _fail(f"{name} present", "missing from .env")
        if _is_placeholder(value):
            _fail(f"{name} configured", f"still a placeholder ({value[:24]!r})")
        shown = value if name.endswith(("URL", "PATH", "PROJECT_ID")) else f"set ({len(value)} chars)"
        _ok(name, shown)

    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        _ok("DEEPSEEK_API_KEY", "mid-tier coder available")
    else:
        _warn("DEEPSEEK_API_KEY", "absent – escalation jumps straight to Claude")



def check_issues() -> None:
    """
    Verify the GitLab Issues intake end to end.

    The lifecycle probe replaces the old Redmine workflow probe and exists for
    the same reason: a token that can read issues but not label or close them
    produces a run that looks healthy and then strands its issue.  The probe
    drives GitLabIssuesClient itself, so it exercises the exact code the
    orchestrator uses rather than a parallel re-implementation.
    """
    print("\n── GitLab Issues ──")
    client = GitLabIssuesClient()
    _ok("Opt-in label", f"{client.issue_label!r} (lock: {client.in_progress_label!r})")

    try:
        response = client.session.get(client._project_api, timeout=_REQUEST_TIMEOUT)
    except Exception as exc:  # pylint: disable=broad-except
        _fail("Project reachable", f"{type(exc).__name__}: {exc}")
    if response.status_code != 200:
        _fail("Project reachable", f"HTTP {response.status_code}")
    project = response.json()
    if not project.get("issues_enabled", False):
        _fail(
            "Issues enabled",
            f"the issue tracker is disabled on {client.project_path} "
            f"(issues_access_level={project.get('issues_access_level')!r}); "
            f"enable it in Settings → General → Visibility",
        )
    _ok("Issues enabled", f"access level {project.get('issues_access_level')}")

    try:
        pending = client.list_pending()
    except Exception as exc:  # pylint: disable=broad-except
        _fail("Pending queue readable", f"{type(exc).__name__}: {exc}")
    _ok(
        "Pending queue",
        f"{len(pending)} issue(s) waiting"
        + (f" (next: #{pending[0]['id']} {pending[0]['subject'][:40]})" if pending else ""),
    )

    _probe_issue_lifecycle(client)


def _probe_issue_lifecycle(client: GitLabIssuesClient) -> None:
    """Create a throwaway issue and drive it through the whole lifecycle."""
    created = client.session.post(
        f"{client._project_api}/issues",
        json={
            "title": "nesti preflight probe",
            "description": "Created by scripts/preflight.py to verify the issue "
                           "lifecycle. Safe to ignore; left closed.",
            "labels": client.issue_label,
        },
        timeout=_REQUEST_TIMEOUT,
    )
    if created.status_code not in (200, 201):
        _fail(
            "Issue creation",
            f"POST /issues → HTTP {created.status_code}: {created.text[:200]} — the "
            f"token needs at least Reporter rights on {client.project_path}",
        )
    probe = created.json()
    iid, web_url = probe["iid"], probe.get("web_url", "")
    _ok("Issue creation", f"probe issue #{iid}")

    if not client.lock_issue(iid):
        _fail("Lock (add ::in-progress label)",
              "the token cannot label issues; every run would fail to claim its issue")
    _ok("Lock (add ::in-progress label)", client.in_progress_label)

    # The failure path: without this a failed issue never returns to the queue.
    if not client.reopen_issue(iid, note="preflight: probing the failure path"):
        _fail("Unlock (back to pending)",
              "a failed issue could not be returned to the pending pool and would "
              "never be retried")
    _ok("Unlock (back to pending)", "lock label removed, issue still open")

    if not client.close_issue(iid, note="preflight: probing the success path"):
        _fail("Close (success path)",
              "a successful run could open its MR but never close the issue")
    _ok("Close (success path)", f"probe issue #{iid} left closed – {web_url}")


def check_gitlab() -> None:
    print("\n── GitLab ──")
    base = os.environ["GITLAB_URL"].rstrip("/")
    path = quote(os.environ["GITLAB_PROJECT_PATH"], safe="")
    url = f"{base}/api/v4/projects/{path}"
    session = requests.Session()
    session.headers.update({"PRIVATE-TOKEN": os.environ["GITLAB_TOKEN"]})
    session.verify = os.environ.get("GITLAB_SSL_VERIFY", "true").lower() != "false"

    try:
        response = session.get(url, timeout=_REQUEST_TIMEOUT)
    except Exception as exc:  # pylint: disable=broad-except
        _fail("GitLab project reachable", f"GET {url} → {type(exc).__name__}: {exc}")
    if response.status_code != 200:
        _fail("GitLab project reachable", f"GET {url} → HTTP {response.status_code}")

    project = response.json()
    _ok("GitLab project", project["path_with_namespace"])
    _ok("Default branch", project.get("default_branch") or "(empty repository)")

    permissions = project.get("permissions") or {}
    levels = [
        (permissions.get(scope) or {}).get("access_level", 0)
        for scope in ("project_access", "group_access")
    ]
    best = max(levels) if levels else 0
    if best < _MIN_PUSH_ACCESS_LEVEL:
        _fail(
            "Token may push",
            f"highest access_level {best} < {_MIN_PUSH_ACCESS_LEVEL} (Developer)",
        )
    _ok("Token may push", f"access_level {best}")


def check_anthropic() -> None:
    print("\n── Anthropic ──")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:  # pylint: disable=broad-except
        _fail(f"Anthropic {model} reachable", f"{type(exc).__name__}: {exc}")
    _ok("Anthropic model", message.model)


def check_redis() -> None:
    print("\n── Redis (optional) ──")
    url = os.environ.get("REDIS_URL", "redis://nesti-redis:6379/0")
    try:
        import redis

        redis.Redis.from_url(url, socket_connect_timeout=3).ping()
    except Exception as exc:  # pylint: disable=broad-except
        # The in-memory fallback is legitimate, so this is never fatal.
        _warn(
            "Redis reachable",
            f"{url} → {type(exc).__name__}: {exc} (in-memory fallback will be used)",
        )
        return
    _ok("Redis reachable", url)


def check_docker() -> None:
    print("\n── Docker ──")
    try:
        import docker

        client = docker.from_env()
        info = client.info()
    except Exception as exc:  # pylint: disable=broad-except
        _fail("Docker daemon responds", f"{type(exc).__name__}: {exc}")
    _ok("Docker daemon", f"server {info.get('ServerVersion', '?')}")

    for name, default in _SANDBOX_IMAGE_VARS:
        image = os.environ.get(name, default)
        try:
            client.images.get(image)
        except Exception as exc:  # pylint: disable=broad-except
            _fail(
                f"Sandbox image {image}",
                f"not present ({type(exc).__name__}) – build it with the "
                f"matching Dockerfile before the live run",
            )
        _ok(f"Sandbox image {image}", "present")

    # The sandbox is mounted by the HOST daemon, so workspace paths under /tmp
    # must exist identically inside and outside the orchestrator container.
    try:
        with tempfile.NamedTemporaryFile(dir="/tmp") as probe:
            probe.write(b"nesti")
    except Exception as exc:  # pylint: disable=broad-except
        _fail("/tmp writable", f"{type(exc).__name__}: {exc}")
    _ok("/tmp writable", "workspace mounts will resolve")


def check_skill_catalog() -> None:
    print("\n── Skill catalog ──")
    status = skill_catalog.catalog_status()
    if not status.get("available"):
        _fail(
            "Vendored skill corpus",
            "skills/registry.json missing or unreadable – run "
            "scripts/fetch_skills.py and commit skills/",
        )
    _ok(
        "Vendored skill corpus",
        f"{status['components']} PrimeVue component doc(s), "
        f"{status['topics']} Laravel topic(s) "
        f"(PrimeVue {status['primevue_version']} / Laravel {status['laravel_branch']})",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-llm", action="store_true",
                        help="skip the paid 1-token Anthropic call")
    parser.add_argument("--skip-docker", action="store_true",
                        help="skip the Docker daemon and sandbox-image checks")
    args = parser.parse_args()

    print("Nesti preflight")
    check_configuration()
    check_issues()
    check_gitlab()
    if args.skip_llm:
        print("\n── Anthropic ──\n  SKIP  --skip-llm")
    else:
        check_anthropic()
    check_redis()
    if args.skip_docker:
        print("\n── Docker ──\n  SKIP  --skip-docker")
    else:
        check_docker()
    check_skill_catalog()

    print(f"\nPREFLIGHT OK ({_warnings} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
