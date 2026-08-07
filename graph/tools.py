"""
graph/tools.py – atomic tool functions.

Design rules (MCP compatibility):
  1. Each function takes simple typed arguments (str, int, dict, list).
  2. Each function returns a plain dict with a "success" bool and result fields.
  3. No LangGraph imports inside this file.
  4. No global state — all dependencies come from environment variables or
     arguments.  Clients are constructed per call (they are cheap: a
     requests.Session / docker handle), which keeps every tool stateless and
     directly exposable as an MCP tool in Phase 3.

Return shape convention (all tools follow this):

    # Success:
    {"success": True, "result": <value>}

    # Failure:
    {"success": False, "error": "<human readable message>"}

Notes
─────
• GitLabClient.create_branch / commit_and_push operate on a ``git.Repo``
  object.  Because MCP tools may only accept plain arguments, these wrappers
  re-open the repository from ``repo_path`` internally.

• tool_skill_fetch returns ``skill_loader.Skill`` dataclass instances in
  ``result`` because prompt_builder (unchanged per spec) consumes them by
  attribute.  When this tool is exposed over MCP in Phase 3, serialise with
  ``dataclasses.asdict`` at the transport boundary.
"""

import logging
import os
from pathlib import Path

import git

from docker_runner import DockerRunner
from frontend_runner import FrontendRunner
from gitlab_client import GitLabClient
from redmine_client import RedmineClient
from skill_loader import load_skills

logger = logging.getLogger(__name__)

_REDMINE_LIST_LIMIT = 25
_REQUEST_TIMEOUT = 15  # seconds, matches RedmineClient's own timeouts

# Directories never treated as project source during stack detection.
# ``node_modules`` is the load-bearing entry: the Vitest sandbox mounts the
# workspace read-write, so from the second attempt onward the tree contains
# installed dependencies — and Vue component libraries ship thousands of .vue
# files.  Without pruning, every retry would report has_vue=True and the walk
# would crawl the whole dependency tree.
_STACK_SCAN_PRUNE = frozenset({
    ".git", "node_modules", "vendor", "dist", "build", ".next", "out",
    "coverage", "playwright-report", "test-results", ".nuxt", ".output",
})

# Markers that prove a layer is present even before any source file matches.
_PHP_PROJECT_FILES = ("composer.json", "composer.lock")

_VALID_STACKS = ("php", "vue", "fullstack")

# Redmine status ids are resolved inside RedmineClient from .env; this maps
# the MCP-friendly status strings onto the client methods.
_VALID_STATUSES = ("in_progress", "closed", "new")


# ─────────────────────────────────────────────────────────────────────────────
# Return-shape helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ok(result) -> dict:
    return {"success": True, "result": result}


def _err(message) -> dict:
    return {"success": False, "error": str(message)}


