"""
graph/tools.py – atomic tool functions.

Design rules (MCP compatibility):
  1. Each function takes simple typed arguments (str, int, dict, list).
  2. Each function returns a plain dict with a "success" bool and result fields.
  3. No LangGraph imports inside this file.
  4. No global state — all dependencies come from environment variables or
     arguments.  Clients are constructed per call (they are cheap: a
     requests.Session / docker handle), which keeps every tool stateless and
     directly exposable as an MCP tool.

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

• tool_skill_fetch and tool_skill_catalog_select return ``skill_loader.Skill``
  dataclass instances in ``result`` because prompt_builder (unchanged per
  spec) consumes them by attribute.  When these tools are exposed over MCP,
  serialise with ``dataclasses.asdict`` at the transport boundary.

• tool_laravel_bootstrap is the only tool that *writes* into the repository
  besides DockerRunner.write_files.  It applies the templates shipped in
  ``templates/laravel/`` and is the reason a greenfield GitLab repository can
  become a Laravel 13 + PrimeVue application inside a single run.
"""

import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import git

from docker_runner import DockerRunner
from frontend_runner import FrontendRunner
from gitlab_client import GitLabClient
from gitlab_issues_client import GitLabIssuesClient
from issue_dependencies import FixtureDependencies
from scripts.oauth import TokenStore, fetch_usage
from semantic_cache import get_semantic_memory
import project_layout
from skill_catalog import catalog_status, select_skills
from skill_loader import load_skills
import stats
from vector_store import get_document_memory

logger = logging.getLogger(__name__)

_ISSUE_LIST_LIMIT = 25
_REQUEST_TIMEOUT = 15  # seconds, matches the clients' own timeouts

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

# Laravel / OpenAPI layer markers.  Checked with direct is_file() calls rather
# than through _scan_workspace: both are fixed, known paths, and the walk must
# stay exactly as pruned as it is.
_LARAVEL_MARKER = "artisan"
_API_ROUTES_FILE = "routes/api.php"

# A written path under one of these makes the OpenAPI layer applicable.  A
# pure .vue or migration change must not pay for a Scramble export.
_API_TOUCH_PREFIXES = (
    "app/Http/Controllers/",
    "app/Http/Resources/",
    "app/Http/Requests/",
)

# Written paths that change what the browser loads: the Vitest and Playwright
# layers apply to them (in a repository that has Vue).  A pure PHP change in a
# repository that merely contains .vue files must not pay for two Node
# containers, and a pure .vue change cannot alter what PHPUnit executes.
_FRONTEND_SUFFIXES = (
    ".vue", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".jsx", ".tsx",
    ".css", ".scss", ".sass", ".less", ".html", ".svg",
)
_FRONTEND_PREFIXES = ("resources/js/", "resources/css/", "e2e/")
_FRONTEND_FILES = frozenset({
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
})
# Blade views and web routes are PHP that serves pages: they count for both sides.
_SHARED_SUFFIXES = (".blade.php",)
_SHARED_FILES = frozenset({"routes/web.php"})
# Besides .php sources, what PHPUnit's run depends on.
_BACKEND_FILES = frozenset({"composer.json", "composer.lock", "artisan", "phpunit.xml", ".env.example"})

# Written by the openapi recipe; storage/app is git-ignored by Laravel, so the
# route dump never lands in the Merge Request.
_ROUTE_DUMP_REL = "storage/app/nesti-routes.json"

# HTTP verbs Laravel registers implicitly; they never appear in OpenAPI.
_IMPLICIT_METHODS = frozenset({"HEAD", "OPTIONS"})

# Bootstrap templates shipped with Nesti, keyed by their repo-relative
# destination.  Scaffold mode writes all of them over the skeleton Nesti just
# created; top-up mode writes only _TOPUP_TEMPLATES, and only when absent.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "laravel"
_SPA_TEMPLATES_DIR = _TEMPLATES_DIR.parent / "spa"

_SCAFFOLD_TEMPLATES = (
    "vite.config.js",
    "vitest.config.js",
    "playwright.config.js",
    "resources/js/app.js",
    "resources/views/app.blade.php",
    "routes/web.php",
    "routes/api.php",
    # Overrides the skeleton's own TestCase: it disables Vite so the PHP
    # sandbox, which never runs `npm run build`, can render Blade views.
    "tests/TestCase.php",
    "tests/Feature/OpenApiDocumentationTest.php",
)

_TOPUP_TEMPLATES = (
    "vitest.config.js",
    "playwright.config.js",
    "tests/Feature/OpenApiDocumentationTest.php",
)

_PACKAGE_DEPENDENCIES = {
    "vue": "^3.5.0",
    "primevue": "^5.0.0",
    # @primevue/themes is deprecated; @primeuix/themes is the PrimeVue 5 home
    # of the Aura preset referenced by resources/js/app.js.
    "@primeuix/themes": "^3.0.0",
    "primeicons": "^8.0.0",
}

_PACKAGE_DEV_DEPENDENCIES = {
    "@vitejs/plugin-vue": "^6.0.0",
    "@vue/test-utils": "^2.5.0",
    "vitest": "^5.0.0",
    "jsdom": "^30.0.0",
    # Exact, never a caret: nesti-sandbox-e2e bakes the Playwright 1.50
    # browsers, and ^1.50.0 resolves past them — Playwright then refuses to
    # launch with "Executable doesn't exist at /ms-playwright/…".
    "@playwright/test": "1.50.0",
}

_PACKAGE_SCRIPTS = {"test": "vitest run"}

# The Laravel 13 skeleton does not ignore the sqlite file the sandbox creates,
# so without this the database would land in the Merge Request.  openapi.json
# is deliberately absent: it is a committed deliverable.
_GITIGNORE_LINES = ("/database/*.sqlite*", "/.phpunit.cache")

