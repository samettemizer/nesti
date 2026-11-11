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
• The repository client's create_branch / commit_and_push operate on a ``git.Repo``
  object.  Because MCP tools may only accept plain arguments, these wrappers
  re-open the repository from ``repo_path`` internally.

• tool_skill_fetch and tool_skill_catalog_select return ``skill_loader.Skill``
  dataclass instances in ``result`` because prompt_builder (unchanged per
  spec) consumes them by attribute.  When these tools are exposed over MCP,
  serialise with ``dataclasses.asdict`` at the transport boundary.

• tool_laravel_bootstrap and tool_starter_kit are the only tools that *write*
  into the repository besides DockerRunner.write_files.  They apply the
  templates shipped in ``templates/laravel/`` and ``templates/starter/``: a
  greenfield repository becomes a Laravel 13 API in ``webservice/``, and
  a SPA-less Laravel API gains a Sakai PrimeVue SPA, inside a single run.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import git

from docker_runner import _PG_IDENTIFIER, APP_FACTS_MARK, DockerRunner, _pgsql_settings
from frontend_runner import FrontendRunner
import forge
from scripts.oauth import TokenStore, fetch_usage
from semantic_cache import get_semantic_memory
import issue_domain
from layer_output import condense
import project_layout
from skill_catalog import catalog_status, select_skills
from skill_loader import load_skills
import stats
import starter_kit
from vector_store import get_document_memory

logger = logging.getLogger(__name__)

_ISSUE_LIST_LIMIT = 25
_REQUEST_TIMEOUT = 15  # seconds, matches the clients' own timeouts

# Directories never treated as project source during stack detection.
# ``node_modules`` is the load-bearing entry: MCP callers may pass host projects
# with installed dependencies — and Vue component libraries ship thousands of .vue
# files.  Without pruning, every scan would report has_vue=True and the walk
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

# A written path matching this makes the OpenAPI layer applicable.  A pure
# .vue or migration change must not pay for a Scramble export.  A route file
# under routes/<dir>/ counts (api.php loads such files; a web subdir only
# costs one export), and so do the Http layers inside a domain.
_API_TOUCH_RE = re.compile(
    r"^(?:routes/api\.php$|routes/.+/[^/]+\.php$|app/(?:[^/]+/)*Http/(?:Controllers|Resources|Requests)/)"
)

# Written by the openapi recipe; storage/app is git-ignored by Laravel, so the
# route dump never lands in the MR/PR.
_ROUTE_DUMP_REL = "storage/app/nesti-routes.json"

# HTTP verbs Laravel registers implicitly; they never appear in OpenAPI.
_IMPLICIT_METHODS = frozenset({"HEAD", "OPTIONS"})

# Bootstrap templates shipped with Nesti, keyed by their repo-relative
# destination.  Scaffold mode writes all of them over the skeleton Nesti just
# created; top-up mode writes only the OpenAPI test, and only when absent.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "laravel"
_SPA_TEMPLATES_DIR = _TEMPLATES_DIR.parent / "spa"

_SCAFFOLD_TEMPLATES = (
    "routes/api.php",
    "tests/Feature/OpenApiDocumentationTest.php",
    # API-only welcome page: no @vite, so the skeleton's GET / test passes without a build.
    "resources/views/welcome.blade.php",
    "database/seeders/DatabaseSeeder.php",
)

_SPA_TOPUP_TEMPLATES = ("vitest.config.js", "vitest.setup.js", "playwright.config.js")
# sha256 of SPA vitest.config.js versions Nesti shipped earlier; an unmodified copy is upgraded in place.
_SUPERSEDED_SPA_VITEST_CONFIGS = frozenset({"f4c1fb28348a6682d655e8ed89421e76fd55c50624ae735b49625fc9e1e29f54"})