# ─────────────────────────────────────────────────────────────────────────────
# Redmine tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_redmine_get_issue(issue_id: int) -> dict:
    """Fetch a Redmine issue by ID.  result: the raw issue dict."""
    try:
        client = RedmineClient()
        response = client.session.get(
            f"{client.base_url}/issues/{issue_id}.json", timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        issue = response.json().get("issue")
        if not issue:
            return _err(f"Redmine returned no issue payload for #{issue_id}.")
        return _ok(issue)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_redmine_get_issue(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_redmine_list_pending() -> dict:
    """
    List new/pending issues for the configured project, oldest first.
    result: list of raw issue dicts (possibly empty).
    """
    try:
        client = RedmineClient()
        params = {
            "project_id": client.project_id,
            "status_id": client.new_status_id,
            "sort": "id:asc",
            "limit": _REDMINE_LIST_LIMIT,
        }
        response = client.session.get(
            f"{client.base_url}/issues.json", params=params, timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return _ok(response.json().get("issues", []))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_redmine_list_pending() failed: %s", exc)
        return _err(exc)


def tool_redmine_set_status(issue_id: int, status: str, note: str = "") -> dict:
    """
    Update issue status. status: "in_progress" | "closed" | "new"
    Maps to the configured status IDs from .env.
    result: {"issue_id": int, "status": str}

    Note: RedmineClient.lock_issue (unchanged per spec) does not accept a
    note, so *note* is ignored for "in_progress".
    """
    if status not in _VALID_STATUSES:
        return _err(f"Invalid status {status!r} – expected one of {_VALID_STATUSES}.")
    try:
        client = RedmineClient()
        if status == "in_progress":
            updated = client.lock_issue(issue_id)
        elif status == "closed":
            updated = client.close_issue(issue_id, note=note)
        else:  # "new"
            updated = client.reopen_issue(issue_id, note=note)
        if not updated:
            return _err(f"Redmine rejected status update for issue #{issue_id}.")
        return _ok({"issue_id": issue_id, "status": status})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_redmine_set_status(%s, %s) failed: %s", issue_id, status, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# GitLab tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_gitlab_clone(target_path: str) -> dict:
    """Clone the configured repository into target_path.  result: {"repo_path": str}."""
    try:
        GitLabClient().clone(target_path)
        return _ok({"repo_path": target_path})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_gitlab_clone(%s) failed: %s", target_path, exc)
        return _err(exc)


def tool_gitlab_create_branch(repo_path: str, issue_id: int, subject: str) -> dict:
    """Create and checkout a feature branch.  result: {"branch_name": str}."""
    try:
        repo = git.Repo(repo_path)
        branch_name = GitLabClient().create_branch(repo, issue_id, subject)
        return _ok({"branch_name": branch_name})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_gitlab_create_branch(%s) failed: %s", repo_path, exc)
        return _err(exc)


def tool_gitlab_commit_and_push(repo_path: str, branch_name: str, message: str) -> dict:
    """
    Stage all, commit, push.  result: {"pushed": bool}.

    ``pushed`` is False (with success=True) when there was nothing to commit –
    the tool executed correctly, the repository simply had no changes.
    """
    try:
        repo = git.Repo(repo_path)
        pushed = GitLabClient().commit_and_push(repo, branch_name, message)
        return _ok({"pushed": pushed})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_gitlab_commit_and_push(%s) failed: %s", branch_name, exc)
        return _err(exc)


def tool_gitlab_open_mr(branch_name: str, issue_id: int, subject: str, description: str) -> dict:
    """Open a GitLab Merge Request.  result: {"mr_url": str, "mr": dict}."""
    try:
        mr = GitLabClient().open_merge_request(
            branch_name=branch_name,
            issue_id=issue_id,
            subject=subject,
            description=description,
        )
        if mr is None:
            return _err(f"GitLab refused to open a Merge Request for branch {branch_name!r}.")
        return _ok({"mr_url": mr.get("web_url", ""), "mr": mr})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_gitlab_open_mr(%s) failed: %s", branch_name, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Docker tool
# ─────────────────────────────────────────────────────────────────────────────

def tool_docker_run_tests(workspace_path: str) -> dict:
    """
    Run PHPUnit in the Docker sandbox.  result: {"passed": bool, "output": str}.

    DockerRunner.run_tests never raises (it catches internally), so failures
    of the *test suite* surface as passed=False with success=True; only an
    unexpected error constructing/driving the Docker client yields success=False.
    """
    try:
        passed, output = DockerRunner().run_tests(workspace_path)
        return _ok({"passed": passed, "output": output})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_docker_run_tests(%s) failed: %s", workspace_path, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Stack detection
# ─────────────────────────────────────────────────────────────────────────────

def _scan_workspace(workspace_path: str) -> tuple[list[str], bool]:
    """
    Walk *workspace_path* once, pruning generated and vendored trees.

    Returns ``(vue_files, has_php)`` where *vue_files* are repo-relative paths
    and *has_php* is True when the workspace contains PHP sources or a Composer
    project file.
    """
    root = Path(workspace_path)
    vue_files: list[str] = []
    has_php = False

    for dirpath, dirnames, filenames in os.walk(workspace_path):
        # In-place mutation is what makes os.walk skip these subtrees.
        dirnames[:] = [d for d in dirnames if d not in _STACK_SCAN_PRUNE]
        for filename in filenames:
            if filename.endswith(".vue"):
                vue_files.append(str(Path(dirpath, filename).relative_to(root)))
            elif not has_php and (
                filename.endswith(".php") or filename in _PHP_PROJECT_FILES
            ):
                has_php = True

    return sorted(vue_files), has_php


def tool_detect_stack(workspace_path: str) -> dict:
    """
    Determine which test layers apply to the code in workspace_path.

    result: {"stack": str, "has_vue": bool, "has_php": bool,
             "run_phpunit": bool, "vue_files": list[str], "source": str}

    ``stack`` is one of:
      "php"       – PHP sources or a Composer project, no .vue files
      "vue"       – .vue files and no PHP whatsoever (frontend-only repository)
      "fullstack" – both layers present
      "unknown"   – neither detected (empty or non-code change)

    ``run_phpunit`` is the routing decision, kept separate from the descriptive
    label.  It is False only for the "vue" stack: a frontend-only workspace has
    no composer.json and no phpunit binary, so running the PHP layer there
    would fail on every attempt and drive the issue to permanent failure —
    which is exactly the trap that made Vue-only issues impossible before.
    "unknown" keeps run_phpunit=True so an unrecognised change still faces a
    test layer instead of silently reaching commit untested.

    Detection is automatic; set NESTI_STACK to php / vue / fullstack to pin it
    when a repository's layout misleads the scan.
    """
    try:
        override = os.environ.get("NESTI_STACK", "auto").strip().lower()
        if override in _VALID_STACKS:
            stack = override
            source = "override"
            has_vue = stack in ("vue", "fullstack")
            has_php = stack in ("php", "fullstack")
            vue_files = []
        elif override not in ("", "auto"):
            return _err(
                f"Invalid NESTI_STACK={override!r} – expected 'auto' or one of {_VALID_STACKS}."
            )
        else:
            vue_files, has_php = _scan_workspace(workspace_path)
            has_vue = bool(vue_files)
            if has_vue and has_php:
                stack = "fullstack"
            elif has_vue:
                stack = "vue"
            elif has_php:
                stack = "php"
            else:
                stack = "unknown"
            source = "auto"

        return _ok({
            "stack": stack,
            "has_vue": has_vue,
            "has_php": has_php,
            "run_phpunit": stack != "vue",
            "vue_files": vue_files,
            "source": source,
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_detect_stack(%s) failed: %s", workspace_path, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Frontend test tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_vitest_run_tests(workspace_path: str) -> dict:
    """
    Run Vitest component tests in the Node sandbox.
    result: {"passed": bool, "output": str}.

    Same semantics as tool_docker_run_tests: FrontendRunner never raises, so a
    failing suite is passed=False with success=True; success=False means the
    Docker client itself could not be driven.
    """
    try:
        passed, output = FrontendRunner().run_vitest(workspace_path)
        return _ok({"passed": passed, "output": output})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_vitest_run_tests(%s) failed: %s", workspace_path, exc)
        return _err(exc)


def tool_playwright_run_tests(workspace_path: str) -> dict:
    """
    Run Playwright E2E tests in the browser sandbox.
    result: {"passed": bool, "output": str}.

    The sandbox builds the app and Playwright's webServer config serves it;
    no server needs to be running beforehand.
    """
    try:
        passed, output = FrontendRunner().run_playwright(workspace_path)
        return _ok({"passed": passed, "output": output})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_playwright_run_tests(%s) failed: %s", workspace_path, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Skill tool
# ─────────────────────────────────────────────────────────────────────────────

def tool_skill_fetch(issue: dict) -> dict:
    """
    Fetch skill documentation URLs from the issue.  result: list of Skill objects.

    load_skills already reports individual URL failures to Telegram and never
    raises for per-URL problems; success=False covers only unexpected errors.
    """
    try:
        return _ok(load_skills(issue))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_skill_fetch(issue #%s) failed: %s", issue.get("id", "?"), exc)
        return _err(exc)
