#!/usr/bin/env python3
"""
scripts/preflight.py – verify every external dependency before a live run.

Prints one line per check and exits non-zero on the first HARD failure, so a
live run is never started against a half-configured environment.  Checks are
ordered cheapest-first: configuration, then Redmine, then GitLab, then the
paid LLM call, then the local Docker/corpus state.

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

_REQUEST_TIMEOUT = 15
_PLACEHOLDER_MARKERS = ("your_", "_here", "changeme", "xxx")

_REQUIRED_VARS = (
    "REDMINE_URL",
    "REDMINE_API_KEY",
    "REDMINE_PROJECT_ID",
    "GITLAB_URL",
    "GITLAB_TOKEN",
    "GITLAB_PROJECT_PATH",
    "ANTHROPIC_API_KEY",
)

_STATUS_VARS = (
    ("REDMINE_NEW_STATUS_ID", "1"),
    ("REDMINE_IN_PROGRESS_STATUS_ID", "2"),
    ("REDMINE_CLOSED_STATUS_ID", "5"),
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

    for name, default in _STATUS_VARS:
        raw = os.environ.get(name, default)
        try:
            int(raw)
        except ValueError:
            _fail(f"{name} numeric", f"got {raw!r}")
        _ok(name, raw)


def check_redmine() -> None:
    print("\n── Redmine ──")
    base = os.environ["REDMINE_URL"].rstrip("/")
    project = os.environ["REDMINE_PROJECT_ID"]
    session = requests.Session()
    session.headers.update({"X-Redmine-API-Key": os.environ["REDMINE_API_KEY"]})

    url = f"{base}/projects/{project}.json"
    try:
        response = session.get(url, timeout=_REQUEST_TIMEOUT)
    except Exception as exc:  # pylint: disable=broad-except
        _fail("Redmine project reachable", f"GET {url} → {type(exc).__name__}: {exc}")
    if response.status_code != 200:
        _fail("Redmine project reachable", f"GET {url} → HTTP {response.status_code}")
    _ok("Redmine project", response.json()["project"]["name"])

    url = f"{base}/issue_statuses.json"
    try:
        response = session.get(url, timeout=_REQUEST_TIMEOUT)
    except Exception as exc:  # pylint: disable=broad-except
        _fail("Redmine statuses readable", f"GET {url} → {type(exc).__name__}: {exc}")
    if response.status_code != 200:
        _fail("Redmine statuses readable", f"GET {url} → HTTP {response.status_code}")

    by_id = {s["id"]: s["name"] for s in response.json()["issue_statuses"]}
    for name, default in _STATUS_VARS:
        status_id = int(os.environ.get(name, default))
        if status_id not in by_id:
            _fail(
                f"{name} exists in Redmine",
                f"id {status_id} not among {sorted(by_id)}",
            )
        _ok(f"{name}={status_id}", by_id[status_id])

    _check_redmine_workflow(session, base, by_id)


def _check_redmine_workflow(session: requests.Session, base: str,
                            by_id: dict[int, str]) -> None:
    """
    Prove the API user may actually perform the three transitions the pipeline
    needs, using a throwaway issue.

    Redmine returns 204 for a PUT whose status change its workflow forbids and
    silently drops the field, so a misconfigured workflow is invisible until a
    real run strands an issue: the orchestrator logs "reopened" while the
    issue stays in-progress and is never polled again.
    """
    project = os.environ["REDMINE_PROJECT_ID"]
    new_id = int(os.environ.get("REDMINE_NEW_STATUS_ID", "1"))
    progress_id = int(os.environ.get("REDMINE_IN_PROGRESS_STATUS_ID", "2"))
    closed_id = int(os.environ.get("REDMINE_CLOSED_STATUS_ID", "5"))

    created = session.post(
        f"{base}/issues.json",
        json={"issue": {
            "project_id": project,
            "subject": "nesti preflight workflow probe",
            "description": "Created by scripts/preflight.py to verify status "
                           "transitions. Safe to delete.",
            "status_id": new_id,
        }},
        timeout=_REQUEST_TIMEOUT,
    )
    if created.status_code not in (200, 201):
        _fail("Redmine issue creation",
              f"POST /issues.json → HTTP {created.status_code}: {created.text[:200]}")
    probe_id = created.json()["issue"]["id"]
    _ok("Redmine issue creation", f"probe issue #{probe_id}")

    def _transition(target: int, label: str) -> bool:
        session.put(
            f"{base}/issues/{probe_id}.json",
            json={"issue": {"status_id": target}},
            timeout=_REQUEST_TIMEOUT,
        )
        actual = session.get(
            f"{base}/issues/{probe_id}.json", timeout=_REQUEST_TIMEOUT
        ).json()["issue"]["status"]["id"]
        return actual == target

    try:
        if not _transition(progress_id, "in-progress"):
            _fail("Workflow: new → in-progress",
                  f"the API user cannot move an issue to status "
                  f"{progress_id} ({by_id.get(progress_id)}); every run would "
                  f"fail to lock its issue")
        _ok("Workflow: new → in-progress", by_id.get(progress_id, "?"))

        # The failure path. A forbidden reopen is not fatal for a successful
        # run, so this is a warning — but a failed issue then stays
        # in-progress forever and is never retried.
        if _transition(new_id, "new"):
            _ok("Workflow: in-progress → new", by_id.get(new_id, "?"))
            _transition(progress_id, "in-progress")
        else:
            _warn(
                "Workflow: in-progress → new",
                f"FORBIDDEN – a failed issue cannot be reopened and will stay "
                f"in {by_id.get(progress_id)!r} forever instead of being "
                f"retried. Grant this transition in Redmine "
                f"(Administration → Workflow) for the API user's role.",
            )

        if not _transition(closed_id, "closed"):
            _fail("Workflow: in-progress → closed",
                  f"the API user cannot move an issue to status "
                  f"{closed_id} ({by_id.get(closed_id)}); a successful run "
                  f"could open its MR but never close the issue")
        _ok("Workflow: in-progress → closed",
            f"{by_id.get(closed_id, '?')} (probe issue #{probe_id} left closed)")
    finally:
        # DELETE needs admin rights the bot usually lacks; leaving the probe
        # closed is harmless and keeps preflight usable by a plain API user.
        session.delete(f"{base}/issues/{probe_id}.json", timeout=_REQUEST_TIMEOUT)


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
    check_redmine()
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