_VALID_STACKS = ("php", "vue", "fullstack")

# Intake lifecycle vocabulary. GitLab has no "in progress" or "paused" issue
# state, so GitLabIssuesClient expresses these words as labels plus
# open/closed — the strings stay stable so every node and MCP client is
# unaffected.
_VALID_STATUSES = ("in_progress", "closed", "new", "paused")


# ─────────────────────────────────────────────────────────────────────────────
# Return-shape helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ok(result) -> dict:
    return {"success": True, "result": result}


def _err(message) -> dict:
    return {"success": False, "error": str(message)}


# ─────────────────────────────────────────────────────────────────────────────
# Issue intake tools (GitLab Issues)
# ─────────────────────────────────────────────────────────────────────────────

def tool_issue_get(issue_id: int) -> dict:
    """
    Fetch one issue by its project-scoped iid.
    result: {"id", "subject", "description", "iid", "state", "labels",
             "web_url", "author", "global_id"}.
    """
    try:
        return _ok(GitLabIssuesClient().get_issue(issue_id))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_get(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_list_pending() -> dict:
    """
    List pending issues for the configured project, oldest first.
    result: list of issue dicts (possibly empty).

    Pending means: open, carrying the opt-in GITLAB_ISSUE_LABEL, carrying
    neither the ``<label>::in-progress`` lock nor the ``<label>::pause`` hold,
    and not held by an unresolved (or malformed) fixture-dependency record.
    """
    try:
        return _ok(GitLabIssuesClient().list_pending(limit=_ISSUE_LIST_LIMIT))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_list_pending() failed: %s", exc)
        return _err(exc)


def tool_issue_set_status(issue_id: int, status: str, note: str = "") -> dict:
    """
    Move an issue through the intake lifecycle.
    status: "in_progress" | "closed" | "new" | "paused"
    result: {"issue_id": int, "status": str}

    The vocabulary is deliberately the words the pipeline has always used;
    GitLab expresses them as labels plus open/closed state:
      in_progress → add    <label>::in-progress (only while the issue is pending)
      closed      → remove <label>::in-progress, close, comment
      new         → remove <label>::in-progress, reopen, comment (back to the
                    pending pool, which is what makes a failed issue retryable);
                    refused for a paused issue or one an unresolved dependency
                    record holds, so a crash handler cannot undo the hold
      paused      → add    <label>::pause, remove <label>::in-progress (manual
                    hold; refused for a closed or opted-out issue)
    """
    if status not in _VALID_STATUSES:
        return _err(f"Invalid status {status!r} – expected one of {_VALID_STATUSES}.")
    try:
        client = GitLabIssuesClient()
        if status == "in_progress":
            updated = client.lock_issue(issue_id)
        elif status == "closed":
            updated = client.close_issue(issue_id, note=note)
        elif status == "paused":
            updated = client.pause_issue(issue_id, note=note)
        else:  # "new"
            updated = client.reopen_issue(issue_id, note=note)
        if not updated:
            return _err(f"GitLab rejected the status update for issue #{issue_id}.")
        return _ok({"issue_id": issue_id, "status": status})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_set_status(%s, %s) failed: %s", issue_id, status, exc)
        return _err(exc)


def tool_project_layout() -> dict:
    """The orchestrator's resolved layout.json record (read-only)."""
    try:
        record = project_layout.load_layout()
        if record is None:
            return _err("layout.json not found: run nesti /arch on the orchestrator")
        return _ok(record)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_project_layout() failed: %s", exc)
        return _err(exc)


def tool_issue_create(title: str, description: str) -> dict:
    """
    Create one unlabelled issue (Nesti ignores it until handed off).
    result: {"id", "web_url", "labels"}.
    """
    if not title.strip() or not description.strip():
        return _err("title and description must be non-blank.")
    try:
        issue = GitLabIssuesClient().create_issue(title, description)
        return _ok({"id": issue["id"], "web_url": issue["web_url"], "labels": issue["labels"]})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_create() failed: %s", exc)
        return _err(exc)


def tool_issue_resolve(issue_id: int, model: str) -> dict:
    """
    Close an open, not-opted-in issue with the note ``omp-developer / model: <model>``.
    The issue stays open when the note cannot be posted.
    result: {"issue_id", "status": "closed", "comment"}.
    """
    model = model.strip()
    if not model or "\n" in model or len(model) > 200:
        return _err("model must be one non-blank line of at most 200 characters.")
    try:
        client = GitLabIssuesClient()
        issue = client.get_issue(issue_id)
        if issue["state"] != "opened":
            return _err(f"Issue #{issue_id} is not open.")
        if client.issue_label in issue["labels"]:
            return _err(f"Issue #{issue_id} was handed to Nesti.")
        comment = f"omp-developer / model: {model}"
        if not client.close_issue(issue_id, note=comment, require_note=True):
            return _err(f"GitLab rejected closing issue #{issue_id}.")
        return _ok({"issue_id": issue_id, "status": "closed", "comment": comment})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_resolve(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_handoff(issue_id: int, report: str) -> dict:
    """
    Append the rejection report to the issue and add the opt-in label.
    result: {"issue_id", "label"}.
    """
    if not report.strip():
        return _err("report must be non-blank.")
    try:
        client = GitLabIssuesClient()
        if not client.handoff_issue(
                issue_id,
                "## Third attempt (OMP team, advised) — rejected\n\n" + report.strip()):
            return _err(f"GitLab rejected the hand-off of issue #{issue_id}.")
        return _ok({"issue_id": issue_id, "label": client.issue_label})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_handoff(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_notes(issue_id: int) -> dict:
    """Non-system notes of an issue, oldest first: [{"id","author","created_at","body"}]."""
    try:
        return _ok(GitLabIssuesClient().list_notes(issue_id))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_notes(%s) failed: %s", issue_id, exc)
        return _err(exc)


def _fixture_dependencies() -> FixtureDependencies:
    """The dependency manager over the configured project and MR target branch."""
    return FixtureDependencies(GitLabIssuesClient(), GitLabClient().default_branch)


def tool_issue_pause_for_fixture(
    issue_id: int, repo_path: str, requirement: dict, written_files: list[str]
) -> dict:
    """
    Pause *issue_id* on a verified missing-seeder fixture and open its backend
    dependency issue once.  Graph-internal: deliberately not exposed over MCP,
    where a second process would become a second dependency writer and could
    hand in caller-invented evidence.

    result: {"status": "paused", "child_iid": int | None, "reason": str}
          | {"status": "ineligible" | "error", "reason": str}
    """
    try:
        return _ok(_fixture_dependencies().pause_for_fixture(
            issue_id, repo_path, requirement, written_files
        ))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_pause_for_fixture(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_reconcile_dependencies() -> dict:
    """
    Advance every open opted-in issue's fixture dependency record: link or
    create children, observe merged MRs, resume released parents.  Runs before
    every pending-issue selection; graph-internal like the pause tool.

    result: {"resumed": [iid], "waiting": [iid], "errors": [{"issue_id", "error"}]}
    success=False only when the issues could not be listed at all.
    """
    try:
        return _ok(_fixture_dependencies().reconcile())
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_reconcile_dependencies() failed: %s", exc)
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


def _touches_api(written_files: "list[str] | None") -> bool:
    """
    True when the last code attempt changed the API surface.

    ``None`` means "caller does not know" — every MCP client and any unit test
    that omits the argument — and gets the conservative answer, True, so the
    document is verified rather than silently skipped.  An empty list means
    "nothing was written", which genuinely cannot touch the API.
    """
    if written_files is None:
        return True
    for raw in written_files:
        path = raw.replace("\\", "/").lstrip("./")
        if path == _API_ROUTES_FILE or path.startswith(_API_TOUCH_PREFIXES):
            return True
    return False


def _change_sides(written_files: "list[str] | None") -> tuple[bool, bool]:
    """
    ``(touches_backend, touches_frontend)`` for the paths the last attempt wrote.

    ``None`` means "caller does not know" and touches both — the conservative
    answer, as in ``_touches_api``.  A path on neither side (README.md,
    .gitignore, openapi.json) touches neither: the PHPUnit fallback in
    ``tool_detect_stack`` then keeps the change from reaching commit untested.
    """
    if written_files is None:
        return True, True
    backend = frontend = False
    for raw in written_files:
        path = raw.replace("\\", "/").removeprefix("./")
        name = path.rsplit("/", 1)[-1]
        if path.endswith(_SHARED_SUFFIXES) or path in _SHARED_FILES:
            backend = frontend = True
        elif path.endswith(".php") or name in _BACKEND_FILES:
            backend = True
        elif (path.endswith(_FRONTEND_SUFFIXES) or path.startswith(_FRONTEND_PREFIXES)
              or name in _FRONTEND_FILES):
            frontend = True
    return backend, frontend


def _under(files: "list[str] | None", folder: str) -> "list[str] | None":
    """*files* inside *folder*, relative to it; ``None`` stays ``None``."""
    if files is None or folder == ".":
        return files
    prefix = folder + "/"
    return [
        p[len(prefix):] for p in (f.replace("\\", "/").removeprefix("./") for f in files)
        if p.startswith(prefix)
    ]


def _detect_separated(
    workspace_path: str, written_files: "list[str] | None", backend_dir: str, frontend_dir: str
) -> dict:
    """``tool_detect_stack`` for a separated layout: each side gated on its own folder."""
    root = Path(workspace_path)
    backend = root / backend_dir
    is_laravel = (backend / _LARAVEL_MARKER).is_file()
    has_api_routes = (backend / _API_ROUTES_FILE).is_file()
    backend_files = _under(written_files, backend_dir)
    frontend_files = _under(written_files, frontend_dir) if frontend_dir else []
    run_openapi = is_laravel and has_api_routes and _touches_api(backend_files)

    override = os.environ.get("NESTI_STACK", "auto").strip().lower()
    if override in _VALID_STACKS:
        stack, source, vue_files = override, "override", []
        has_vue = stack in ("vue", "fullstack")
        has_php = stack in ("php", "fullstack")
    elif override not in ("", "auto"):
        return _err(
            f"Invalid NESTI_STACK={override!r} – expected 'auto' or one of {_VALID_STACKS}."
        )
    else:
        _, has_php = _scan_workspace(str(backend))
        vue_files = [
            f"{frontend_dir}/{f}" for f in _scan_workspace(str(root / frontend_dir))[0]
        ] if frontend_dir else []
        has_vue = bool(vue_files)
        stack = ("fullstack" if has_php else "vue") if has_vue else ("php" if has_php else "unknown")
        source = "auto"

    touches_backend = written_files is None or bool(backend_files)
    touches_frontend = bool(frontend_dir) and (written_files is None or bool(frontend_files))
    run_frontend = has_vue and touches_frontend
    run_phpunit = touches_backend or not run_frontend
    return _ok({
        "stack": stack,
        "has_vue": has_vue,
        "has_php": has_php,
        "run_phpunit": run_phpunit,
        "run_frontend": run_frontend,
        "vue_files": vue_files,
        "source": source,
        "is_laravel": is_laravel,
        "has_api_routes": has_api_routes,
        "run_openapi": run_openapi,
    })


def tool_detect_stack(
    workspace_path: str,
    written_files: "list[str] | None" = None,
    backend_dir: str = ".",
    frontend_dir: str = ".",
) -> dict:
    """
    Determine which test layers apply to the code in workspace_path.

    result: {"stack": str, "has_vue": bool, "has_php": bool,
             "run_phpunit": bool, "run_frontend": bool, "vue_files": list[str],
             "source": str, "is_laravel": bool, "has_api_routes": bool,
             "run_openapi": bool}

    ``stack`` is one of:
      "php"       – PHP sources or a Composer project, no .vue files
      "vue"       – .vue files and no PHP whatsoever (frontend-only repository)
      "fullstack" – both layers present
      "unknown"   – neither detected (empty or non-code change)

    ``stack`` describes the repository; the three ``run_*`` gates describe
    *this change* (*written_files*, the paths the last attempt wrote):

    ``run_frontend`` gates Vitest → Playwright.  It needs Vue in the
    repository and a change that touched the frontend (.vue, JavaScript, CSS,
    Blade views, routes/web.php, package.json, e2e/); a "vue" stack always
    runs it, since it is that stack's only gate.  A backend change in a
    repository that merely contains .vue files no longer starts two Node
    containers.

    ``run_phpunit`` gates the PHP layer.  It is False for the "vue" stack — a
    frontend-only workspace has no composer.json and no phpunit binary, so
    running the PHP layer there would fail on every attempt and drive the
    issue to permanent failure — and for a change that touched only frontend
    files while the frontend layers run: a .vue, CSS or JavaScript change
    cannot alter what PHPUnit executes.  Whenever the frontend layers do not
    run, PHPUnit does, so no change — "unknown" stack, README-only, a JS
    change in a repository without Vue — ever reaches commit untested.

    ``run_openapi`` is the same kind of gate for the Scramble layer and needs
    all three of: a Laravel app (``artisan``), a registered API surface
    (``routes/api.php``), and a change that actually touched that surface.
    Exporting the document for a pure .vue or migration change would only add
    a slow container to every attempt.

    Omitting *written_files* (MCP callers) yields the conservative answer for
    all three gates: every layer the repository supports runs.

    *backend_dir*/*frontend_dir* name the layout's folders ("." = root,
    frontend "" = no SPA); anything but "."/"." gates each side on its folder.

    Detection is automatic; set NESTI_STACK to php / vue / fullstack to pin the
    *stack* when a repository's layout misleads the scan.  NESTI_STACK never
    pins the Laravel markers: those are two cheap is_file() checks that cannot
    be misled.
    """
    try:
        if (backend_dir, frontend_dir) != (".", "."):
            return _detect_separated(workspace_path, written_files, backend_dir, frontend_dir)
        root = Path(workspace_path)
        is_laravel = (root / _LARAVEL_MARKER).is_file()
        has_api_routes = (root / _API_ROUTES_FILE).is_file()
        run_openapi = is_laravel and has_api_routes and _touches_api(written_files)

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

        touches_backend, touches_frontend = _change_sides(written_files)
        run_frontend = stack == "vue" or (has_vue and touches_frontend)
        run_phpunit = stack != "vue" and (touches_backend or not run_frontend)

        return _ok({
            "stack": stack,
            "has_vue": has_vue,
            "has_php": has_php,
            "run_phpunit": run_phpunit,
            "run_frontend": run_frontend,
            "vue_files": vue_files,
            "source": source,
            "is_laravel": is_laravel,
            "has_api_routes": has_api_routes,
            "run_openapi": run_openapi,
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_detect_stack(%s) failed: %s", workspace_path, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Laravel bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def _has_scramble(root: Path) -> bool:
    """True when dedoc/scramble is already part of the repository."""
    if (root / "config" / "scramble.php").is_file():
        return True
    composer = root / "composer.json"
    if composer.is_file():
        try:
            return "dedoc/scramble" in composer.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Could not read composer.json: %s", exc)
    return False


def _apply_templates(
    repo_path: str, names: tuple[str, ...], overwrite: bool, source_dir: Path = _TEMPLATES_DIR
) -> list[str]:
    """Copy bootstrap templates into the repository.  Returns the paths written."""
    applied: list[str] = []
    for rel in names:
        source = source_dir / rel
        if not source.is_file():
            raise FileNotFoundError(f"bootstrap template missing: {source}")
        dest = Path(repo_path, rel)
        if dest.exists() and not overwrite:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        applied.append(rel)
    return applied


def _merge_package_json(repo_path: str, overwrite: bool) -> list[str]:
    """
    Merge Nesti's frontend dependencies into the repository's package.json.

    Merging, never replacing: the Laravel skeleton's own ``vite``,
    ``laravel-vite-plugin``, ``tailwindcss`` and ``@tailwindcss/vite`` entries
    must survive, and a foreign repository's dependencies must not be touched.
    With *overwrite* False (top-up mode) only absent keys are added.
    """
    path = Path(repo_path, "package.json")
    data: dict = {}
    indent = 4
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw) or {}
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"package.json is not valid JSON: {exc}") from exc
        # Keep a foreign repository's indentation so the MR diff stays minimal.
        if match := re.search(r"\n( +)\"", raw):
            indent = len(match.group(1))

    changed: list[str] = []
    if overwrite:
        if data.get("type") != "module":
            data["type"] = "module"
            changed.append("type=module")
        data.setdefault("private", True)
    elif data.get("type") != "module":
        # Adding "type": "module" to a foreign repository would reinterpret
        # every existing .js file, so top-up mode only warns.
        logger.warning(
            'package.json has no "type": "module" – the ESM vitest/playwright '
            "configs added by top-up mode may fail to load."
        )

    for section, wanted in (
        ("dependencies", _PACKAGE_DEPENDENCIES),
        ("devDependencies", _PACKAGE_DEV_DEPENDENCIES),
        ("scripts", _PACKAGE_SCRIPTS),
    ):
        bucket = data.setdefault(section, {})
        for key, value in wanted.items():
            if key in bucket and not overwrite:
                continue
            if bucket.get(key) == value:
                continue
            bucket[key] = value
            changed.append(f"{section}.{key}")

    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def _append_gitignore(repo_path: str) -> list[str]:
    """Append the missing Nesti .gitignore lines.  Returns the lines added."""
    path = Path(repo_path, ".gitignore")
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    present = {line.strip() for line in existing.splitlines()}
    missing = [line for line in _GITIGNORE_LINES if line not in present]
    if not missing:
        return []
    separator = "" if (not existing or existing.endswith("\n")) else "\n"
    path.write_text(existing + separator + "\n".join(missing) + "\n", encoding="utf-8")
    return missing


def tool_laravel_bootstrap(repo_path: str, spa_path: str = "") -> dict:
    """
    Make *repo_path* a Laravel 13 + Scramble + PrimeVue application.

    result: {"created": bool, "mode": str, "reason": str, "output": str}

    Exactly three outcomes:

    • greenfield (no artisan, no composer.json) → mode "scaffold".
      Runs ``composer create-project laravel/laravel`` + ``install:api`` +
      ``composer require dedoc/scramble`` in the PHP sandbox, then writes every
      template over the skeleton (Nesti created those files seconds earlier, so
      overwriting is safe), merges package.json and appends .gitignore.

    • existing Laravel app (artisan present) → mode "top-up".  Never overwrites
      a file the repository already has: installs Scramble only when absent,
      writes only the missing test-runner configs and the Scramble wiring test,
      and adds only missing package.json keys.  vite.config.js,
      resources/js/app.js, resources/views/** and routes/** are never touched.

    • non-Laravel PHP project (composer.json without artisan) → success=False.
      Scaffolding a Laravel skeleton over a foreign application would destroy
      it, so this is reported as the configuration error it is.

    *spa_path* (separated layout: *repo_path* is the Laravel API folder) tops
    up the SPA folder instead: it skips the vite.config.js guard, writes only
    the Scramble wiring test into the backend and the absent
    vitest/playwright configs plus missing package.json keys into the SPA.
    """
    try:
        root = Path(repo_path)
        has_artisan = (root / _LARAVEL_MARKER).is_file()
        has_composer = (root / "composer.json").is_file()

        if not has_artisan and has_composer:
            return _err(
                "repository has composer.json but no artisan: not a Laravel app "
                "and not greenfield"
            )

        if not has_artisan and not spa_path:
            passed, output = DockerRunner().run_bootstrap(repo_path)
            if not passed:
                return _err(f"Laravel skeleton bootstrap failed:\n{output}")
            if not (root / _LARAVEL_MARKER).is_file():
                return _err(
                    "bootstrap reported success but no artisan file appeared in "
                    f"the repository:\n{output}"
                )
            applied = _apply_templates(repo_path, _SCAFFOLD_TEMPLATES, overwrite=True)
            package = _merge_package_json(repo_path, overwrite=True)
            ignored = _append_gitignore(repo_path)
            return _ok({
                "created": True,
                "mode": "scaffold",
                "reason": (
                    f"Laravel skeleton + Scramble scaffolded; {len(applied)} template(s), "
                    f"{len(package)} package.json key(s), {len(ignored)} .gitignore line(s)"
                ),
                "output": output,
            })

        # ── top-up: an existing Laravel application ──────────────────────────
        vite_config = root / "vite.config.js"
        if not spa_path and vite_config.is_file():
            vite_source = vite_config.read_text(encoding="utf-8", errors="replace")
            if "@vitejs/plugin-vue" not in vite_source:
                # Generating .vue files a repository cannot compile would burn
                # every retry on infrastructure the model cannot fix.
                return _err(
                    "existing vite.config.js has no @vitejs/plugin-vue — add Vue "
                    "support to the repository before running frontend issues"
                )

        notes: list[str] = []
        output = ""
        if not _has_scramble(root):
            passed, output = DockerRunner().run_scramble_install(repo_path)
            if not passed:
                return _err(f"dedoc/scramble installation failed:\n{output}")
            notes.append("installed dedoc/scramble")

        if spa_path:
            applied = _apply_templates(
                repo_path, ("tests/Feature/OpenApiDocumentationTest.php",), overwrite=False
            )
            ignored = _append_gitignore(repo_path)
            applied += [
                f"{Path(spa_path).name}/{rel}" for rel in _apply_templates(
                    spa_path, ("vitest.config.js", "playwright.config.js"),
                    overwrite=False, source_dir=_SPA_TEMPLATES_DIR,
                )
            ]
            package = _merge_package_json(spa_path, overwrite=False)
        else:
            applied = _apply_templates(repo_path, _TOPUP_TEMPLATES, overwrite=False)
            package = _merge_package_json(repo_path, overwrite=False)
            ignored = _append_gitignore(repo_path)
        if applied:
            notes.append("added " + ", ".join(applied))
        if package:
            notes.append(f"added {len(package)} package.json key(s)")
        if ignored:
            notes.append("extended .gitignore")

        return _ok({
            "created": False,
            "mode": "top-up",
            "reason": "; ".join(notes) if notes else "already fully wired",
            "output": output,
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_laravel_bootstrap(%s) failed: %s", repo_path, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI layer
# ─────────────────────────────────────────────────────────────────────────────

def _load_json_document(text: str):
    """
    Parse JSON that may be prefixed with PHP notices.

    ``php artisan route:list --json`` writes only JSON on a clean install, but
    a single deprecation notice on stdout would otherwise fail the whole layer
    for a reason the model cannot fix by rewriting its code.
    """
    try:
        return json.loads(text)
    except ValueError:
        for opener, closer in (("[", "]"), ("{", "}")):
            start = text.find(opener)
            end = text.rfind(closer)
            if 0 <= start < end:
                return json.loads(text[start:end + 1])
        raise


def _index_openapi_paths(document: dict) -> tuple[dict, list[str]]:
    """
    Return ``(lookup, full_paths)`` for the exported OpenAPI document.

    Scramble serves the document with the API prefix in ``servers[0].url`` and
    the path keys relative to it, so ``/api/tasks`` is stored as ``/tasks``.
    The lookup therefore holds both the raw key and the server-prefixed form:
    the gate must detect a genuinely *missing* route, never a convention
    difference in where the prefix lives.
    """
    raw = document.get("paths") or {}
    prefix = ""
    servers = document.get("servers") or []
    if servers and isinstance(servers[0], dict):
        prefix = urlsplit(str(servers[0].get("url", ""))).path.rstrip("/")

    lookup: dict[str, dict] = {}
    full_paths: list[str] = []
    for key, item in raw.items():
        if not isinstance(item, dict):
            continue
        prefixed = key if (not prefix or key.startswith(prefix)) else prefix + key
        for form in {key, prefixed}:
            lookup.setdefault(form, item)
        full_paths.append(prefixed)
    return lookup, sorted(set(full_paths))


def _expected_api_routes(routes: list) -> list[tuple[str, list[str]]]:
    """Extract ``(openapi_path, methods)`` for every route under /api."""
    expected: list[tuple[str, list[str]]] = []
    for entry in routes:
        if not isinstance(entry, dict):
            continue
        uri = str(entry.get("uri") or "").strip().strip("/")
        if uri != "api" and not uri.startswith("api/"):
            continue
        # Laravel writes optional parameters as {task?}; OpenAPI has no such
        # notation and Scramble emits {task}.
        path = "/" + uri.replace("?}", "}")
        methods = [
            method
            for method in str(entry.get("method") or "").split("|")
            if method and method not in _IMPLICIT_METHODS
        ]
        if methods:
            expected.append((path, methods))
    return expected


def _is_prefixed(routes: list) -> bool:
    """True when any registered URI lives under /api (the conventional apiPrefix)."""
    for entry in routes:
        uri = str(entry.get("uri") or "").strip().strip("/") if isinstance(entry, dict) else ""
        if uri == "api" or uri.startswith("api/"):
            return True
    return False


def _route_keys(routes: list) -> set[str]:
    """``"METHOD uri"`` for every explicit verb of every route-list entry."""
    keys: set[str] = set()
    for entry in routes:
        if isinstance(entry, dict):
            uri = str(entry.get("uri") or "").strip().strip("/")
            keys.update(f"{method} {uri}" for method in str(entry.get("method") or "").split("|")
                        if method and method not in _IMPLICIT_METHODS)
    return keys


def _new_api_group_routes(routes: list, baseline: list[str]) -> list[tuple[str, list[str]]]:
    """``(openapi_path, methods)`` for ``api``-group routes absent from the HEAD route list."""
    known = set(baseline)
    expected: list[tuple[str, list[str]]] = []
    for entry in routes:
        if not isinstance(entry, dict) or "api" not in (entry.get("middleware") or []):
            continue
        uri = str(entry.get("uri") or "").strip().strip("/")
        methods = [
            method for method in str(entry.get("method") or "").split("|")
            if method and method not in _IMPLICIT_METHODS and f"{method} {uri}" not in known
        ]
        if methods:
            expected.append(("/" + uri.replace("?}", "}"), methods))
    return expected


def _head_route_list(workspace_path: str) -> list[str]:
    """
    Export the clone's HEAD route list as sorted ``"METHOD uri"`` strings.

    A detached worktree of HEAD under /tmp (host-identical, like every sandbox
    mount) gets its own route:list run; the clone itself is never touched and
    the worktree is removed in ``finally``. Raises when the list cannot be
    produced — the caller fails closed.
    """
    repo = git.Repo(workspace_path, search_parent_directories=True)
    relative = Path(workspace_path).resolve().relative_to(Path(repo.working_tree_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="nesti-head-", dir="/tmp", ignore_cleanup_errors=True) as tmp:
        head = Path(tmp, "head")
        repo.git.worktree("add", "--detach", str(head), "HEAD")
        try:
            ok, output = DockerRunner().run_route_list(str(head / relative))
            dump = head / relative / _ROUTE_DUMP_REL
            if not ok or not dump.is_file():
                raise RuntimeError(f"route:list failed at HEAD:\n{output[-2000:]}")
            routes = _load_json_document(dump.read_text(encoding="utf-8"))
        finally:
            repo.git.worktree("remove", "--force", str(head))
            repo.git.worktree("prune")
    return sorted(_route_keys(routes if isinstance(routes, list) else []))


def tool_openapi_export(workspace_path: str, baseline_routes: list[str] | None = None) -> dict:
    """
    Export the OpenAPI document and verify the API routes are documented.

    result: {"passed": bool, "output": str, "paths": list[str],
             "undocumented": list[str], "baseline_routes": list[str]}
             (``baseline_routes`` only for an unprefixed project)

    This is the gate: ``php artisan scramble:export`` writes ``openapi.json``
    and ``php artisan route:list --json`` writes the registered surface, then
    the two are compared.  ``scramble:analyze`` runs advisory-only inside the
    container — it exits non-zero on any unresolved type anywhere in the
    application, including pre-existing code, so gating on it would strand
    every issue.  Its output still reaches the model through ``output``.

    A project with routes under /api must document every one of them. A
    project whose ``apiPrefix`` is not ``api`` must document every ``api``-group
    route the change added: routes absent from the HEAD route list
    (*baseline_routes*, exported via ``_head_route_list`` when not supplied
    and returned for the caller to cache). Routes already registered at HEAD
    are not re-checked; a failed HEAD export fails the gate.

    A failing comparison appends the undocumented routes to ``output`` so the
    retry prompt names exactly what to fix.
    """
    try:
        _, output = DockerRunner().run_openapi_export(workspace_path)
        root = Path(workspace_path)

        document_path = root / "openapi.json"
        if not document_path.is_file():
            return _ok({
                "passed": False,
                "output": f"{output}\n\nopenapi.json was not produced by the export step.",
                "paths": [],
                "undocumented": [],
            })
        try:
            document = _load_json_document(document_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pylint: disable=broad-except
            return _ok({
                "passed": False,
                "output": f"{output}\n\nopenapi.json is not valid JSON: {exc}",
                "paths": [],
                "undocumented": [],
            })

        lookup, full_paths = _index_openapi_paths(document if isinstance(document, dict) else {})
        if not lookup:
            return _ok({
                "passed": False,
                "output": f"{output}\n\nThe exported OpenAPI document contains no paths.",
                "paths": [],
                "undocumented": [],
            })

        routes_path = root / _ROUTE_DUMP_REL
        if not routes_path.is_file():
            return _ok({
                "passed": False,
                "output": (
                    f"{output}\n\n{_ROUTE_DUMP_REL} was not produced: the documented "
                    "surface could not be verified against the registered routes."
                ),
                "paths": full_paths,
                "undocumented": [],
            })
        try:
            routes = _load_json_document(routes_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pylint: disable=broad-except
            return _ok({
                "passed": False,
                "output": f"{output}\n\nroute:list output is not valid JSON: {exc}",
                "paths": full_paths,
                "undocumented": [],
            })

        route_list = routes if isinstance(routes, list) else []
        extra: dict = {}
        if _is_prefixed(route_list):
            expected = _expected_api_routes(route_list)
            if not expected:
                return _ok({
                    "passed": False,
                    "output": (
                        f"{output}\n\nThe change touches API code but no route under "
                        "/api is registered."
                    ),
                    "paths": full_paths,
                    "undocumented": [],
                })
        else:
            try:
                if baseline_routes is None:
                    baseline_routes = _head_route_list(workspace_path)
            except Exception as exc:  # pylint: disable=broad-except
                return _ok({
                    "passed": False,
                    "output": (
                        f"{output}\n\nCould not export the HEAD route list to find the "
                        f"routes this change added: {exc}"
                    ),
                    "paths": full_paths,
                    "undocumented": [],
                })
            extra = {"baseline_routes": baseline_routes}
            expected = _new_api_group_routes(route_list, baseline_routes)
            if not expected:
                output += "\n\nNo new API route; routes registered at HEAD are not re-checked."

        undocumented: list[str] = []
        for path, methods in expected:
            item = lookup.get(path)
            for method in methods:
                if not item or method.lower() not in item:
                    undocumented.append(f"{method} {path}")

        if undocumented:
            output = (
                f"{output}\n\nUndocumented API routes:\n"
                + "\n".join(f"- {route}" for route in undocumented)
            )

        return _ok({
            "passed": not undocumented,
            "output": output,
            "paths": full_paths,
            "undocumented": undocumented,
            **extra,
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_openapi_export(%s) failed: %s", workspace_path, exc)
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
    result: {"passed": bool, "output": str, "fixture_request": dict | None}.

    The sandbox prepares a Laravel app's database and the fixtures declared in
    e2e/nesti-fixtures.json, builds the app, and Playwright's webServer config
    serves it; no server needs to be running beforehand.  ``fixture_request``
    is the declared requirement (endpoint, model, seeder, table) whose seeder
    class and file are both absent — set only when the helper verified that
    and stopped before the browser started; None for every other outcome.
    """
    try:
        return _ok(FrontendRunner().run_playwright(workspace_path))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_playwright_run_tests(%s) failed: %s", workspace_path, exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Skill tools
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


def tool_skill_catalog_select(
    text: str,
    max_component_docs: int = 3,
    max_topic_docs: int = 2,
    max_practice_docs: int = 1,
) -> dict:
    """
    Select vendored PrimeVue / Laravel / practice docs matching *text*.
    result: list of Skill objects (same in-process dataclass exception as
    tool_skill_fetch — the MCP wrapper serialises them).

    Deterministic and offline: the corpus in ``skills/`` is generated once by
    ``scripts/fetch_skills.py`` and selection is pure alias/trigger matching,
    so the same issue text always yields the same documentation.
    """
    try:
        return _ok(
            select_skills(
                text,
                max_component_docs=max_component_docs,
                max_topic_docs=max_topic_docs,
                max_practice_docs=max_practice_docs,
            )
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_skill_catalog_select failed: %s", exc)
        return _err(exc)


def tool_skill_catalog_status() -> dict:
    """
    Report whether the vendored skill corpus is present and how large it is.
    result: {"available": bool, "components": int, "topics": int,
             "practices": int, "primevue_version": str, "laravel_branch": str}.
    """
    try:
        return _ok(catalog_status())
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_skill_catalog_status failed: %s", exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# Hierarchical vector memory
# ─────────────────────────────────────────────────────────────────────────────
#
# Disabled memory is not an error.  When a backing store reports
# ``available is False`` (Qdrant not running, pre-8 Redis, embedder missing,
# NESTI_MEMORY_ENABLED=false) the read tools return an empty list and the
# write tools ``{"stored": False, "reason": "memory unavailable"}``, both with
# success=True.  success=False is reserved for a genuine exception — otherwise
# every attempt of every issue would log a warning on an install that simply
# chose not to run the memory layer.
#
# The two stores are process-wide singletons constructed on first call, so
# importing this module performs no network I/O.

_MEMORY_UNAVAILABLE = {"stored": False, "reason": "memory unavailable"}


def tool_memory_search_docs(text: str, stack: str = "", limit: int = 6) -> dict:
    """
    Semantic search over the vendored skills/ corpus indexed in Qdrant.
    stack "php" / "vue" narrows the search to Laravel / PrimeVue docs; any
    other value searches both stacks and interleaves them rank by rank, so
    the PrimeVue-heavy corpus cannot crowd out the Laravel docs.
    result: [{"doc_title", "doc_url", "doc_path", "source", "stack",
              "heading", "text", "score"}, ...]; [] when unavailable.
    """
    try:
        memory = get_document_memory()
        if not memory.available:
            return _ok([])
        return _ok(memory.search(text, stack=stack, limit=limit))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_search_docs failed: %s", exc)
        return _err(exc)


def tool_memory_find_similar(text: str, limit: int = 2) -> dict:
    """
    Previously merged issues similar to *text* (Redis solution cache).
    result: [{"issue_id", "subject", "plan", "mr_url", "stack", "similarity"},
             ...] most similar first, above NESTI_SOLUTION_MIN_SCORE.
    """
    try:
        memory = get_semantic_memory()
        if not memory.available:
            return _ok([])
        return _ok(memory.find_similar_solutions(text, limit=limit))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_find_similar failed: %s", exc)
        return _err(exc)


def tool_memory_remember_solution(
    issue_id: int, subject: str, description: str, plan: str, stack: str, mr_url: str
) -> dict:
    """
    Store the plan that produced a merged issue in the solution cache.
    result: {"stored": bool} (plus "reason" when not stored).
    """
    try:
        memory = get_semantic_memory()
        if not memory.available:
            return _ok(dict(_MEMORY_UNAVAILABLE))
        stored = memory.remember_solution(issue_id, subject, description, plan, stack, mr_url)
        return _ok({"stored": True} if stored else {"stored": False, "reason": "write failed"})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_remember_solution(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_remember_failure(issue_id: int, attempt: int, layer: str, output: str) -> dict:
    """
    Store one failed attempt of an issue in episodic memory.
    result: {"stored": bool} (plus "reason" when not stored).
    """
    try:
        memory = get_semantic_memory()
        if not memory.available:
            return _ok(dict(_MEMORY_UNAVAILABLE))
        stored = memory.remember_failure(issue_id, attempt, layer, output)
        return _ok({"stored": True} if stored else {"stored": False, "reason": "write failed"})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_remember_failure(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_recall_failures(issue_id: int, text: str, attempt: int, limit: int = 2) -> dict:
    """
    Older failed attempts of an issue similar to *text*.  ``attempt`` is the
    attempt about to run; the one that just failed (attempt - 1) is excluded
    because its output is already in the conversation history.
    result: [{"issue_id", "attempt", "layer", "summary", "similarity"}, ...].
    """
    try:
        memory = get_semantic_memory()
        if not memory.available:
            return _ok([])
        return _ok(memory.recall_failures(issue_id, text, attempt=attempt, limit=limit))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_recall_failures(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_forget_episodes(issue_id: int) -> dict:
    """
    Drop every episodic-memory row of an issue.  result: {"deleted": int}.
    """
    try:
        return _ok({"deleted": get_semantic_memory().forget_episodes(issue_id)})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_forget_episodes(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_status() -> dict:
    """
    Report both memory tiers.
    result: {"qdrant": {"available", "url", "collection", "points", "model",
                        "dim", "error"},
             "redis": {"available", "url", "solutions", "episodes", "engine"}}.
    Counts are None, never guessed, when they cannot be read.
    """
    try:
        return _ok({
            "qdrant": get_document_memory().status(),
            "redis": get_semantic_memory().status(),
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_status failed: %s", exc)
        return _err(exc)



# ─────────────────────────────────────────────────────────────────────────────
# OAuth consumer-provider quota
# ─────────────────────────────────────────────────────────────────────────────

def tool_quota_check() -> dict:
    """
    Report remaining usage/quota for every OAuth consumer provider
    (scripts/oauth.py) authenticated via '/provider login'.
    result: {"<provider>": {"remaining": int | None, "limit": int | None,
             "reset_time": ISO-8601 str | None, ...}, ...} — claude,
             antigravity and chatgpt-plus add "windows" (label /
             used_percent / resets_at per rate-limit window). A provider
             never logged in is omitted, never reported with a fake value.
             Credentials renewed on the way are persisted
             (scripts.oauth.fetch_usage).

    node_on_layer_failure calls this instead of importing scripts.oauth
    directly, so the quota check follows the same nodes.py -> tools.py
    {"success": bool, ...} contract as every other tool_* here and stays
    reachable from MCP clients, which only ever wrap this module.
    """
    try:
        store = TokenStore()
        usage_by_provider = {
            name: fetch_usage(store, name, token_data)
            for name, token_data in store.get_all_tokens().items()
        }
        return _ok(usage_by_provider)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_quota_check failed: %s", exc)
        return _err(exc)
stats.instrument(globals())  # record tool_* runs for nesti /stats
