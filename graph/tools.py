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
from pathlib import Path
from urllib.parse import urlsplit

import git

from docker_runner import DockerRunner
from frontend_runner import FrontendRunner
from gitlab_client import GitLabClient
from gitlab_issues_client import GitLabIssuesClient
from issue_dependencies import FixtureDependencies
from project_architecture import collect_inventory, inventory_listing
from scripts.oauth import TokenStore, fetch_usage
from semantic_cache import get_semantic_memory
from skill_catalog import catalog_status, select_skills
from skill_loader import load_skills
from vector_store import get_document_memory

logger = logging.getLogger(__name__)

_ISSUE_LIST_LIMIT = 25
_REQUEST_TIMEOUT = 15  # seconds, matches the clients' own timeouts


# Markers that prove a layer is present even before any source file matches.
_PHP_PROJECT_FILES = ("composer.json", "composer.lock")

_LARAVEL_MARKER = "artisan"
_API_ROUTES_FILE = "routes/api.php"


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
    """Detect owned Vue/PHP sources using the shared pruned, secret-free listing."""
    files = inventory_listing(Path(workspace_path))
    return (
        [path for path in files if path.endswith(".vue")],
        any(path.endswith(".php") or path in _PHP_PROJECT_FILES for path in files),
    )


def _routing_metadata(inventory: dict, application_root: str = "") -> dict:
    """Find literal route registrations without executing PHP; uncertainty stays explicit."""
    files = inventory["files"]
    roots = [
        item["path"].rstrip("/") for item in inventory["psr4"]
        if item["resolved"] and not item["dev"]
    ]
    if not roots:
        roots = [(Path(application_root) / "app").as_posix()]
    routes: dict[str, set[str]] = {}
    registrations: set[str] = set()
    unresolved: set[str] = set()
    for path, kind in (("routes/api.php", "api"), ("routes/web.php", "web")):
        path = (Path(application_root) / path).as_posix()
        if path in files:
            routes[path] = {kind}
    for path, entry in files.items():
        if not path.endswith(".php"):
            continue
        body = entry["content"]
        if not re.search(r"withRouting\s*\(|loadRoutesFrom\s*\(|Route::|->group\s*\(", body):
            continue
        registrations.add(path)
        if "Route::" in body:
            kinds = routes.setdefault(path, set())
            if re.search(r"""(?:prefix|middleware)\s*\(\s*['"]api['"]|['"]/api(?:/|['"])""", body):
                kinds.add("api")
            if re.search(r"\b(?:Route::view|view)\s*\(", body):
                kinds.add("web")
            if not kinds:
                kinds.add("unknown")
        found = False
        for match in re.finditer(
            r"""(?:(?P<base>base_path|resource_path|app_path)\s*\(\s*|(?P<directory>__DIR__)\s*\.\s*)?['"](?P<path>[^'"]+\.php)['"]""",
            body,
        ):
            literal = match["path"]
            if match["base"]:
                prefix = {"base_path": "", "resource_path": "resources", "app_path": "app"}[match["base"]]
                candidate = Path(application_root) / prefix / literal.lstrip("/")
            elif match["directory"]:
                candidate = Path(path).parent / literal.lstrip("/")
            elif literal.startswith("/"):
                unresolved.add(path)
                continue
            else:
                candidate = Path(application_root) / literal
            relative = os.path.normpath(candidate.as_posix()).replace("\\", "/")
            if relative.startswith("../") or relative not in files:
                unresolved.add(path)
                continue
            context = body[max(body.rfind(";", 0, match.start()), 0):match.start()]
            kind = "unknown"
            if re.search(r"""\bapi\s*:|(?:prefix|middleware)\s*\(\s*['"]api['"]""", context):
                kind = "api"
            elif re.search(r"""\bweb\s*:|middleware\s*\(\s*['"]web['"]""", context):
                kind = "web"
            routes.setdefault(relative, set()).add(kind)
            found = True
        if (
            not found and re.search(r"withRouting\s*\(|loadRoutesFrom\s*\(|->group\s*\(", body)
            and path not in routes
        ) or re.search(r"(?:loadRoutesFrom|->group)\s*\(\s*\$", body):
            unresolved.add(path)
    if inventory["unresolved"]:
        unresolved.add((Path(application_root) / "composer.json").as_posix())
    if not routes:
        unresolved.add((Path(application_root) / "bootstrap/app.php").as_posix())
    return {"roots": roots, "routes": routes, "registrations": registrations, "unresolved": unresolved}


