#!/usr/bin/env python3
"""
scripts/preflight.py – verify every external dependency before a live run.

Prints one line per check and exits non-zero on the first HARD failure, so a
live run is never started against a half-configured environment.  Checks are
ordered cheapest-first: configuration, then the forge's (GitLab or GitHub)
issues, then its repository, then a consumer-first LLM probe, then the local
Docker/corpus state.

Usage:
    python scripts/preflight.py                 # everything
    python scripts/preflight.py --skip-llm      # no inference call
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
import forge  # noqa: E402

_REQUEST_TIMEOUT = 15
_PLACEHOLDER_MARKERS = ("your_", "_here", "changeme", "xxx")

_REQUIRED_VARS = {
    "gitlab": ("GITLAB_URL", "GITLAB_TOKEN", "GITLAB_PROJECT_PATH"),
    "github": ("NESTI_GITHUB_TOKEN", "NESTI_GITHUB_REPOSITORY"),
}

# Per forge: where the issue tracker is enabled, and the right issue creation needs.
_ISSUE_HINTS = {
    "gitlab": ("Settings → General → Visibility", "at least Reporter rights"),
    "github": ("Settings → General → Features", "the Issues: read and write permission"),
}

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
    try:
        kind = forge.kind()
    except ValueError as exc:
        _fail("NESTI_FORGE", str(exc))
    _ok("NESTI_FORGE", kind)
    for name in _REQUIRED_VARS[kind]:
        value = os.environ.get(name, "")
        if not value.strip():
            _fail(f"{name} present", "missing from .env")
        if _is_placeholder(value):
            _fail(f"{name} configured", f"still a placeholder ({value[:24]!r})")
        shown = value if name.endswith(("URL", "PATH", "PROJECT_ID", "REPOSITORY")) else f"set ({len(value)} chars)"
        _ok(name, shown)

    for provider, default in (("OPENROUTER", "false"), ("DEEPSEEK", "true"), ("ANTHROPIC", "false")):
        if os.environ.get(f"{provider}_API_ENABLED", default).strip().lower() != "true":
            _ok(f"{provider} API", "disabled")
            continue
        key_name = f"{provider}_API_KEY"
        key = os.environ.get(key_name, "").strip()
        if not key:
            _warn(key_name, "absent; this API tier will be skipped")
            continue
        if _is_placeholder(key):
            _fail(key_name, "enabled API still has a placeholder key")
        _ok(key_name, "configured; used only after consumer and local tiers")



def check_issues() -> None:
    """
    Verify the forge's issue intake end to end.

    The lifecycle probe replaces the old Redmine workflow probe and exists for
    the same reason: a token that can read issues but not label or close them
    produces a run that looks healthy and then strands its issue.  The probe
    drives the forge's issue client itself, so it exercises the exact code the
    orchestrator uses rather than a parallel re-implementation.
    """
    print(f"\n── {forge.term('forge')} Issues ──")
    client = forge.issue_client()
    _ok("Opt-in label", f"{client.issue_label!r} (lock: {client.in_progress_label!r})")

    project = _project_info(client, "Project reachable")
    level = project.get("issues_access_level")  # GitLab only
    if not project.get("issues_enabled", False):
        _fail(
            "Issues enabled",
            f"the issue tracker is disabled on {client.project_path} "
            + (f"(issues_access_level={level!r}); " if level is not None else "")
            + f"enable it in {_ISSUE_HINTS[forge.kind()][0]}",
        )
    _ok("Issues enabled", f"access level {level}" if level is not None else "")

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


def _probe_issue_lifecycle(client: forge.IssueClient) -> None:
    """Create a throwaway issue and drive it through the whole lifecycle."""
    try:
        probe = client.create_issue(
            "nesti preflight probe",
            "Created by scripts/preflight.py to verify the issue "
            "lifecycle. Safe to ignore; left closed.",
            labels=[client.issue_label],
        )
    except Exception as exc:  # pylint: disable=broad-except
        _fail(
            "Issue creation",
            f"{exc} — the token needs {_ISSUE_HINTS[forge.kind()][1]} on {client.project_path}",
        )
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
              f"a successful run could open its {forge.term('mr')} but never close the issue")
    _ok("Close (success path)", f"probe issue #{iid} left closed – {web_url}")


def _project_info(client, label: str) -> dict:
    """The forge project record from *client*, or a hard failure under *label*."""
    try:
        return client.project_info()
    except requests.HTTPError as exc:
        _fail(label, f"GET {exc.response.url} → HTTP {exc.response.status_code}")
    except Exception as exc:  # pylint: disable=broad-except
        _fail(label, f"{type(exc).__name__}: {exc}")


def check_gitlab() -> None:
    print("\n── GitLab ──")
    project = _project_info(forge.issue_client(), "GitLab project reachable")
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


def _github_get(session, url: str, label: str, allowed: tuple[int, ...] = ()) -> requests.Response:
    """GET *url*: a 2xx or *allowed* response is returned, anything else is a hard failure under *label*."""
    try:
        response = session.get(url, timeout=_REQUEST_TIMEOUT)
    except Exception as exc:  # pylint: disable=broad-except
        _fail(label, f"GET {url} → {type(exc).__name__}: {exc}")
    if not response.ok and response.status_code not in allowed:
        _fail(label, f"GET {url} → HTTP {response.status_code}")
    return response


def check_github() -> None:
    from github_issues_client import api_session, api_url  # a GitLab run never needs it

    print(f"\n── {forge.term('forge')} ──")
    repo = _project_info(forge.issue_client(), "GitHub repository reachable")
    _ok("GitHub repository", repo["path_with_namespace"])
    if not (repo.get("permissions") or {}).get("push"):
        _fail("Token may push", "permissions.push is false – the token needs Contents: read and write")
    _ok("Token may push", "permissions.push")

    branch, base = forge.default_branch(), f"{api_url()}/repos/{forge.path()}"
    with api_session() as session:
        if _github_get(session, f"{base}/branches/{quote(branch)}", "Target branch exists", (404,)).ok:
            _ok("Target branch", branch)
        else:
            # An empty repository has no branch yet; the first run pushes its initial commit there.
            listing = _github_get(session, f"{base}/branches?per_page=1", "Target branch exists", (409,))
            if listing.ok and listing.json():
                _fail("Target branch exists",
                      f"{branch!r} is not a branch of {forge.path()} – check NESTI_GITHUB_DEFAULT_BRANCH")
            _ok("Target branch", f"{branch} (empty repository; the first run creates it)")
        variables = _github_get(session, f"{base}/actions/variables?per_page=1", "Actions variables", (403, 404))

    if repo.get("delete_branch_on_merge"):
        _ok("Delete head branches", "on")
    else:
        _warn("Delete head branches",
              "off – merged PR branches stay; Nesti does not change the setting "
              "(Settings → General → Pull Requests)")
    if variables.ok:
        _ok("Actions variables", "readable (poll heartbeat)")
    else:
        _warn("Actions variables",
              f"HTTP {variables.status_code} – no Variables permission; the poll heartbeat "
              "warns once and runs without it")


def check_llm() -> None:
    """Probe the configured cascade, never a hard-wired billed provider."""
    from llm_client import LLMClient

    print("\n── LLM cascade ──")
    try:
        client = LLMClient()
        result = client.generate_plan("Reply only OK.", "Connectivity check. Reply OK.")
        if not result.strip():
            raise RuntimeError("The provider returned no text.")
    except Exception as exc:  # pylint: disable=broad-except
        _fail("LLM reachable", f"{type(exc).__name__}: {exc}")
    _ok("LLM reachable", client.last_planner_label)


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
        f"{status['topics']} Laravel topic(s), "
        f"{status['practices']} practice doc(s) "
        f"(PrimeVue {status['primevue_version']} / Laravel {status['laravel_branch']})",
    )


def check_vector_memory() -> None:
    """memory is optional by design: this section warns, never fails."""
    print("\n── Vector memory (optional) ──")
    from embedding import get_embedder
    from graph.tools import tool_memory_status

    embedder = get_embedder()
    if not embedder.enabled:
        _warn("Vector memory", "NESTI_MEMORY_ENABLED=false – prompts use the keyword catalog only")
        return
    if embedder.embed_query("preflight"):
        _ok("Embedding model", f"{embedder.model_name} ({embedder.dim} dims)")
    else:
        _warn("Embedding model", f"{embedder.model_name} failed to load: {embedder.error}")

    status = tool_memory_status()
    if not status["success"]:
        _warn("Memory status", status["error"])
        return

    qdrant = status["result"]["qdrant"]
    target = f"{qdrant['collection']} @ {qdrant['url']}"
    if qdrant["points"] is None:
        _warn("Qdrant document memory", f"{target} unreachable or not indexed – "
              f"{qdrant.get('error') or 'no detail'}")
    elif qdrant["points"] == 0:
        _warn("Qdrant document memory", f"{target} is empty – run scripts/index_skills.py")
    else:
        _ok("Qdrant document memory", f"{qdrant['points']} chunk(s) in {target}")

    semantic = status["result"]["redis"]
    if semantic["engine"] != "redis-query-engine":
        _warn("Redis query engine", f"{semantic['url']} unreachable or without FT.CREATE – "
              "Redis 8+ is required; solution cache and episodic memory disabled")
    else:
        _ok("Redis query engine",
            f"{semantic['solutions']} solution(s), {semantic['episodes']} episode(s) "
            f"@ {semantic['url']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-llm", action="store_true",
                        help="skip the consumer-first inference probe (may use a billed fallback)")
    parser.add_argument("--skip-docker", action="store_true",
                        help="skip the Docker daemon and sandbox-image checks")
    args = parser.parse_args()

    print("Nesti preflight")
    check_configuration()
    check_issues()
    check_github() if forge.kind() == "github" else check_gitlab()
    if args.skip_llm:
        print("\n── LLM cascade ──\n  SKIP  --skip-llm")
    else:
        check_llm()
    check_redis()
    if args.skip_docker:
        print("\n── Docker ──\n  SKIP  --skip-docker")
    else:
        check_docker()
    check_skill_catalog()
    check_vector_memory()

    print(f"\nPREFLIGHT OK ({_warnings} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
