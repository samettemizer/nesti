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
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import git

from docker_runner import DockerRunner
from frontend_runner import FrontendRunner
from gitlab_client import GitLabClient
from gitlab_issues_client import GitLabIssuesClient
from skill_catalog import catalog_status, select_skills
from skill_loader import load_skills

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

# Intake lifecycle vocabulary. GitLab has no "in progress" issue state, so
# GitLabIssuesClient expresses these three words as labels plus open/closed —
# the strings stay stable so every node and MCP client is unaffected.
_VALID_STATUSES = ("in_progress", "closed", "new")


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

    Pending means: open, carrying the opt-in GITLAB_ISSUE_LABEL, and not yet
    carrying the ``<label>::in-progress`` lock.
    """
    try:
        return _ok(GitLabIssuesClient().list_pending(limit=_ISSUE_LIST_LIMIT))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_list_pending() failed: %s", exc)
        return _err(exc)


def tool_issue_set_status(issue_id: int, status: str, note: str = "") -> dict:
    """
    Move an issue through the intake lifecycle.
    status: "in_progress" | "closed" | "new"
    result: {"issue_id": int, "status": str}

    The vocabulary is deliberately the same three words the pipeline has always
    used; GitLab expresses them as labels plus open/closed state:
      in_progress → add    <label>::in-progress
      closed      → remove <label>::in-progress, close, comment
      new         → remove <label>::in-progress, reopen, comment (back to the
                    pending pool, which is what makes a failed issue retryable)
    """
    if status not in _VALID_STATUSES:
        return _err(f"Invalid status {status!r} – expected one of {_VALID_STATUSES}.")
    try:
        client = GitLabIssuesClient()
        if status == "in_progress":
            updated = client.lock_issue(issue_id)
        elif status == "closed":
            updated = client.close_issue(issue_id, note=note)
        else:  # "new"
            updated = client.reopen_issue(issue_id, note=note)
        if not updated:
            return _err(f"GitLab rejected the status update for issue #{issue_id}.")
        return _ok({"issue_id": issue_id, "status": status})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_issue_set_status(%s, %s) failed: %s", issue_id, status, exc)
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


def tool_detect_stack(workspace_path: str, written_files: "list[str] | None" = None) -> dict:
    """
    Determine which test layers apply to the code in workspace_path.

    result: {"stack": str, "has_vue": bool, "has_php": bool,
             "run_phpunit": bool, "vue_files": list[str], "source": str,
             "is_laravel": bool, "has_api_routes": bool, "run_openapi": bool}

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

    ``run_openapi`` is the same kind of gate for the Scramble layer and needs
    all three of: a Laravel app (``artisan``), a registered API surface
    (``routes/api.php``), and a change that actually touched that surface
    (*written_files*).  Exporting the document for a pure .vue or migration
    change would only add a slow container to every attempt.

    Detection is automatic; set NESTI_STACK to php / vue / fullstack to pin the
    *stack* when a repository's layout misleads the scan.  NESTI_STACK never
    pins the Laravel markers: those are two cheap is_file() checks that cannot
    be misled.
    """
    try:
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

        return _ok({
            "stack": stack,
            "has_vue": has_vue,
            "has_php": has_php,
            "run_phpunit": stack != "vue",
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
        vite_config = root / "vite.config.js"
        if vite_config.is_file():
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

        applied = _apply_templates(repo_path, _TOPUP_TEMPLATES, overwrite=False)
        if applied:
            notes.append("added " + ", ".join(applied))
        package = _merge_package_json(repo_path, overwrite=False)
        if package:
            notes.append(f"added {len(package)} package.json key(s)")
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
    text: str, max_component_docs: int = 3, max_topic_docs: int = 2
) -> dict:
    """
    Select vendored Laravel / PrimeVue docs matching *text*.
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
            )
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_skill_catalog_select failed: %s", exc)
        return _err(exc)


def tool_skill_catalog_status() -> dict:
    """
    Report whether the vendored skill corpus is present and how large it is.
    result: {"available": bool, "components": int, "topics": int,
             "primevue_version": str, "laravel_branch": str}.
    """
    try:
        return _ok(catalog_status())
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("tool_skill_catalog_status failed: %s", exc)
        return _err(exc)