def _touches_api(written_files: list[str] | None, routing: dict) -> bool:
    """Gate custom HTTP roots and routes, conservatively retaining unresolved PHP changes."""
    if written_files is None:
        return True
    for raw in written_files:
        path = raw.replace("\\", "/").removeprefix("./")
        parts = set(Path(path).parts)
        if parts & {"migrations", "factories", "seeders", "tests", "Tests"} or path.endswith("Test.php"):
            continue
        kinds = routing["routes"].get(path, set())
        if kinds & {"api", "unknown"}:
            return True
        in_source = any(not root or path.startswith(root + "/") for root in routing["roots"])
        if in_source and re.search(r"(?:^|/)Http/(?:Controllers|Resources|Requests)/", path):
            return True
        if path in routing["unresolved"]:
            return True
        if routing["unresolved"] and in_source and path.endswith(".php"):
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


def tool_detect_stack(
    workspace_path: str, written_files: "list[str] | None" = None, *,
    application_root: str | None = None, frontend_root: str = "",
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

    ``run_openapi`` follows registered API routes and HTTP classes under
    Composer roots. Unresolved PHP routing is checked conservatively against
    the actual route:list API surface, even without routes/api.php.

    Omitting *written_files* (MCP callers) yields the conservative answer for
    all three gates: every layer the repository supports runs.

    NESTI_STACK pins descriptive stack detection, never the source-based API gate.
    """
    try:
        if application_root is not None:
            root = Path(workspace_path).resolve()
            backend = root / application_root
            frontend = root / frontend_root if frontend_root else None
            for directory in (backend, frontend):
                if directory is not None and (
                    not directory.is_dir() or directory.absolute() != directory.resolve()
                    or not directory.resolve().is_relative_to(root)
                ):
                    return _err("Configured application directory is absent or unsafe.")
            if frontend is not None and (
                frontend.is_relative_to(backend) or backend.is_relative_to(frontend)
            ):
                return _err("Backend and frontend directories must not overlap.")

            def relative_changes(directory: Path) -> list[str] | None:
                if written_files is None:
                    return None
                prefix = directory.relative_to(root)
                return [
                    Path(raw.replace("\\", "/")).relative_to(prefix).as_posix()
                    for raw in written_files
                    if Path(raw.replace("\\", "/")).is_relative_to(prefix)
                ]

            backend_files = relative_changes(backend)
            detected = tool_detect_stack(str(backend), backend_files)
            if not detected["success"]:
                return detected
            result = detected["result"]
            frontend_files = relative_changes(frontend) if frontend is not None else []
            run_frontend = frontend is not None and (
                frontend_files is None or bool(frontend_files)
            )
            vue_files = _scan_workspace(str(frontend))[0] if frontend is not None else []
            return _ok({
                **result,
                "stack": "fullstack" if frontend is not None else "php",
                "has_php": True,
                "has_vue": bool(vue_files),
                "vue_files": [str(Path(frontend_root) / path) for path in vue_files],
                "run_frontend": run_frontend,
                "run_phpunit": backend_files is None or bool(backend_files) or not run_frontend,
            })
        root = Path(workspace_path)
        is_laravel = (root / _LARAVEL_MARKER).is_file()
        routing = _routing_metadata(collect_inventory(workspace_path))
        has_api_routes = any(kinds & {"api", "unknown"} for kinds in routing["routes"].values())
        run_openapi = is_laravel and bool(has_api_routes or routing["unresolved"]) and _touches_api(written_files, routing)

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
        if written_files is not None and has_vue:
            for raw in written_files:
                path = raw.replace("\\", "/").removeprefix("./")
                if routing["routes"].get(path, set()) & {"web", "unknown"} or path in routing["unresolved"]:
                    touches_backend = touches_frontend = True
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


def _apply_templates(repo_path: str, names: tuple[str, ...], overwrite: bool) -> list[str]:
    """Copy bootstrap templates into the repository.  Returns the paths written."""
    applied: list[str] = []
    for rel in names:
        source = _TEMPLATES_DIR / rel
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
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"package.json is not valid JSON: {exc}") from exc

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

    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
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


def tool_laravel_bootstrap(repo_path: str) -> dict:
    """Scaffold greenfield Laravel apps; preserve the installed stack of existing apps.

    result: {"created": bool, "mode": str, "reason": str, "output": str}

    Exactly three outcomes:

    • greenfield (no artisan, no composer.json) → mode "scaffold".
      Runs ``composer create-project laravel/laravel`` + ``install:api`` +
      ``composer require dedoc/scramble`` in the PHP sandbox, then writes every
      template over the skeleton (Nesti created those files seconds earlier, so
      overwriting is safe), merges package.json and appends .gitignore.

    • existing Laravel app (artisan present) → mode "top-up". Install Scramble
      only when absent and add absent test configs without replacing custom
      configuration. Backend-only applications receive no frontend scaffolding
      or dependencies; existing packages, routes, entries and themes stay intact.

    • non-Laravel PHP project (composer.json without artisan) → success=False.
      Scaffolding a Laravel skeleton over a foreign application would destroy
      it, so this is reported as the configuration error it is.
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

        if not has_artisan:
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
        notes: list[str] = []
        output = ""
        if not _has_scramble(root):
            passed, output = DockerRunner().run_scramble_install(repo_path)
            if not passed:
                return _err(f"dedoc/scramble installation failed:\n{output}")
            notes.append("installed dedoc/scramble")

        vue_files, _ = _scan_workspace(repo_path)
        templates = ["tests/Feature/OpenApiDocumentationTest.php"]
        if vue_files:
            for name in _TOPUP_TEMPLATES[:2]:
                stem = name.removesuffix(".js")
                if not any((root / (stem + suffix)).exists() for suffix in (".js", ".ts", ".mjs", ".mts", ".cjs", ".cts")):
                    templates.append(name)
        applied = _apply_templates(repo_path, tuple(templates), overwrite=False)
        if applied:
            notes.append("added " + ", ".join(applied))
        ignored = _append_gitignore(repo_path)
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


def tool_openapi_export(workspace_path: str) -> dict:
    """
    Export the OpenAPI document and verify every /api route is documented.

    result: {"passed": bool, "output": str, "paths": list[str],
             "undocumented": list[str]}

    This is the gate: ``php artisan scramble:export`` writes ``openapi.json``
    and ``php artisan route:list --json`` writes the registered surface, then
    the two are compared.  ``scramble:analyze`` runs advisory-only inside the
    container — it exits non-zero on any unresolved type anywhere in the
    application, including pre-existing code, so gating on it would strand
    every issue.  Its output still reaches the model through ``output``.

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

        expected = _expected_api_routes(routes if isinstance(routes, list) else [])
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
              "heading", "text", "score", "version", "doc_hash", "chunk_index"}, ...]; [] when unavailable.
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
    MR-opened precedents similar to *text*; merge status is unverified.
    result: [{"issue_id", "subject", "plan", "mr_url", "stack", "similarity", "created_at"},
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
    Store the plan that opened an MR, without claiming it has merged.
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
    result: [{"issue_id", "attempt", "layer", "summary", "similarity", "created_at"}, ...].
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
             "redis": {"available", "url", "solutions", "episodes", "engine", "namespace"}}.
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


def tool_project_architecture() -> dict:
    """Read verified configured-project structure and current evidence; never write or infer."""
    try:
        from project_context import configured_project_root, inspect_project
        from project_architecture import collect_architecture

        root = str(configured_project_root())
        return _ok(collect_architecture(root, inspect_project(root)))
    except Exception as exc:
        return _err(exc)


def tool_issue_history(project_id: int, issue_id: int) -> dict:
    """Read project-scoped history with trusted-author and escalation-phase metadata."""
    from issue_escalations import issue_history

    return issue_history(project_id, issue_id)


def tool_issue_escalation_create(project_id: int, operation_id: str, report: dict) -> dict:
    """Create or recover one verified unlabeled assisted issue after two rejections."""
    from issue_escalations import issue_escalation_create

    return issue_escalation_create(project_id, operation_id, report)


def tool_issue_escalation_complete(
    project_id: int, issue_id: int, operation_id: str, model: str, review: dict
) -> dict:
    """Verify actual developer-model attribution before closing an approved third attempt."""
    from issue_escalations import issue_escalation_complete

    return issue_escalation_complete(project_id, issue_id, operation_id, model, review)


def tool_issue_escalation_handoff(
    project_id: int, issue_id: int, operation_id: str, report: dict
) -> dict:
    """Verify failure evidence then transfer intake to Nesti for clean reimplementation."""
    from issue_escalations import issue_escalation_handoff

    return issue_escalation_handoff(project_id, issue_id, operation_id, report)