_PACKAGE_DEPENDENCIES = {
    "vue": "^3.5.0",
    "primevue": "^5.0.0",
    # @primevue/themes is deprecated; @primeuix/themes is the PrimeVue 5 home
    # of the Aura preset an SPA's src/main.* registers.
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
# so without this the database would land in the MR/PR.  openapi.json
# is deliberately absent: it is a committed deliverable.
_GITIGNORE_LINES = ("/database/*.sqlite*", "/.phpunit.cache")

_VALID_STACKS = ("php", "vue", "fullstack")

# Intake lifecycle vocabulary. Neither forge has an "in progress" or "paused"
# issue state, so the issue clients express these words as labels plus
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
# Issue intake tools (the forge's issues)
# ─────────────────────────────────────────────────────────────────────────────

def tool_issue_get(issue_id: int) -> dict:
    """
    Fetch one issue by its project-scoped iid.
    result: {"id", "subject", "description", "iid", "state", "labels",
             "web_url", "author", "global_id"}.
    """
    try:
        return _ok(forge.issue_client().get_issue(issue_id))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_get(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_list_pending() -> dict:
    """
    List pending issues for the configured project, oldest first.
    result: list of issue dicts (possibly empty).

    Pending means: open, carrying the opt-in GITLAB_ISSUE_LABEL and carrying
    neither the ``<label>::in-progress`` lock nor the ``<label>::pause`` hold.
    """
    try:
        return _ok(forge.issue_client().list_pending(limit=_ISSUE_LIST_LIMIT))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_list_pending() failed: %s", exc)
        return _err(exc)


def tool_issue_set_status(issue_id: int, status: str, note: str = "") -> dict:
    """
    Move an issue through the intake lifecycle.
    status: "in_progress" | "closed" | "new" | "paused"
    result: {"issue_id": int, "status": str}

    The vocabulary is deliberately the words the pipeline has always used;
    the forges express them as labels plus open/closed state:
      in_progress → add    <label>::in-progress (only while the issue is pending)
      closed      → remove <label>::in-progress, close, comment
      new         → remove <label>::in-progress, reopen, comment (back to the
                    pending pool, which is what makes a failed issue retryable);
                    refused for a paused issue, so a crash handler cannot undo the hold
      paused      → add    <label>::pause, remove <label>::in-progress (manual
                    hold; refused for a closed or opted-out issue)
    """
    if status not in _VALID_STATUSES:
        return _err(f"Invalid status {status!r} – expected one of {_VALID_STATUSES}.")
    try:
        client = forge.issue_client()
        if status == "in_progress":
            updated = client.lock_issue(issue_id)
        elif status == "closed":
            updated = client.close_issue(issue_id, note=note)
        elif status == "paused":
            updated = client.pause_issue(issue_id, note=note)
        else:  # "new"
            updated = client.reopen_issue(issue_id, note=note)
        if not updated:
            return _err(f"{forge.term('forge')} rejected the status update for issue #{issue_id}.")
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
        identity = forge.identity()
        if record.get("gitlab_project") != identity:
            return _err(
                f"layout.json describes {record.get('gitlab_project') or 'an unrecorded project'}, "
                f"not {identity}: only the orchestrator configured for {identity} records its layout "
                "(nesti /arch)."
            )
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
        issue = forge.issue_client().create_issue(title, description)
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
        client = forge.issue_client()
        issue = client.get_issue(issue_id)
        if issue["state"] != "opened":
            return _err(f"Issue #{issue_id} is not open.")
        if client.issue_label in issue["labels"]:
            return _err(f"Issue #{issue_id} was handed to Nesti.")
        comment = f"omp-developer / model: {model}"
        if not client.close_issue(issue_id, note=comment, require_note=True):
            return _err(f"{forge.term('forge')} rejected closing issue #{issue_id}.")
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
        client = forge.issue_client()
        if not client.handoff_issue(
                issue_id,
                "## Third attempt (OMP team, advised) — rejected\n\n" + report.strip()):
            return _err(f"{forge.term('forge')} rejected the hand-off of issue #{issue_id}.")
        return _ok({"issue_id": issue_id, "label": client.issue_label})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_handoff(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_notes(issue_id: int) -> dict:
    """Non-system notes of an issue, oldest first: [{"id","author","author_id","created_at","body","trusted"}]."""
    try:
        return _ok(forge.issue_client().list_notes(issue_id))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_notes(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_domain_answer(issue_id: int, options: list[str]) -> dict:
    """
    The domains a human named in reply to Nesti's latest domain question on
    *issue_id*.  Graph-internal.  result: list[str], [] = no answer.
    """
    try:
        client = forge.issue_client()
        return _ok(issue_domain.answer(client.list_notes(issue_id), client.current_user_id(), options))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_domain_answer(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_ask_domain(issue_id: int, options: list[str]) -> dict:
    """
    Post the domain question on *issue_id* and pause it, both verified.
    Graph-internal.  result: {"issue_id": int, "options": list[str]}.
    """
    try:
        issue_domain.ask(forge.issue_client(), issue_id, options)
        return _ok({"issue_id": issue_id, "options": options})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_ask_domain(%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_issue_reconcile_domain_questions() -> dict:
    """
    Resume answered domain questions and re-ask unmatched replies.  Graph-internal.

    result: {"resumed": [iid], "asked": [iid], "waiting": [iid], "errors": [{"issue_id", "error"}]}
    success=False only when the issues or the token user could not be read.
    """
    try:
        return _ok(issue_domain.reconcile(forge.issue_client()))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_reconcile_domain_questions() failed: %s", exc)
        return _err(exc)


def tool_issue_swap_poll_heartbeat(value: str) -> dict:
    """
    Write this poller's heartbeat to the project and return the previous one.  Graph-internal.

    result: {"previous": str | None}
    """
    try:
        return _ok({"previous": forge.issue_client().swap_poll_heartbeat(value)})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_swap_poll_heartbeat() failed: %s", exc)
        return _err(exc)


# ─────────────────────────────────────────────────────────────────────────────
# GitLab tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_gitlab_clone(target_path: str) -> dict:
    """Clone the configured repository into target_path.  result: {"repo_path": str, "head_sha": str}."""
    try:
        repo = forge.repo_client().clone(target_path)
        return _ok({"repo_path": target_path, "head_sha": repo.head.commit.hexsha})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_gitlab_clone(%s) failed: %s", target_path, exc)
        return _err(exc)


def tool_gitlab_create_branch(repo_path: str, issue_id: int, subject: str) -> dict:
    """Create and checkout a feature branch.  result: {"branch_name": str}."""
    try:
        repo = git.Repo(repo_path)
        branch_name = forge.repo_client().create_branch(repo, issue_id, subject)
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
        pushed = forge.repo_client().commit_and_push(repo, branch_name, message)
        return _ok({"pushed": pushed})
    except forge.OpenMergeRequestError as exc:
        logger.warning("tool_gitlab_commit_and_push(%s) stopped: %s", branch_name, exc)
        return {**_err(exc), "mr_url": exc.url}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_gitlab_commit_and_push(%s) failed: %s", branch_name, exc)
        return _err(exc)


def tool_gitlab_open_mr(branch_name: str, issue_id: int, subject: str, description: str) -> dict:
    """Open a Merge Request (GitLab) or Pull Request (GitHub).  result: {"mr_url": str, "mr": dict}."""
    try:
        mr = forge.repo_client().open_merge_request(
            branch_name=branch_name,
            issue_id=issue_id,
            subject=subject,
            description=description,
        )
        if mr is None:
            return _err(f"{forge.term('forge')} refused to open a {forge.term('merge_request')} "
                        f"for branch {branch_name!r}.")
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
        if _API_TOUCH_RE.match(path):
            return True
    return False


def _under(files: "list[str] | None", folder: str) -> "list[str] | None":
    """*files* inside *folder*, relative to it; ``None`` stays ``None``."""
    if files is None or folder == ".":
        return files
    prefix = folder + "/"
    return [
        p[len(prefix):] for p in (f.replace("\\", "/").removeprefix("./") for f in files)
        if p.startswith(prefix)
    ]


def tool_detect_stack(
    workspace_path: str,
    written_files: "list[str] | None" = None,
    backend_dir: str = ".",
    frontend_dir: str = "",
) -> dict:
    """
    Determine which test layers apply to the code in workspace_path.

    result: {"stack": str, "has_vue": bool, "has_php": bool,
             "run_phpunit": bool, "run_frontend": bool, "vue_files": list[str],
             "source": str, "is_laravel": bool, "has_api_routes": bool,
             "run_openapi": bool}

    ``stack`` is one of:
      "php"       – PHP sources or a Composer project, no .vue files
      "vue"       – .vue files in the SPA and no PHP in the backend folder
      "fullstack" – both layers present
      "unknown"   – neither detected (empty or non-code change)

    ``stack`` describes the repository; the three ``run_*`` gates describe
    *this change* (*written_files*, the paths the last attempt wrote):

    ``run_frontend`` gates Vitest → Playwright: the SPA has Vue and the change
    touched the SPA folder.  A backend change in a repository that merely
    contains .vue files never starts two Node containers.

    ``run_phpunit`` gates the PHP layer: the change touched the backend folder,
    or the frontend layers do not run — so no change (README-only, a change in
    a repository without Vue) ever reaches commit untested.

    ``run_openapi`` is the same kind of gate for the Scramble layer and needs
    all three of: a Laravel app (``artisan``), a registered API surface
    (``routes/api.php``), and a change that actually touched that surface.
    Exporting the document for a pure .vue or migration change would only add
    a slow container to every attempt.

    Omitting *written_files* (MCP callers) yields the conservative answer for
    all three gates: every layer the repository supports runs.

    *backend_dir* is the Laravel folder ("." = root); *frontend_dir* the SPA
    folder ("" = no SPA). A frontend inside the Laravel app is refused.

    Detection is automatic; set NESTI_STACK to php / vue / fullstack to pin the
    *stack* when a repository's layout misleads the scan.  NESTI_STACK never
    pins the Laravel markers: those are two cheap is_file() checks that cannot
    be misled.
    """
    try:
        if frontend_dir in (".", "./"):
            return _err("frontend_dir '.' (a frontend inside the Laravel app) is not supported")
        root = Path(workspace_path)
        backend = root / backend_dir
        is_laravel = (backend / _LARAVEL_MARKER).is_file()
        has_api_routes = (backend / _API_ROUTES_FILE).is_file()
        backend_files = _under(written_files, backend_dir)
        if backend_dir == "." and frontend_dir and backend_files is not None:
            # A root backend's SPA (.frontend/) is the frontend side, never a backend change.
            backend_files = [f for f in backend_files
                             if not f.replace("\\", "/").removeprefix("./").startswith(frontend_dir + "/")]
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


def _merge_package_json(repo_path: str) -> list[str]:
    """
    Merge Nesti's frontend dependencies into the repository's package.json.

    Merging, never replacing: only absent keys are added, so the Laravel
    skeleton's own ``vite``/``laravel-vite-plugin``/``tailwindcss`` entries and
    a foreign repository's dependencies are never touched.
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
        # Keep a foreign repository's indentation so the MR/PR diff stays minimal.
        if match := re.search(r"\n( +)\"", raw):
            indent = len(match.group(1))

    if data.get("type") != "module":
        # Adding "type": "module" to a foreign SPA would reinterpret every
        # existing .js file, so the SPA top-up only warns.
        logger.warning(
            'package.json has no "type": "module" – the ESM vitest/playwright '
            "configs added by the SPA top-up may fail to load."
        )

    changed: list[str] = []
    for section, wanted in (
        ("dependencies", _PACKAGE_DEPENDENCIES),
        ("devDependencies", _PACKAGE_DEV_DEPENDENCIES),
        ("scripts", _PACKAGE_SCRIPTS),
    ):
        bucket = data.setdefault(section, {})
        for key, value in wanted.items():
            if key not in bucket:
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


def _env_value(text: str, key: str) -> str | None:
    """The first uncommented ``KEY=`` value of a dotenv *text*, quotes and inline comment stripped."""
    match = re.search(rf"^[ \t]*{key}[ \t]*=(.*)$", text, re.MULTILINE)
    if not match:
        return None
    return re.sub(r"\s+#.*$", "", match.group(1)).strip().strip("'\"")


def _set_phpunit_env(text: str, key: str, value: str) -> str:
    """*text* with its uncommented ``<env name="key">`` set to *value*; added inside ``<php>`` when absent."""
    comments = [m.span() for m in re.finditer(r"<!--.*?-->", text, re.DOTALL)]

    def live(pattern: str, flags: int = 0) -> "re.Match | None":
        return next((m for m in re.finditer(pattern, text, flags)
                     if not any(start <= m.start() < end for start, end in comments)), None)

    entry = live(rf'(<env\s+name="{key}"\s+value=")[^"]*"')
    if entry:
        return text[:entry.end(1)] + value + text[entry.end() - 1:]
    line = f'<env name="{key}" value="{value}"/>'
    closing = live(r"^([ \t]*)</php>", re.MULTILINE)
    if closing:
        return text[:closing.start()] + f"{closing.group(1)}    {line}\n" + text[closing.start():]
    root = live(r"^([ \t]*)</phpunit>", re.MULTILINE)
    if not root:
        return text
    indent = root.group(1)
    block = f"{indent}    <php>\n{indent}        {line}\n{indent}    </php>\n"
    return text[:root.start()] + block + text[root.start():]


def _align_phpunit_database(app_root: Path) -> str:
    """
    Point phpunit.xml at a separate PostgreSQL database when the app runs on pgsql.

    The driver is ``.env.example``'s DB_CONNECTION (else config/database.php's
    default); mysql/mariadb/sqlite apps are left alone because the PHPUnit
    sandbox forces sqlite for them.  A phpunit.xml already on pgsql is never
    touched.  The database is ``<DB_DATABASE>_test`` (else ``testing``), served
    by docker_runner's postgres sidecar.  Text edits only, formatting kept.
    Returns the database name set, or "" when nothing changed.
    """
    env_file = app_root / ".env.example"
    env = env_file.read_text(encoding="utf-8", errors="replace") if env_file.is_file() else ""
    driver = _env_value(env, "DB_CONNECTION")
    if driver is None:
        config = app_root / "config" / "database.php"
        found = re.search(r"env\(\s*['\"]DB_CONNECTION['\"]\s*,\s*['\"]([^'\"]+)['\"]",
                          config.read_text(encoding="utf-8", errors="replace")) if config.is_file() else None
        driver = found.group(1) if found else ""
    if driver != "pgsql":
        return ""
    target = next((app_root / name for name in ("phpunit.xml", "phpunit.xml.dist")
                   if (app_root / name).is_file()), None)
    if target is None or _pgsql_settings(str(app_root)) is not None:
        return ""
    base = _env_value(env, "DB_DATABASE") or ""
    database = f"{base}_test" if base and _PG_IDENTIFIER.fullmatch(f"{base}_test") else "testing"
    original = target.read_text(encoding="utf-8")
    text = _set_phpunit_env(_set_phpunit_env(original, "DB_CONNECTION", "pgsql"), "DB_DATABASE", database)
    if text == original:
        return ""
    target.write_text(text, encoding="utf-8")
    return database


def tool_laravel_bootstrap(repo_path: str, spa_path: str = "") -> dict:
    """
    Make *repo_path* a Laravel 13 API with Scramble (plus the test-runner wiring
    of its frontend, when it has one).

    result: {"created": bool, "mode": str, "reason": str, "output": str}

    Exactly three outcomes:

    • greenfield (no artisan, no composer.json) → mode "scaffold".  Creates
      *repo_path*, runs ``composer create-project laravel/laravel`` +
      ``install:api`` (Sanctum) + ``composer require dedoc/scramble
      spatie/laravel-permission`` in the PHP sandbox, then writes the API
      templates and the spatie seed data over the skeleton (Nesti created those
      files seconds earlier, so overwriting is safe), a README.md when absent,
      the HasApiTokens/HasRoles traits on User, and appends .gitignore.  No Vue:
      the skeleton's own package.json/vite.config.js stay as they are.

    • existing Laravel app (artisan present) → mode "top-up".  Never overwrites
      a file the repository already has: installs Scramble only when absent and
      writes the Scramble wiring test when absent.  routes/** is never touched.
      A pgsql app's phpunit.xml is pointed at a separate test database.

    • non-Laravel PHP project (composer.json without artisan) → success=False.
      Scaffolding a Laravel skeleton over a foreign application would destroy
      it, so this is reported as the configuration error it is.

    *spa_path* (*repo_path* is the Laravel API folder) also tops up the SPA
    folder with the absent vitest.config.js, vitest.setup.js (jsdom polyfills
    for matchMedia/ResizeObserver) and playwright.config.js plus missing
    package.json keys; an unmodified vitest.config.js an earlier Nesti wrote
    is upgraded in place so it loads the setup file.
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
            root.mkdir(parents=True, exist_ok=True)
            passed, output = DockerRunner().run_bootstrap(repo_path)
            if not passed:
                return _err(f"Laravel skeleton bootstrap failed:\n{output}")
            if not (root / _LARAVEL_MARKER).is_file():
                return _err(
                    "bootstrap reported success but no artisan file appeared in "
                    f"the repository:\n{output}"
                )
            applied = _apply_templates(repo_path, _SCAFFOLD_TEMPLATES, overwrite=True)
            applied += _apply_templates(repo_path, starter_kit.DATA_FILES, overwrite=True,
                                        source_dir=starter_kit.BACKEND_TEMPLATES / "spatie")
            applied += _apply_templates(repo_path, ("README.md",), overwrite=False)
            starter_kit.add_model_traits(root / "app/Models/User.php", starter_kit.MODEL_TRAITS["spatie"])
            ignored = _append_gitignore(repo_path)
            return _ok({
                "created": True,
                "mode": "scaffold",
                "reason": (
                    "Laravel API skeleton with Sanctum, Scramble and spatie/laravel-permission "
                    f"scaffolded; {len(applied)} template(s), {len(ignored)} .gitignore line(s)"
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

        package: list[str] = []
        applied = _apply_templates(
            repo_path, ("tests/Feature/OpenApiDocumentationTest.php",), overwrite=False
        )
        if spa_path:
            vitest_config = Path(spa_path, "vitest.config.js")
            if (vitest_config.is_file() and hashlib.sha256(vitest_config.read_bytes()).hexdigest()
                    in _SUPERSEDED_SPA_VITEST_CONFIGS):
                shutil.copyfile(_SPA_TEMPLATES_DIR / "vitest.config.js", vitest_config)
                applied.append(f"{Path(spa_path).name}/vitest.config.js")
            applied += [
                f"{Path(spa_path).name}/{rel}" for rel in _apply_templates(
                    spa_path, _SPA_TOPUP_TEMPLATES, overwrite=False, source_dir=_SPA_TEMPLATES_DIR,
                )
            ]
            package = _merge_package_json(spa_path)
        ignored = _append_gitignore(repo_path)
        database = _align_phpunit_database(root)
        if applied:
            notes.append("added " + ", ".join(applied))
        if package:
            notes.append(f"added {len(package)} package.json key(s)")
        if ignored:
            notes.append("extended .gitignore")
        if database:
            notes.append(f"phpunit.xml switched to the PostgreSQL test database {database}")

        return _ok({
            "created": False,
            "mode": "top-up",
            "reason": "; ".join(notes) if notes else "already fully wired",
            "output": output,
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_laravel_bootstrap(%s) failed: %s", repo_path, exc)
        return _err(exc)


def _composer_requires(app: Path, package: str) -> bool:
    """True when *app*'s composer.json requires *package* (require or require-dev)."""
    try:
        composer = json.loads((app / "composer.json").read_text(encoding="utf-8"))
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Unreadable composer.json in %s: %s", app, exc)
        return False
    return any(package in (composer.get(key) or {}) for key in ("require", "require-dev"))


_MAX_APP_FACTS_CHARS = 12000
# Laravel's own tables: noise in a schema summary meant for feature work.
_FRAMEWORK_TABLES = frozenset({
    "migrations", "cache", "cache_locks", "jobs", "job_batches", "failed_jobs", "sessions",
    "password_reset_tokens", "personal_access_tokens",
})


def _boost_payload(segment: str) -> dict:
    """The payload of one ``boost:execute-tool`` result printed in *segment*; ValueError when unusable."""
    start, end = segment.find("{"), segment.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON result")
    result = json.loads(segment[start:end + 1])
    if not isinstance(result, dict):
        raise ValueError("the result is not a JSON object")
    content = result.get("content") or []
    first = content[0] if content and isinstance(content[0], dict) else None
    if result.get("isError"):
        raise ValueError((first or {}).get("text") or "Boost reported an error")
    if first is None:
        raise ValueError("the result has no content")
    if not isinstance(first.get("text"), str):
        return first
    payload = json.loads(first["text"])
    if not isinstance(payload, dict):
        raise ValueError("the result text is not a JSON object")
    return payload


def _render_app_facts(info: dict, schema: dict) -> tuple[str, int]:
    """Versions, packages and the application tables, within _MAX_APP_FACTS_CHARS; returns (text, tables rendered)."""
    engine = info.get("database_engine") or schema.get("engine") or "unknown"
    lines = [f"PHP {info.get('php_version', '?')} · Laravel {info.get('laravel_version', '?')} · database {engine}"]
    packages = ", ".join(
        f"{p.get('package_name') or p.get('roster_name')} {p.get('version', '')}".strip()
        for p in info.get("packages") or [] if isinstance(p, dict)
    )
    if packages:
        lines.append(f"Packages: {packages}")
    lines.append("Tables (column type):")
    text = "\n".join(lines)
    raw_tables = schema.get("tables")
    tables = {
        name: columns for name, columns in (raw_tables.items() if isinstance(raw_tables, dict) else ())
        if name not in _FRAMEWORK_TABLES and isinstance(columns, dict) and "error" not in columns
    }
    names = sorted(tables)
    for index, name in enumerate(names):
        line = f"- {name}: " + ", ".join(f"{column} {kind}" for column, kind in tables[name].items())
        omitted = f"\n- … {len(names) - index} more table(s) omitted"
        rest = omitted if index < len(names) - 1 else ""
        if len(text) + 1 + len(line) + len(rest) > _MAX_APP_FACTS_CHARS:
            return text + omitted, index
        text += "\n" + line
    return text, len(names)


def tool_app_facts(backend_path: str) -> dict:
    """
    Laravel Boost ApplicationInfo + DatabaseSchema summary of *backend_path* at
    its current checkout, for the prompts.
    result: {"facts": str, "tables": int, "reason": str}.

    Skips (success, empty facts) without artisan or without laravel/boost in
    composer.json; never installs Boost. Packages are limited to the ones
    composer.json requires directly (Boost lists every installed package).
    """
    try:
        app = Path(backend_path)
        if not (app / _LARAVEL_MARKER).is_file():
            return _ok({"facts": "", "tables": 0, "reason": "no Laravel app"})
        if not _composer_requires(app, "laravel/boost"):
            return _ok({"facts": "", "tables": 0, "reason": "laravel/boost is not a dependency"})
        passed, output = DockerRunner().run_app_facts(backend_path)
        if not passed:
            return _err(f"app facts export failed:\n{condense(output, 2000)}")
        parts = output.split(APP_FACTS_MARK)
        if len(parts) < 4:
            return _err("app facts output carries no Boost results")
        try:
            info = _boost_payload(parts[1])
            composer = json.loads((app / "composer.json").read_text(encoding="utf-8"))
            direct = {name for key in ("require", "require-dev") for name in composer.get(key) or {}}
            info["packages"] = [p for p in info.get("packages") or []
                                if isinstance(p, dict) and p.get("package_name") in direct]
            text, count = _render_app_facts(info, _boost_payload(parts[2]))
        except ValueError as exc:
            return _err(f"Boost result unreadable: {exc}")
        return _ok({"facts": text, "tables": count, "reason": f"{count} table(s)"})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_app_facts(%s) failed: %s", backend_path, exc)
        return _err(exc)


def tool_starter_kit(repo_path: str, backend_dir: str, spa_dir: str) -> dict:
    """
    Add Nesti's starter kit to the Laravel API *backend_dir* of *repo_path*:
    a sign-in + administration API (Sanctum login/logout, users, and roles /
    permissions when the app has a role schema) with seeders and tests, plus a
    Sakai PrimeVue SPA in the absent *spa_dir*.  Graph-internal.

    Validates everything before writing anything: the SPA folder must be
    absent, no starter contract file may exist, User must be editable and, when
    seed data is written, DatabaseSeeder must accept the calls.  Sanctum and
    the permission migrations are installed in the PHP sandbox only when missing.

    result: {"variant": "spatie"|"custom"|"none", "files": [repo-relative paths], "reason": str}
    """
    try:
        repo = Path(repo_path)
        app = repo / backend_dir
        spa = repo / spa_dir
        if spa.exists():
            return _err(f"{spa_dir}/ already exists; the starter kit only fills an absent SPA folder")

        variant = starter_kit.role_schema(app)
        overlays = starter_kit.backend_overlays(variant)
        files = starter_kit.overlay_files(starter_kit.BACKEND_TEMPLATES, overlays)
        stub = starter_kit.routes_stub(starter_kit.BACKEND_TEMPLATES, overlays)
        spa_files = starter_kit.overlay_files(
            starter_kit.SPA_TEMPLATES, ["base"] if variant == "none" else ["base", "roles"])
        if stub is None:
            return _err(f"starter kit template missing: routes.stub for {overlays}")
        data = {rel: src for rel, src in files.items() if rel in starter_kit.DATA_FILES}
        contract = {rel: src for rel, src in files.items() if rel not in starter_kit.DATA_FILES}
        routes = app / _API_ROUTES_FILE
        had_routes = routes.is_file()
        conflicts = [rel for rel in contract if (app / rel).exists()]
        if had_routes and "// Nesti starter kit" in routes.read_text(encoding="utf-8", errors="replace"):
            conflicts.append(_API_ROUTES_FILE)
        if conflicts:
            return _err("starter kit files already exist: " + ", ".join(conflicts))

        notes: list[str] = []
        present = [rel for rel in data if (app / rel).exists()]
        write_data = not present
        if present:
            notes.append(f"kept existing seed data ({', '.join(present)}); demo accounts may differ")
        user = app / "app/Models/User.php"
        seeder = app / "database/seeders/DatabaseSeeder.php"
        if not user.is_file():
            return _err("app/Models/User.php is missing")
        try:
            starter_kit.model_with_traits(user.read_text(encoding="utf-8"), starter_kit.MODEL_TRAITS[variant])
            if write_data and seeder.is_file():
                starter_kit.seeder_with_calls(seeder.read_text(encoding="utf-8"),
                                              starter_kit.seeder_classes(variant))
        except ValueError as exc:
            return _err(exc)

        migrations = app / "database" / "migrations"
        install_api = not _composer_requires(app, "laravel/sanctum") or not had_routes
        publish_sanctum = not install_api and not any(
            migrations.glob("*_create_personal_access_tokens_table.php"))
        publish_permission = variant == "spatie" and not any(
            migrations.glob("*_create_permission_tables.php"))
        if install_api or publish_sanctum or publish_permission:
            passed, output = DockerRunner().run_starter_install(
                str(app), install_api=install_api, publish_sanctum=publish_sanctum,
                publish_permission=publish_permission,
            )
            if not passed:
                return _err(f"starter kit install failed:\n{condense(output, 4000)}")
            notes.append("installed " + ", ".join(name for name, flag in (
                ("Sanctum (install:api)", install_api), ("the Sanctum migration", publish_sanctum),
                ("the spatie/laravel-permission migration", publish_permission)) if flag))
        if not routes.is_file() or not _composer_requires(app, "laravel/sanctum"):
            return _err("starter kit install left no routes/api.php or no laravel/sanctum requirement")

        if not had_routes:
            # Drops install:api's /user closure stub: the starter's routes are the whole surface.
            shutil.copyfile(_TEMPLATES_DIR / _API_ROUTES_FILE, routes)
        starter_kit.append_routes(routes, stub)
        written = [_API_ROUTES_FILE]
        for rel, source in [*contract.items(), *(data.items() if write_data else ())]:
            (app / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, app / rel)
            written.append(rel)
        if write_data and starter_kit.register_seeders(seeder, starter_kit.seeder_classes(variant)):
            written.append("database/seeders/DatabaseSeeder.php")
        if starter_kit.add_model_traits(user, starter_kit.MODEL_TRAITS[variant]):
            written.append("app/Models/User.php")
        changed = [(Path(backend_dir) / rel).as_posix() for rel in written]
        for rel, source in spa_files.items():
            (spa / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, spa / rel)
            changed.append(f"{spa_dir}/{rel}")
        return _ok({
            "variant": variant,
            "files": changed,
            "reason": "; ".join([
                f"starter kit ({variant} roles): {len(written)} backend file(s), "
                f"Sakai SPA in {spa_dir}/ ({len(spa_files)} file(s))",
                *notes,
            ]),
        })
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_starter_kit(%s) failed: %s", repo_path, exc)
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
    result: {"passed": bool, "output": str}.

    The sandbox builds the SPA and Playwright's webServer config serves it;
    no server needs to be running beforehand.  Same semantics as
    tool_vitest_run_tests.
    """
    try:
        passed, output = FrontendRunner().run_playwright(workspace_path)
        return _ok({"passed": passed, "output": output})
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
_RUN_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_RUN_ID_ERROR = "run_id must be 1-64 characters from A-Z a-z 0-9 _ -"


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
    Previously merged issues of this project similar to *text* (Redis solution cache).
    result: [{"issue_id", "subject", "plan", "mr_url", "stack", "similarity"},
             ...] most similar first, above NESTI_SOLUTION_MIN_SCORE.
    """
    try:
        project = forge.identity()
        memory = get_semantic_memory()
        if not memory.available:
            return _ok([])
        return _ok(memory.find_similar_solutions(project, text, limit=limit))
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
        project = forge.identity()
        memory = get_semantic_memory()
        if not memory.available:
            return _ok(dict(_MEMORY_UNAVAILABLE))
        stored = memory.remember_solution(
            project, issue_id, subject, description, plan, stack, mr_url
        )
        return _ok({"stored": True} if stored else {"stored": False, "reason": "write failed"})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_remember_solution(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_remember_failure(
    issue_id: int, run_id: str, attempt: int, layer: str, output: str
) -> dict:
    """
    Store one failed attempt of an issue's run *run_id* in episodic memory.
    result: {"stored": bool} (plus "reason" when not stored).
    """
    if not _RUN_ID.fullmatch(run_id or ""):
        return _err(_RUN_ID_ERROR)
    try:
        project = forge.identity()
        memory = get_semantic_memory()
        if not memory.available:
            return _ok(dict(_MEMORY_UNAVAILABLE))
        stored = memory.remember_failure(project, issue_id, run_id, attempt, layer, output)
        return _ok({"stored": True} if stored else {"stored": False, "reason": "write failed"})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_remember_failure(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_recall_failures(
    issue_id: int, run_id: str, text: str, attempt: int, limit: int = 2
) -> dict:
    """
    Older failed attempts of an issue's run *run_id* similar to *text*.  ``attempt`` is the
    attempt about to run; the one that just failed (attempt - 1) is excluded
    because its output is already in the conversation history.
    result: [{"issue_id", "attempt", "layer", "summary", "similarity"}, ...].
    """
    if not _RUN_ID.fullmatch(run_id or ""):
        return _err(_RUN_ID_ERROR)
    try:
        project = forge.identity()
        memory = get_semantic_memory()
        if not memory.available:
            return _ok([])
        return _ok(
            memory.recall_failures(project, issue_id, run_id, text, attempt=attempt, limit=limit)
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_memory_recall_failures(issue #%s) failed: %s", issue_id, exc)
        return _err(exc)


def tool_memory_forget_episodes(issue_id: int, run_id: str) -> dict:
    """
    Drop every episodic-memory row of an issue's run *run_id*.  result: {"deleted": int}.
    """
    if not _RUN_ID.fullmatch(run_id or ""):
        return _err(_RUN_ID_ERROR)
    try:
        project = forge.identity()
        return _ok({"deleted": get_semantic_memory().forget_episodes(project, issue_id, run_id)})
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
