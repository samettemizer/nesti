"""
graph/nodes.py – LangGraph node functions.

Each node is a function ``(state: IssueState) -> dict`` returning a *partial
state update* — only the fields it changes.  LangGraph merges the update into
the running state.

Conversation semantics
──────────────────────────────────────────
The stored transcript is diagnostic, not provider input. Each provider call
gets one compiled current request: issue, plan, current repository, previous
change set and latest failure. Raw responses are retained and applied intact.
Planning starts a fresh transcript, even after an interrupted previous run.

Error strategy per node
───────────────────────
• node_setup      – a refused claim returns ``failure_reason`` and routes
                    straight to cleanup (nothing cloned, no LLM call); raises
                    on unrecoverable git errors (after removing its own
                    tempdir); TaskEngine's try/except reopens the issue.
• node_plan       – catches RuntimeError ("all planners failed"), leaves
                    ``plan`` empty; route_after_plan then routes to failure.
• node_code       – catches RuntimeError ("all coders exhausted") and jumps
                    ``attempt`` to ``max_attempts`` so route_after_code routes
                    straight to failure. Unapplied code never starts a test layer.
• node_commit     – tool failures reopen the issue + notify instead of raising,
                    so the commit → cleanup edge still runs.

Test layering
───────────────────────────
node_bootstrap runs right after node_setup and guarantees the clone is a
Laravel application; node_detect_stack then runs between node_code and the
test layers and decides which of them apply to the files the attempt wrote:

    PHP touched            → phpunit [→ openapi]
    frontend touched       → vitest → playwright     (needs Vue in the repo)
    both touched           → phpunit [→ openapi] → vitest → playwright
    neither applies        → phpunit                 (never no-tests)
    "vue" stack            → vitest → playwright     (phpunit skipped entirely)

The optional openapi layer runs when the attempt touched routes/api.php or an
app/Http/{Controllers,Resources,Requests} file in a Laravel repo that has an
API surface.

Every layer failure funnels into one escalate-and-retry node
(node_on_layer_failure), so the retry budget (max_attempts) is shared across
all four layers rather than per layer.

Task scope
──────────
node_plan decides whether the issue is backend, frontend or fullstack work
(issue text first, then the planner's ``SCOPE:`` line) and logs it as the run's
one ``SCOPE:`` line.  The scope narrows the prompts, the reference docs and the
retrieved chunks; it never gates a test layer.

Fixture dependencies
────────────────────
When the E2E sandbox verifies that a declared fixture's seeder genuinely does
not exist, node_playwright_test logs BLOCKED and node_pause_dependency pauses
the issue durably in GitLab and opens one backend dependency issue — with no
planner, coder or escalation call, independently of the scope.  The issue is
resumed by TaskEngine's reconciliation only after that child's MR is merged.
"""

import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import git

from graph.state import IssueState
from graph.tools import (
    tool_skill_fetch, tool_gitlab_clone, tool_gitlab_create_branch,
    tool_docker_run_tests, tool_gitlab_commit_and_push, tool_gitlab_open_mr,
    tool_issue_set_status, tool_detect_stack, tool_vitest_run_tests,
    tool_playwright_run_tests, tool_laravel_bootstrap, tool_openapi_export,
    tool_skill_catalog_select, tool_skill_catalog_status, tool_quota_check,
    tool_memory_search_docs, tool_memory_find_similar, tool_memory_remember_solution,
    tool_memory_remember_failure, tool_memory_recall_failures,
    tool_memory_forget_episodes, tool_issue_pause_for_fixture,
    _routing_metadata,
)
from issue_scope import ScopeDecision, classify_issue, declared_scope, widen
from llm_client import LLMClient
from project_architecture import (
    collect_inventory, collect_architecture, load_project_rules, format_project_context,
)
from project_context import configured_project_root, inspect_project
from conversation_store import ConversationStore
from prompt_builder import (
    build_plan_prompt, build_code_prompt, drop_injected_chunks, format_catalog_for_prompt,
)
from layer_output import condense
from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)

_llm = LLMClient()
_store = ConversationStore()

# Output budgets. Both are applied by layer_output.condense, which strips
# installer chatter and keeps the TAIL — the assertion failure and the
# `Tests: N failed` summary are always last, so slicing from the front used to
# leave a note containing nothing but npm advisories.
#
# The reopen note is the only thing a human sees on a failed issue, and 1000
# chars of *condensed* output is still thin for a PHPUnit stack trace; GitLab
# comments have no practical size limit, so the budget is 3000.
_MAX_NOTE_CHARS = 3000
_MAX_MR_TEST_OUTPUT_CHARS = 2000

# Documented /api paths listed in the Merge Request body.  A large API surface
# would otherwise bury the test output under hundreds of bullet lines.
_MAX_MR_OPENAPI_PATHS = 40

# Fallback when the initial state somehow lacks max_attempts (unit tests).
_ENV_MAX_ATTEMPTS = int(os.environ.get("MAX_CODE_RETRIES", "2")) + 1

# retrieval sizes. Qdrant is asked for more chunks than a prompt keeps
# so that dropping the passages the keyword catalog already injected still
# leaves a full set of complementary ones.
_DOC_CHUNK_SEARCH_LIMIT = 8
_DOC_CHUNK_KEEP = 6
_DOC_RERANK_SEARCH_LIMIT = 20
# The failure text used to query episodic memory is condensed exactly like the
# stored episodes (semantic_cache._EPISODE_OUTPUT_LIMIT); embedding the raw
# output would embed its first 512 tokens — installer chatter, not the error.
_EPISODE_QUERY_CHARS = 1200

# Corrective feedback for an unapplied coding response, before any test layer.
_NO_FILE_BLOCKS_OUTPUT = (
    "No file changes could be applied or tested. Output each created or "
    "modified file in full using '### FILE: <path>' blocks and each requested "
    "physical removal using '### DELETE: <path>' directives."
)

# Reference-doc lanes per scope: (PrimeVue component docs, Laravel topic docs).
# A backend issue spends no catalog budget on PrimeVue pages and a frontend
# issue none on Laravel topics.  The code prompt keeps one topic doc instead of
# two to leave room for the plan itself.
_PLAN_CATALOG_LIMITS = {"backend": (0, 2), "frontend": (3, 0), "fullstack": (3, 2)}
_CODE_CATALOG_LIMITS = {"backend": (0, 1), "frontend": (3, 0), "fullstack": (3, 1)}

# Qdrant payload filter per scope.  A fullstack scope searches both stacks.
_SCOPE_DOC_STACK = {"backend": "php", "frontend": "vue"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cleared_layer_outputs() -> dict:
    """
    Empty results for every test layer, merged into node_code's return.

    The layers follow the files each attempt writes, so one attempt can run
    Vitest and the next only PHPUnit.  A red output left over from an earlier
    attempt would then be fed back as this attempt's failure
    (``_last_failure_output`` picks the newest red layer with any output),
    widen the scope on the wrong side, and reach the MR body as a layer that
    never ran on the merged code.  Clearing them in node_code's *return* keeps
    its own episodic-recall query on the failure that led to it.  The fixture
    fields are cleared for the same reason: no attempt inherits an earlier
    attempt's block.
    """
    return {
        "test_output": "",
        "openapi_output": "",
        "openapi_paths": [],
        "vitest_output": "",
        "playwright_output": "",
        "fixture_request": None,
        "dependency_status": "",
    }


def _select_catalog_skills(
    text: str, max_component_docs: int, max_topic_docs: int, max_practice_docs: int = 0
) -> list:
    """
    Pick vendored PrimeVue / Laravel / practice reference docs matching *text*.

    Selection is deterministic and offline (see ``skill_catalog``).  A missing
    or broken corpus must never block a run, so any failure degrades to an
    empty list and the prompt is built without reference documentation.

    Practice docs are cross-cutting engineering guidance, not API reference, so
    they default to zero: only the plan phase asks for one.  The plan text is
    part of the code prompt, which is how that guidance reaches the coder
    without spending the tighter code budget on it a second time.
    """
    result = tool_skill_catalog_select(
        text, max_component_docs, max_topic_docs, max_practice_docs
    )
    if not result["success"]:
        logger.warning("Skill catalog selection failed: %s", result["error"])
        return []
    selected = result["result"]
    if selected:
        logger.info(
            "Reference docs selected: %s",
            ", ".join(skill.title for skill in selected),
        )
    return selected


def _retrieve_chunks(
    text: str, catalog_skills: list, stack: str = "", limit: int = _DOC_CHUNK_SEARCH_LIMIT,
    *, phase: str = "plan", scope: str = "fullstack",
) -> list[dict]:
    """
    Semantic doc chunks from Qdrant, minus passages the catalog already injected.

    The test is on content, not URL: a catalog document is capped at 7 000
    chars, and its passages past the cap must stay retrievable.  Memory is
    optional: an unavailable store yields ``[]`` silently (the tool reports
    success with an empty list); only a genuine error is logged.
    Opt-in reranking expands candidates only after retaining the exact dense
    baseline, which is returned unchanged whenever expansion or scoring fails.
    """
    result = tool_memory_search_docs(text, stack=stack, limit=limit)
    if not result["success"]:
        logger.warning("Document memory search failed: %s", result["error"])
        return []
    injected = format_catalog_for_prompt(catalog_skills, phase, scope)
    chunks = drop_injected_chunks(result["result"], injected)[:_DOC_CHUNK_KEEP]
    if chunks:
        logger.info(
            "Retrieved doc chunks%s: %s",
            f" (stack={stack})" if stack else "",
            ", ".join(f"{c['doc_title']} — {c['heading']}" for c in chunks),
        )
    if os.environ.get("NESTI_RERANKER_ENABLED", "").strip().lower() not in {
        "true", "1", "yes", "on",
    }:
        return chunks

    started = time.monotonic()
    candidate_count = 0
    reason = "baseline_empty"
    if chunks:
        try:
            reason = "expansion_error"
            expanded = tool_memory_search_docs(
                text, stack=stack, limit=_DOC_RERANK_SEARCH_LIMIT
            )
            if not expanded["success"]:
                raise ValueError("Expansion failed")
            reason = "expansion_malformed"
            candidates = expanded["result"]
            if not isinstance(candidates, list) or not all(
                isinstance(c, dict) and isinstance(c.get("text"), str)
                for c in candidates
            ):
                raise ValueError("Malformed expansion")
            candidates = drop_injected_chunks(candidates, injected)
            candidate_count = len(candidates)
            reason = "expansion_empty"
            if candidates:
                reason = "adapter_unavailable"
                from reranker import rerank_candidates

                slots = [c["stack"] for c in chunks]
                selected = rerank_candidates(text, candidates, slots)
                return chunks if selected is None else selected
        except Exception as exc:
            # Memory enrichment must never fail the issue or expose its text.
            reason = f"{reason}:{type(exc).__name__}"
    logger.info(
        "RERANK candidates=%d scored=0 selected=%d model=unknown revision=unknown "
        "elapsed_ms=%.1f fallback=%s",
        candidate_count, len(chunks), (time.monotonic() - started) * 1000, reason,
    )
    return chunks


def _committed_paths(root: str, relatives: list[str]) -> set[str]:
    """
    The subset of *relatives* (normalised, repo-relative) committed in the
    clone's HEAD.  Empty outside a git repository or before its first commit.
    """
    if not relatives:
        return set()
    try:
        with git.Repo(root, search_parent_directories=True) as repo:
            if not repo.head.is_valid():
                return set()
            prefix = Path(root).relative_to(repo.working_tree_dir).as_posix()
            prefix = "" if prefix == "." else prefix + "/"
            listed = repo.git.ls_tree("-r", "-z", "--name-only", "HEAD", "--",
                                      *(prefix + path for path in relatives))
    except (git.InvalidGitRepositoryError, git.NoSuchPathError, git.GitCommandError) as exc:
        logger.debug("No committed baseline for the stale files: %s", exc)
        return set()
    return {path.removeprefix(prefix) for path in listed.split("\0") if path}


def _prune_stale_files(
    previous: list[str], current: list[str], repo_path: str
) -> list[str]:
    """
    Revert file changes the previous attempt made that this attempt did not re-emit.

    The workspace persists across retries, so without this an attempt that
    renames a file leaves both versions behind.  For Laravel that is fatal
    rather than untidy: two ``*_create_tasks_table.php`` migrations both run
    and the second dies with "table already exists" — on every remaining
    attempt, for a reason the model cannot see in its own output.

    Retries are asked for the complete set of affected files (see
    ``ConversationStore.append_test_failure``), so anything the new response
    omits is no longer part of the change.  "Reverted" depends on the file:

    * committed in the clone (README.md, routes/api.php, …) → restored to its
      committed content.  Deleting it would put a deletion no issue asked for
      into the Merge Request — an unrequested README edit dropped on a retry
      would otherwise come back as a deleted README;
    * anything else → deleted, and directories left empty go with it, so a
      renamed package does not leave a stray tree in the Merge Request.
    """
    root = os.path.abspath(repo_path)

    def _normalised(relative: str) -> str:
        return os.path.relpath(os.path.abspath(os.path.join(root, relative)), root)

    # Compared after normalisation: "./README.md" and "README.md" are one file,
    # and reverting the spelling the current attempt did not use would undo
    # the file it just wrote.
    current_paths = {_normalised(relative) for relative in current}
    stale: dict[str, str] = {}
    for relative in previous:
        normalised = _normalised(relative)
        # Never step outside the clone, whatever the model emitted as a path.
        outside = normalised == os.pardir or normalised.startswith(os.pardir + os.sep)
        if normalised not in current_paths and not outside:
            stale[relative] = normalised
    committed = _committed_paths(root, sorted(set(stale.values())))
    reverted: list[str] = []

    for relative, normalised in stale.items():
        target = os.path.join(root, normalised)
        if normalised in committed:
            try:
                with git.Repo(root, search_parent_directories=True) as repo:
                    relative = Path(target).relative_to(repo.working_tree_dir).as_posix()
                    repo.git.checkout("HEAD", "--", relative)
                reverted.append(relative)
            except git.GitCommandError as exc:
                logger.warning("Could not restore stale file %s: %s", relative, exc)
            continue
        if not os.path.isfile(target):
            continue
        try:
            os.remove(target)
            reverted.append(relative)
        except OSError as exc:
            logger.warning("Could not remove stale file %s: %s", relative, exc)
            continue
        # Walk up while directories are empty, stopping at the repo root.
        parent = os.path.dirname(target)
        while parent != root and os.path.isdir(parent) and not os.listdir(parent):
            try:
                os.rmdir(parent)
            except OSError:
                break
            parent = os.path.dirname(parent)

    return reverted



# Every scope quotes the default seeder so backend removals can preserve
# unrelated registrations. Frontend/fullstack also quote the served entry
# chain, fixture manifest and configs. Only COMPLETE bodies are quoted; an
# oversized or unreadable body is named as omitted, never safe to rewrite.
_INVENTORY_QUOTED_FILES = (
    ("resources/js/app.js", "js"),
    ("resources/js/app.ts", "ts"),
    ("resources/views/app.blade.php", "blade"),
    ("resources/js/App.vue", "vue"),
    ("database/seeders/DatabaseSeeder.php", "php"),
    ("e2e/nesti-fixtures.json", "json"),
    ("vite.config.js", "js"),
    ("vite.config.ts", "ts"),
    ("playwright.config.js", "js"),
    ("playwright.config.ts", "ts"),
    ("vitest.config.js", "js"),
    ("vitest.config.ts", "ts"),
    ("package.json", "json"),
)
_MAX_QUOTED_FILE_CHARS = 24000
_MAX_QUOTED_TOTAL_CHARS = 48000




def _quoted_entry_files(
    root: Path, scope: str = "fullstack", referenced_files: list[tuple[str, str]] | None = None,
    inventory: dict | None = None,
) -> list[str]:
    """Quote complete task targets and entry bodies within one budget, never fragments."""
    inventory = inventory if inventory is not None else collect_inventory(str(root))
    fixed_files = [
        (relative, language) for relative, language in _INVENTORY_QUOTED_FILES
        if scope != "backend" or relative == "database/seeders/DatabaseSeeder.php"
    ]
    files = dict((referenced_files or []) + fixed_files)
    entries: list[tuple[str | None, str]] = []
    for relative, language in files.items():
        path = root / relative
        if relative not in inventory["files"]:
            continue
        if path.is_symlink():
            entries.append((None, f"\n{relative}: exists, body omitted (symbolic link)."))
            continue
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            entries.append((None,
                f"\n{relative}: exists, body omitted (unreadable: {type(exc).__name__}). "
                "Do not recreate it."))
            continue
        if len(body) > _MAX_QUOTED_FILE_CHARS:
            telegram_notify(
                f"⚠️ Nodes :: _MAX_QUOTED_FILE_CHARS limit:{_MAX_QUOTED_FILE_CHARS} exceeded: <b>{len(body)}</b>"
                f"\nF:{relative}"
            )
            entries.append((None,
                f"\n{relative}: exists, body omitted ({len(body)} characters, over the "
                f"{_MAX_QUOTED_FILE_CHARS}-character quote limit). Do not recreate it from memory."))
            continue
        quote = f"\nCurrent {relative} (complete):\n```{language}\n{body}\n```"
        omitted = (
            f"\n{relative}: exists, body omitted (the {_MAX_QUOTED_TOTAL_CHARS}-character "
            "quote budget is spent). Do not recreate it from memory."
        )
        entries.append((quote, omitted))

    # Reserve every omission notice first so later files can always be named;
    # headings, fences, separators and notices all count toward the budget.
    remaining = _MAX_QUOTED_TOTAL_CHARS - len("\n\n".join(omitted for _, omitted in entries))
    sections: list[str] = []
    for quote, omitted in entries:
        extra = len(quote) - len(omitted) if quote is not None else 0
        if quote is not None and extra <= remaining:
            sections.append(quote)
            remaining -= extra
        else:
            sections.append(omitted)
    return sections


def _api_contract_files(root: Path, routes: str, inventory: dict | None = None) -> list[tuple[str, str]]:
    """Follow literal FQCN references through longest-first Composer PSR-4 mappings."""
    inventory = inventory if inventory is not None else collect_inventory(str(root))
    available = inventory["files"]
    mappings = sorted(
        (item for item in inventory["psr4"] if item["resolved"]),
        key=lambda item: -len(item["namespace"]),
    )
    files: dict[str, str] = {}
    sources = [routes]
    remaining = _MAX_QUOTED_TOTAL_CHARS
    for source in sources:
        for name in re.findall(r"\b[A-Za-z_]\w*\\(?:[A-Za-z_]\w*\\)*[A-Za-z_]\w*", source):
            for mapping in mappings:
                if not name.startswith(mapping["namespace"]):
                    continue
                relative = (Path(mapping["path"]) / (
                    name[len(mapping["namespace"]):].replace("\\", "/") + ".php"
                )).as_posix()
                if relative not in available:
                    continue
                if relative not in files:
                    files[relative] = "php"
                    body = available[relative]["content"]
                    if len(body) <= min(_MAX_QUOTED_FILE_CHARS, remaining):
                        remaining -= len(body)
                        sources.append(body)
                break
    return list(files.items())


def _repo_inventory(
    repo_path: str, scope: str = "fullstack", task_text: str = "",
    previous_files: list[str] | None = None,
    project: dict | None = None,
) -> str:
    """
    Describe what the cloned repository already contains, for the prompts.

    The model otherwise sees only the issue text and cannot distinguish a
    greenfield clone from an application that already has the feature's
    foundations.  Observed consequence: on a repository that already had
    ``/api/tasks``, a frontend-only issue made the coder re-emit the whole
    backend including a second ``create_tasks_table`` migration, and the PHP
    layer then failed with "table already exists" on every attempt.

    Every scope gets the backend listing, route files and default seeder.
    Files named by the issue or plan get complete bodies before fixed entry
    files, so modifying an existing component does not require guessing its
    implementation. Tests importing a named SFC bring their existing mount
    setup even when the issue names no test. Frontend/fullstack also get the served entry chain,
    fixture manifest and configs within the same bounded quote section. API
    class references also supply validation, serialization and pagination
    contracts; a response field alone does not establish a writable field.

    Never raises: an unreadable workspace yields an empty string and the
    prompts are built without the section, exactly as before; one unreadable
    file is named, never fatal for the rest.
    """
    try:
        root = Path(repo_path)
        if not root.is_dir():
            return ""

        project = project or {}
        application_root = project.get("application_root", "")
        inventory = collect_inventory(str(root), application_root=application_root)
        files = inventory["files"]
        routing = _routing_metadata(inventory, application_root)
        lines = list(inventory["warnings"]) + list(inventory["unresolved"])
        referenced_files = [
            (path, Path(path).suffix.lstrip(".")) for path in (previous_files or [])
            if path in files
        ]
        for prefix in dict.fromkeys((application_root, project.get("frontend_root", ""))):
            for path, language in _INVENTORY_QUOTED_FILES:
                if scope != "backend" or path == "database/seeders/DatabaseSeeder.php":
                    referenced_files.append(((Path(prefix) / path).as_posix(), language))
        api_files: list[tuple[str, str]] = []
        test_files: list[str] = []
        directories: dict[str, list[str]] = {}
        for path, entry in files.items():
            if entry["kind"] == "rule":
                continue
            directory, _, name = path.rpartition("/")
            directories.setdefault(directory, []).append(name)
            if re.search(r"\.(?:test|spec)\.[cm]?[jt]sx?$", path):
                test_files.append(path)
            pattern = rf"(?<![\w./-])(?:{re.escape(path)}|{re.escape(name)})(?![\w./-])"
            if task_text and re.search(pattern, task_text):
                referenced_files.append((path, Path(path).suffix.lstrip(".")))
        for directory, names in directories.items():
            cap = len(names) if "migrations" in Path(directory).parts else 60
            suffix = f" … (+{len(names) - cap} omitted)" if len(names) > cap else ""
            lines.append(f"- {directory or '.'}/: {', '.join(f'{directory}/{name}'.lstrip('/') for name in names[:cap])}{suffix}")

        targets = {(root / path).resolve() for path, _ in referenced_files if path.endswith(".vue") and path in files}
        e2e_names = {re.sub(r"(?<!^)(?=[A-Z])", "-", path.stem).lower() for path in targets}
        # shortcut: relative SFC imports; Vite aliases need a resolver for alias-only suites.
        for relative in test_files if targets else []:
            path = root / relative
            if "e2e" in Path(relative).parts and path.name.split(".")[0] in e2e_names:
                referenced_files.append((relative, path.suffix.lstrip(".")))
                continue
            if not path.resolve().is_relative_to(root.resolve()):
                continue
            try:
                with path.open(encoding="utf-8") as handle:
                    body = handle.read(_MAX_QUOTED_FILE_CHARS + 1)
            except (OSError, UnicodeDecodeError):
                continue
            imports = re.findall(r"""from\s*['"](\.[^'"]+\.vue)['"]""", body)
            if any((path.parent / name).resolve() in targets for name in imports):
                referenced_files.append((relative, path.suffix.lstrip(".")))

        api_context = task_text
        if scope == "frontend":
            for relative, _ in referenced_files:
                path = root / relative
                if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
                    continue
                try:
                    with path.open(encoding="utf-8") as handle:
                        api_context += "\n" + handle.read(_MAX_QUOTED_FILE_CHARS)
                except (OSError, UnicodeDecodeError):
                    continue

        for relative in sorted(routing["routes"]):
            route_file = root / relative
            if not route_file.is_file():
                continue
            try:
                body = route_file.read_text(encoding="utf-8", errors="replace").strip()
            except OSError as exc:
                lines.append(f"\n{relative}: exists, body omitted (unreadable: {type(exc).__name__}).")
                continue
            if routing["routes"][relative] & {"api", "unknown"}:
                contract_routes = body
                if (
                    scope == "frontend" and (targets or "/api/" in task_text)
                    and not re.search(r"(?:Route::|->)(?:prefix|group)\s*\(", body)
                ):
                    # shortcut: literal ungrouped routes; grouped routes keep all contracts.
                    relevant = [
                        route for route in re.findall(r"Route::[^;]+;", body)
                        if any(
                            re.search(rf"{re.escape('/api/' + uri.strip('/'))}(?![\w-])", api_context)
                            for uri in re.findall(r"""Route::\w+\(\s*['"]([^'"]+)['"]""", route)
                        )
                    ]
                    aliases = "\n".join(relevant)
                    imports = []
                    for name, alias in re.findall(r"use\s+([\w\\]+)(?:\s+as\s+(\w+))?;", body):
                        alias = alias or name.rsplit("\\", 1)[-1]
                        if re.search(rf"\b{re.escape(alias)}::", aliases):
                            imports.append(f"use {name};")
                    contract_routes = "\n".join(imports + relevant)
                api_files.extend(_api_contract_files(root, contract_routes, inventory))
                if re.search(r"\buse\s+[^;]*\{|::\s*\$", body):
                    lines.append(f"{relative}: grouped/dynamic class references unresolved; no complete PHP resolver.")
            referenced_files.append((relative, "php"))

        if scope != "backend":
            for path, entry in files.items():
                if path.endswith((".js", ".ts", ".vue", ".blade.php")) and re.search(
                    r"\bcreateApp\s*\(|\.mount\s*\(|@vite\b", entry["content"]
                ):
                    referenced_files.append((path, Path(path).suffix.lstrip(".")))
                    for imported in re.findall(r"""from\s*['"](\.[^'"]+\.vue)['"]""", entry["content"]):
                        target = os.path.normpath(str(Path(path).parent / imported))
                        if target in files:
                            referenced_files.append((target, "vue"))

        lines += _quoted_entry_files(root, scope, referenced_files + api_files, inventory)
        project_prefix = ""
        if project.get("project_root") and project.get("git_root"):
            project_prefix = Path(project["project_root"]).relative_to(project["git_root"]).as_posix()
        containing_root = root / project_prefix
        snapshot = collect_architecture(str(containing_root), {
            **project, "root": str(root / application_root),
            "project_root": str(containing_root), "git_root": str(root),
            "application_root": application_root,
        })
        paths = [
            Path(path).relative_to(project_prefix).as_posix()
            for path, _ in referenced_files + api_files
            if Path(path).is_relative_to(project_prefix)
        ]
        rules = {rule["path"]: rule for rule in load_project_rules(str(containing_root), task_text, paths)}
        external = project.get("project_root") or project.get("root")
        if external and Path(external) != containing_root:
            rules.update({rule["path"]: rule for rule in load_project_rules(
                external, task_text, paths, evidence_repo_path=str(containing_root)
            )})
        if project:
            lines.insert(0, (
                "SEPARATE APPLICATION LAYOUT (all FILE/DELETE paths are git-repository-relative): "
                f"Laravel API backend = {application_root or '.'}/; "
                f"standalone SPA = {project.get('frontend_root') or 'absent (do not invent a location)'}. "
                "PHP/OpenAPI run in the backend; Vitest/Playwright run in the SPA. "
                "Never put SPA files, Blade-mounted Vue, Inertia or Livewire in the API backend. "
                "Architecture/rule evidence paths below are relative to the containing project "
                f"{project_prefix or '.'}/, not necessarily the FILE-block root."
            ))
        context = format_project_context(snapshot, list(rules.values()))
        if not files:
            lines.insert(0, "No eligible source evidence was collected; this does not establish a freshly scaffolded application.")
        lines.append(context)
        return (
            "These files already exist in the repository. Reuse them; do not "
            "re-create them and do not add a create-table migration for a "
            "table an existing migration already creates.\n"
            + "\n".join(lines)
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not build the repository inventory: %s", exc)
        return ""


def _last_failure_output(state: IssueState) -> tuple[str, str]:
    """
    Return ``(failure_kind, output)`` for generation rejection or the red test layer.

    Layers are checked newest-first (Playwright → Vitest → OpenAPI → PHPUnit)
    so the retry turn and the reopen note carry the failure the model actually
    has to fix.  Without this, a Vue-only issue would reopen with an empty
    note: PHPUnit never ran, so ``test_output`` is blank.
    """
    if state.get("files_written") is False:
        output = state.get("error") or _NO_FILE_BLOCKS_OUTPUT
        response = state.get("code_response", "").strip()
        if response and not state.get("error"):
            output += f"\n\nCoder response:\n{condense(response, _MAX_NOTE_CHARS)}"
        return "Code generation", output

    candidates = (
        ("Playwright (E2E tests)", state.get("playwright_passed", False),
         state.get("playwright_output", "")),
        ("Vitest (component tests)", state.get("vitest_passed", False),
         state.get("vitest_output", "")),
        ("OpenAPI documentation", state.get("openapi_passed", False),
         state.get("openapi_output", "")),
        ("PHPUnit", state.get("test_passed", False), state.get("test_output", "")),
    )
    for label, passed, output in candidates:
        if not passed and output:
            return label, output
    return "PHPUnit", state.get("test_output", "")


def _openapi_section(state: IssueState) -> str:
    """Render the documented API surface for the Merge Request body."""
    paths = state.get("openapi_paths") or []
    if not paths:
        return state.get("openapi_output", "")
    listing = "\n".join(f"- {path}" for path in paths[:_MAX_MR_OPENAPI_PATHS])
    if len(paths) > _MAX_MR_OPENAPI_PATHS:
        listing += f"\n- … {len(paths) - _MAX_MR_OPENAPI_PATHS} more"
    return f"{len(paths)} path(s) documented:\n{listing}"


def _test_report(state: IssueState) -> str:
    """Render the output of every layer that ran, for the Merge Request body."""
    sections: list[tuple[str, str]] = []
    if state.get("test_output"):
        sections.append(("PHPUnit", state["test_output"]))
    if state.get("openapi_paths") or state.get("openapi_output"):
        sections.append(("OpenAPI", _openapi_section(state)))
    if state.get("vitest_output"):
        sections.append(("Vitest", state["vitest_output"]))
    if state.get("playwright_output"):
        sections.append(("Playwright", state["playwright_output"]))
    if not sections:
        sections.append(("PHPUnit", ""))

    return "\n\n".join(
        f"### {label}\n```\n{condense(output, _MAX_MR_TEST_OUTPUT_CHARS)}\n```"
        for label, output in sections
    )


# ─────────────────────────────────────────────────────────────────────────────
# Nodes
# ─────────────────────────────────────────────────────────────────────────────

def node_setup(state: IssueState) -> dict:
    """
    Lock the issue (status → in-progress), then create the tempdir workspace,
    clone the repo and create the branch.
    Put the coder chain back on its head tier: ``_llm`` lives for the whole
    loop process, and one issue's escalations must not start the next one.

    Only a verified claim continues: the lock refuses an issue that stopped
    being pending since it was listed (paused, held by a dependency record,
    taken by another worker), and then nothing is cloned and no LLM is called
    — ``failure_reason`` routes straight to cleanup.
    """
    logger.debug("→ node_setup")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")
    _llm.reset_coder_tier()
    project = (
        inspect_project(str(configured_project_root()))
        if os.getenv("NESTI_PROJECT_PATH", "").strip() else {}
    )

    # Lock first so no other worker grabs the issue during the clone.
    lock = tool_issue_set_status(issue_id, "in_progress")
    if not lock["success"]:
        reason = f"Could not claim issue #{issue_id}: {lock['error']}"
        logger.warning("%s – leaving it untouched.", reason)
        logger.debug("← node_setup (claim refused)")
        return {"failure_reason": reason}

    workspace = tempfile.mkdtemp(prefix=f"nesti-{issue_id}-")
    git_root = os.path.join(workspace, "repo")

    cloned = tool_gitlab_clone(git_root)
    if not cloned["success"]:
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError(f"Repository clone failed: {cloned['error']}")
    relative = project.get("application_root", "")
    application = Path(git_root) / relative
    if project and (
        Path(relative).is_absolute() or ".." in Path(relative).parts
        or not application.resolve().is_relative_to(Path(git_root).resolve())
        or application.absolute() != application.resolve()
        or not (application / "artisan").is_file()
        or not (application / "composer.json").is_file()
    ):
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError("Configured application subdirectory is absent or unsafe in the clean clone; refusing bootstrap")
    repo_path = str(application)
    frontend_relative = project.get("frontend_root", "")
    frontend = Path(git_root) / frontend_relative if frontend_relative else None
    if frontend is not None and (
        Path(frontend_relative).is_absolute() or ".." in Path(frontend_relative).parts
        or frontend.absolute() != frontend.resolve()
        or not frontend.resolve().is_relative_to(Path(git_root).resolve())
        or frontend.is_relative_to(application) or application.is_relative_to(frontend)
        or not (frontend / "package.json").is_file()
    ):
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError("Configured frontend subdirectory is absent, overlapping or unsafe in the clean clone")

    branched = tool_gitlab_create_branch(git_root, issue_id, subject)
    if not branched["success"]:
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError(f"Branch creation failed: {branched['error']}")

    branch_name = branched["result"]["branch_name"]
    logger.debug("← node_setup (workspace=%s, branch=%s)", workspace, branch_name)
    return {
        "workspace": workspace,
        "repo_path": repo_path,
        "git_root": git_root,
        "frontend_path": str(frontend) if frontend is not None else "",
        "project_context": project,
        "branch_name": branch_name,
    }


def node_bootstrap(state: IssueState) -> dict:
    """
    Guarantee the clone is a Laravel 13 + Scramble + PrimeVue application.

    A greenfield repository is scaffolded inside the PHP sandbox; an existing
    Laravel app is topped up with the test-runner configs it lacks.  A
    non-Laravel PHP project is a configuration error no model can fix by
    rewriting its code, so this node mirrors node_setup's own failure
    handling — remove the workspace and raise — and TaskEngine's crash net
    reopens the issue with that reason without leaking a tempdir.
    """
    logger.debug("→ node_bootstrap")
    result = tool_laravel_bootstrap(state["repo_path"])
    if not result["success"]:
        shutil.rmtree(state.get("workspace") or "", ignore_errors=True)
        raise RuntimeError(f"Laravel bootstrap failed: {result['error']}")

    detail = result["result"]
    if detail["created"]:
        logger.info(
            "Laravel skeleton scaffolded (mode=%s): %s", detail["mode"], detail["reason"]
        )
    else:
        logger.info(
            "Existing Laravel application detected (mode=%s): %s",
            detail["mode"],
            detail["reason"],
        )
    logger.debug("← node_bootstrap (created=%s)", detail["created"])
    return {"is_laravel": True, "bootstrapped": detail["created"]}


def node_load_skills(state: IssueState) -> dict:
    """Fetch skill documentation URLs found in the issue."""
    logger.debug("→ node_load_skills")
    issue_id = state["issue_id"]
    logger.info("Loading skill URLs for issue #%s …", issue_id)

    result = tool_skill_fetch(state["issue"])
    skills = result.get("result", []) if result["success"] else []
    if not result["success"]:
        # parity: unexpected skill-loading errors are reported but
        # never block the pipeline.
        logger.warning(
            "Skill loading failed for issue #%s: %s", issue_id, result["error"]
        )
        telegram_notify(
            f"⚠️ Skill loading error for issue <b>#{issue_id}</b> – "
            f"<i>{state.get('subject', '')}</i>\n"
            f"<code>{result['error']}</code>\n"
            f"Continuing without skill documentation."
        )

    status = tool_skill_catalog_status()
    if status["success"] and status["result"].get("available"):
        catalog = status["result"]
        logger.info(
            "Skill catalog ready: %d PrimeVue component doc(s), %d Laravel topic(s) "
            "(PrimeVue %s / Laravel %s).",
            catalog["components"],
            catalog["topics"],
            catalog["primevue_version"],
            catalog["laravel_branch"],
        )
    else:
        logger.warning(
            "Vendored skill catalog unavailable – run scripts/fetch_skills.py. "
            "Prompts will carry no Laravel/PrimeVue reference documentation."
        )

    logger.info("Loaded %d skill(s) for issue #%s.", len(skills), issue_id)
    logger.debug("← node_load_skills")
    return {"skills": skills}


def _log_scope(issue_id: int, scope: str, decision: ScopeDecision, planner: str) -> None:
    """
    Emit the run's one SCOPE line: the scope the coder works in first, then its
    two sources — the issue-text classification and the planner's declaration
    ("no declaration" / "failed" when there is none).
    """
    logger.info(
        "SCOPE: %s · GitLab issue #%s · issue text: %s (%s) · planner: %s",
        scope, issue_id, decision.scope, decision.evidence(), planner,
    )


def node_plan(state: IssueState) -> dict:
    """
    Generate implementation plan via LLM planner chain.
    Appends plan turns to the shared conversation history.

    The issue is classified first (issue_scope, offline), so the plan prompt,
    its reference docs and its retrieved chunks are narrowed to the side of the
    application the issue changes.  The planner confirms or corrects that
    scope on line 1 of its plan; the result is the scope the coder works in,
    logged as the run's one ``SCOPE:`` line.
    """
    logger.debug("→ node_plan")
    issue_id = state["issue_id"]
    logger.info("Step 1 – Generating plan for issue #%s …", issue_id)

    subject = state.get("subject", "")
    description = state["issue"].get("description", "") or ""
    issue_text = f"{subject}\n{description}"
    decision = classify_issue(subject, description)
    components, topics = _PLAN_CATALOG_LIMITS[decision.scope]
    catalog_skills = _select_catalog_skills(
        issue_text,
        max_component_docs=components,
        max_topic_docs=topics,
        max_practice_docs=1,
    )
    repo_context = _repo_inventory(
        state.get("git_root") or state.get("repo_path", ""), decision.scope, issue_text,
        project=state.get("project_context"),
    )

    # memory: how similar issues were solved before (Redis solution
    # cache) and the corpus passages the keyword catalog missed (Qdrant).
    past = tool_memory_find_similar(issue_text, limit=2)
    if not past["success"]:
        logger.warning("Solution cache lookup failed: %s", past["error"])
    past_solutions = past["result"] if past["success"] else []
    retrieved = _retrieve_chunks(
        issue_text, catalog_skills, stack=_SCOPE_DOC_STACK.get(decision.scope, ""),
        phase="plan", scope=decision.scope,
    )
    if past_solutions or retrieved:
        logger.info(
            "Memory: %d past solution(s), %d doc chunk(s) selected for the plan prompt.",
            len(past_solutions),
            len(retrieved),
        )
    memory_counts = {
        "retrieved_chunks": len(retrieved),
        "past_solutions": len(past_solutions),
    }

    metrics: dict = {}
    system_prompt, user_prompt = build_plan_prompt(
        state["issue"],
        skills=state.get("skills", []),
        catalog_skills=catalog_skills,
        repo_context=repo_context,
        retrieved_chunks=retrieved,
        past_solutions=past_solutions,
        scope=decision.scope,
        scope_evidence=decision.evidence(),
        metrics=metrics,
    )
    messages = [{"role": "user", "content": user_prompt}]
    _store.save(issue_id, messages)
    memory_counts["retrieved_chunks"] = metrics["rag_rendered"]
    logger.info("Context plan · issue #%s · %s", issue_id, metrics)
    try:
        plan = _llm.generate_plan(system_prompt, user_prompt, messages=messages)
    except RuntimeError as exc:
        # All planners failed – route_after_plan will send us to node_failure.
        logger.error("All planners failed for issue #%s: %s", issue_id, exc)
        _log_scope(issue_id, decision.scope, decision, "failed")
        logger.debug("← node_plan (failed)")
        return {
            "plan": "", "scope": decision.scope, "error": str(exc),
            "messages": messages, **memory_counts,
        }

    logger.debug("Plan:\n%s", plan)
    declared = declared_scope(plan)
    scope = declared or decision.scope
    _log_scope(issue_id, scope, decision, declared or "no declaration")
    messages = _store.append(issue_id, "assistant", plan)
    logger.debug("← node_plan")
    return {"plan": plan, "scope": scope, "messages": messages, **memory_counts}


def node_code(state: IssueState) -> dict:
    """
    Generate code via LLM coder chain.
    Applies FILE blocks and DELETE directives. Appends code turns to the history.
    The prompt, its reference docs and its retrieved chunks follow ``scope``.
    """
    logger.debug("→ node_code")
    issue_id = state["issue_id"]
    attempt = state.get("attempt", 0) + 1
    max_attempts = state.get("max_attempts", _ENV_MAX_ATTEMPTS)
    scope = state.get("scope", "fullstack")
    logger.info(
        "Step 2 – Generating code (attempt %d/%d, scope: %s, provider: %s) …",
        attempt,
        max_attempts,
        scope,
        _llm.current_coder_name,
    )

    # The plan is part of the haystack here: it names the PrimeVue components
    # and Laravel artefacts the issue text may only have implied.
    haystack = (
        f"{state.get('subject', '')}\n"
        f"{state['issue'].get('description', '') or ''}\n"
        f"{state.get('plan', '')}"
    )
    components, topics = _CODE_CATALOG_LIMITS.get(scope, _CODE_CATALOG_LIMITS["fullstack"])
    catalog_skills = _select_catalog_skills(
        haystack,
        max_component_docs=components,
        max_topic_docs=topics,
    )
    # Rebuilt every attempt: the previous attempt's own files are part of the
    # repository now, and a retry must see them rather than re-inventing them.
    previous_files = state.get("written_files") or []
    repo_context = _repo_inventory(
        state.get("git_root") or state.get("repo_path", ""), scope, haystack, previous_files,
        project=state.get("project_context"),
    )

    # memory.  A narrow scope filters the doc search from the first
    # attempt.  A fullstack scope falls back to the detected stack, and only
    # from attempt 2: before node_detect_stack has run, ``stack`` is merely the
    # seeded default ("php"), and filtering on it would hide every PrimeVue doc
    # from a Vue issue's first attempt.
    detected = state.get("stack", "") if attempt > 1 else ""
    stack_filter = _SCOPE_DOC_STACK.get(scope) or (detected if detected in ("php", "vue") else "")
    retrieved = _retrieve_chunks(
        haystack, catalog_skills, stack=stack_filter, phase="code", scope=scope,
    )
    # The latest failure goes into the current request; recall only older episodes.
    recalled: list[dict] = []
    if attempt > 2:
        layer, last_output = _last_failure_output(state)
        rc = tool_memory_recall_failures(
            issue_id,
            f"{layer} failure: {condense(last_output, _EPISODE_QUERY_CHARS)}",
            attempt=attempt,
            limit=2,
        )
        if not rc["success"]:
            logger.warning("Episodic memory recall failed: %s", rc["error"])
        recalled = rc["result"] if rc["success"] else []
        if recalled:
            logger.info(
                "Memory: %d earlier failed attempt(s) recalled into the code prompt.",
                len(recalled),
            )
    memory_counts = {
        "retrieved_chunks": len(retrieved),
        "recalled_failures": len(recalled),
    }

    metrics: dict = {}
    system_prompt, user_prompt = build_code_prompt(
        state["issue"],
        state.get("plan", ""),
        skills=state.get("skills", []),
        catalog_skills=catalog_skills,
        repo_context=repo_context,
        retrieved_chunks=retrieved,
        recalled_failures=recalled,
        scope=scope,
        metrics=metrics,
    )
    base_user_chars = len(user_prompt)
    if previous_files:
        user_prompt += (
            "\n\n## Previous attempt's change set\n"
            + "\n".join(f"- `{path}`" for path in previous_files)
            + "\nRe-emit every file above that the feature still needs, even if unchanged. "
            "A test-only correction still needs the component and E2E FILE blocks. "
            "Omit a path only to deliberately revert that change; retain required DELETE directives."
        )
    change_set_chars = len(user_prompt) - base_user_chars
    feedback = ""
    if attempt > 1:
        layer, last_output = _last_failure_output(state)
        feedback = "\n\n## Latest failure\n" + _store.format_test_failure(last_output, layer)
        user_prompt += feedback
    metrics.update(
        change_set_chars=change_set_chars, latest_failure_chars=len(feedback),
        user_chars=len(user_prompt),
    )
    memory_counts["retrieved_chunks"] = metrics["rag_rendered"]
    logger.info("Context code · issue #%s · attempt %d · %s", issue_id, attempt, metrics)
    messages = _store.append(issue_id, "user", user_prompt)

    try:
        code_response = _llm.generate_code(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except RuntimeError as exc:
        # Every reachable coder failed: exhaust the shared budget so
        # route_after_code goes straight to failure without a test verdict.
        logger.error("All coding providers exhausted on attempt %d: %s", attempt, exc)
        logger.debug("← node_code (providers exhausted)")
        return {
            "code_response": "",
            "messages": messages,
            "files_written": False,
            "attempt": max_attempts,
            "error": str(exc),
            **_cleared_layer_outputs(),
            **memory_counts,
        }

    attribution = _llm.last_coder_attribution()
    logger.info(
        "Issue #%s – code generated by %s", issue_id, _llm.last_coder_label
    )
    messages = _store.append(issue_id, "assistant", code_response)

    from docker_runner import DockerRunner
    # Static file application needs neither a Docker client nor a container.
    apply_error = ""
    try:
        project = state.get("project_context") or {}
        layout = ({
            "backend_root": project.get("application_root", ""),
            "frontend_root": project.get("frontend_root", ""),
        } if project else {})
        files_written, written = DockerRunner.write_files(
            code_response, state.get("git_root") or state["repo_path"], **layout,
        )
    except ValueError as exc:
        files_written, written = False, []
        apply_error = f"File changes rejected: {exc}"
        logger.warning("%s", apply_error)
    if files_written:
        logger.info("Applied %d file change(s): %s", len(written), ", ".join(written))
    else:
        logger.warning("No file changes applied (attempt %d).", attempt)
        # A rejected/empty response must not lose earlier changes: the next
        # valid complete response still needs to restore omitted deletions.
        written = state.get("written_files") or []

    if files_written:
        pruned = _prune_stale_files(
            state.get("written_files") or [], written, state.get("git_root") or state["repo_path"]
        )
        if pruned:
            logger.info(
                "Reverted %d stale file(s) from the previous attempt: %s",
                len(pruned), ", ".join(pruned),
            )

    logger.debug("← node_code (attempt=%d, files_written=%s)", attempt, files_written)
    return {
        "code_response": code_response,
        "messages": messages,
        "files_written": files_written,
        "written_files": written,
        "attempt": attempt,
        "error": apply_error,
        "coder_provider": attribution["provider"],
        "coder_model": attribution["model"],
        "coder_billing": attribution["billing"],
        **_cleared_layer_outputs(),
        **memory_counts,
    }


def node_detect_stack(state: IssueState) -> dict:
    """
    Decide which test layers apply to the files the last attempt wrote.

    Runs between node_code and the test layers.  Detection is automatic — the
    developer never declares the stack in the issue, and the issue's scope
    never decides a layer: a backend change skips Vitest and Playwright even
    in a repository full of .vue files, a frontend-only change skips PHPUnit,
    and a change on neither side still runs PHPUnit.
    """
    logger.debug("→ node_detect_stack")

    # route_after_code admits only responses with accepted file operations.

    project = state.get("project_context") or {}
    layout = ({
        "application_root": project.get("application_root", ""),
        "frontend_root": project.get("frontend_root", ""),
    } if project else {})
    result = tool_detect_stack(
        state.get("git_root") or state["repo_path"], state.get("written_files"), **layout,
    )
    if not result["success"]:
        # Detection is advisory: a scan error must never strand an issue.
        # Fall back to previous behaviour and run the PHP layer.
        logger.warning("Stack detection failed: %s – assuming 'php'.", result["error"])
        logger.debug("← node_detect_stack (scan error)")
        return {
            "has_vue_files": False,
            "stack": "php",
            "run_phpunit": True,
            "run_frontend": False,
            "run_openapi": False,
        }

    detected = result["result"]
    stack = detected["stack"]
    has_vue = detected["has_vue"]
    run_phpunit = detected["run_phpunit"]
    run_frontend = detected["run_frontend"]
    run_openapi = detected["run_openapi"]

    logger.info(
        "Repository stack: %s (%s) – PHPUnit: %s, OpenAPI: %s, frontend layers: %s%s",
        stack,
        detected["source"],
        "yes" if run_phpunit else "skipped",
        "yes" if run_openapi else "skipped",
        "yes" if run_frontend else "skipped",
        f" [{len(detected['vue_files'])} .vue file(s)]" if has_vue else "",
    )
    logger.debug("← node_detect_stack (stack=%s)", stack)
    return {
        "has_vue_files": has_vue,
        "stack": stack,
        "run_phpunit": run_phpunit,
        "run_frontend": run_frontend,
        "is_laravel": detected["is_laravel"],
        "has_api_routes": detected["has_api_routes"],
        "run_openapi": run_openapi,
    }


def _log_layer_verdict(
    layer: str,
    passed: bool,
    state: IssueState,
    reason: str = "",
    *,
    blocked: bool = False,
) -> None:
    """Emit the one-line verdict for a test layer.

    Exactly one line per layer run, green or red, always carrying the GitLab
    issue number and the provider/model/billing that produced the code — this
    is the line an operator greps for in `docker-compose logs`. Green goes to
    INFO, red to ERROR so a failure stays visible at any sane log level.
    ``blocked`` (INFO) says the suite never started because fixture
    preparation stopped first — neither a pass nor a failed browser run.

    The attribution comes from IssueState, written by node_code from the coder
    that actually answered: the chain head moves under escalation and would
    misattribute the run.
    """
    message = (
        f"{layer} %s · GitLab issue #%s · attempt %d/%d · provider: %s · "
        "model: %s · %s" + (" · reason: %s" if reason else "")
    )
    args = [
        "BLOCKED" if blocked else ("PASSED" if passed else "FAILED"),
        state.get("issue_id", "?"),
        state.get("attempt", 0),
        state.get("max_attempts", _ENV_MAX_ATTEMPTS),
        state.get("coder_provider", "unknown"),
        state.get("coder_model", "unknown"),
        state.get("coder_billing", "unknown"),
    ]
    if reason:
        args.append(reason)
    (logger.info if passed or blocked else logger.error)(message, *args)


def node_test(state: IssueState) -> dict:
    """Run PHPUnit tests in the Docker sandbox."""
    logger.debug("→ node_test")


    logger.info("Running tests (attempt %d) …", state.get("attempt", 0))
    result = tool_docker_run_tests(state["repo_path"])
    passed = result.get("result", {}).get("passed", False) if result["success"] else False
    output = (
        result.get("result", {}).get("output", "")
        if result["success"]
        else result.get("error", "")
    )

    _log_layer_verdict("PHPUnit", passed, state)

    logger.debug("← node_test (passed=%s)", passed)
    return {"test_passed": passed, "test_output": output}


def node_openapi_test(state: IssueState) -> dict:
    """
    Export the OpenAPI document and gate on its completeness.

    Reached only when route_after_phpunit saw ``run_openapi`` True, so there is
    deliberately no guard here: routing decides whether this layer applies.
    """
    logger.debug("→ node_openapi_test")
    logger.info("Exporting OpenAPI document (attempt %d) …", state.get("attempt", 0))

    result = tool_openapi_export(state["repo_path"])
    if result["success"]:
        detail = result["result"]
        passed = detail.get("passed", False)
        output = detail.get("output", "")
        paths = detail.get("paths", [])
        undocumented = detail.get("undocumented", [])
    else:
        passed, output, paths, undocumented = False, result["error"], [], []

    if passed:
        logger.info("✓ OpenAPI: %d path(s) documented.", len(paths))
    elif undocumented:
        logger.warning(
            "OpenAPI gate failed on attempt %d – undocumented: %s",
            state.get("attempt", 0),
            ", ".join(undocumented),
        )
    else:
        logger.warning("OpenAPI gate failed on attempt %d.", state.get("attempt", 0))

    logger.debug("← node_openapi_test (passed=%s)", passed)
    return {
        "openapi_passed": passed,
        "openapi_output": output,
        "openapi_paths": paths,
    }


def node_vitest_test(state: IssueState) -> dict:
    """Run Vitest component tests in the Node sandbox."""
    logger.debug("→ node_vitest_test")
    logger.info("Running Vitest component tests (attempt %d) …", state.get("attempt", 0))

    result = tool_vitest_run_tests(state.get("frontend_path") or state["repo_path"])
    passed = result.get("result", {}).get("passed", False) if result["success"] else False
    output = (
        result.get("result", {}).get("output", "")
        if result["success"]
        else result.get("error", "")
    )

    _log_layer_verdict("Vitest", passed, state)

    logger.debug("← node_vitest_test (passed=%s)", passed)
    return {"vitest_passed": passed, "vitest_output": output}


def node_playwright_test(state: IssueState) -> dict:
    """
    Run Playwright E2E tests in the browser sandbox.

    ``fixture_request`` is set only when the sandbox verified that a declared
    fixture's seeder class and file are both absent and stopped before the
    browser started; that run logs BLOCKED rather than FAILED, and
    route_after_playwright hands it to node_pause_dependency.
    A separate SPA uses its existing API/webServer setup; no Laravel backend
    is mounted into its sandbox and the fixture-report validation is unchanged.
    """
    logger.debug("→ node_playwright_test")
    logger.info("Running Playwright E2E tests (attempt %d) …", state.get("attempt", 0))

    result = tool_playwright_run_tests(state.get("frontend_path") or state["repo_path"])
    detail = result.get("result", {}) if result["success"] else {}
    passed = bool(detail.get("passed", False))
    output = detail.get("output", "") if result["success"] else result.get("error", "")
    fixture_request = None if passed else detail.get("fixture_request")

    if fixture_request:
        _log_layer_verdict(
            "Playwright", False, state,
            reason=(
                f"fixture GET {fixture_request['endpoint']} needs "
                f"{fixture_request['seeder']}, whose class and file are absent; "
                "the browser suite did not start"
            ),
            blocked=True,
        )
    else:
        _log_layer_verdict("Playwright", passed, state)

    logger.debug("← node_playwright_test (passed=%s)", passed)
    return {
        "playwright_passed": passed,
        "playwright_output": output,
        "fixture_request": fixture_request,
    }


def node_pause_dependency(state: IssueState) -> dict:
    """
    Turn a verified missing-seeder fixture into a durable dependency.

    No planner, coder, escalation, quota check, commit or reopen happens here:

    • paused     – GitLab holds the durable record, the issue carries the
                   pause label and the backend child exists (or its creation
                   is held for an operator).  The conversation and episodes are
                   dropped only now, after the intent is durable, so the
                   resumed run starts fresh.  → cleanup
    • ineligible – the prerequisite belongs to this change's own backend work;
                   the explanation is appended to the Playwright output and the
                   shared retry budget decides (on_layer_failure / failure).
    • error      – a transport or transition failure: alert, try a plain
                   pause, and stop (→ cleanup) without node_failure, whose
                   reopen would undo the hold.
    """
    logger.debug("→ node_pause_dependency")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")
    requirement = state.get("fixture_request") or {}

    written = list(state.get("written_files") or [])
    backend_prefix = (state.get("project_context") or {}).get("application_root", "")
    if backend_prefix:
        written = [
            Path(path).relative_to(backend_prefix).as_posix() for path in written
            if Path(path).is_relative_to(backend_prefix)
        ]
    result = tool_issue_pause_for_fixture(
        issue_id, state["repo_path"], requirement, written
    )
    detail = result["result"] if result["success"] else {}
    status = detail.get("status")

    if status == "paused":
        _store.delete(issue_id)
        forgot = tool_memory_forget_episodes(issue_id)
        if not forgot["success"]:
            logger.warning("Failed to drop the episodes of issue #%s: %s", issue_id, forgot["error"])
        logger.info("Issue #%s paused: %s", issue_id, detail.get("reason", ""))
        logger.debug("← node_pause_dependency (paused)")
        return {"dependency_status": "paused", "failure_reason": detail.get("reason", "")}

    if status == "ineligible":
        reason = detail.get("reason", "")
        logger.info("Issue #%s: fixture dependency ineligible – %s", issue_id, reason)
        logger.debug("← node_pause_dependency (ineligible)")
        return {
            "dependency_status": "ineligible",
            "fixture_request": None,
            "playwright_output": f"{state.get('playwright_output', '')}\n\n{reason}".strip(),
        }

    error = detail.get("reason") if result["success"] else result["error"]
    error = error or f"unexpected dependency status {status!r}"
    held = tool_issue_set_status(
        issue_id, "paused",
        note=f"Nesti: handling this issue's fixture dependency failed ({error}); "
             "holding it for an operator.",
    )
    if held["success"]:
        message = f"Fixture dependency handling failed and the issue is held (paused): {error}"
    else:
        message = (
            f"Fixture dependency handling failed ({error}) and the pause could not be "
            f"applied ({held['error']}): the issue may keep its stale in-progress lock. "
            "Operator recovery: stop the poller, confirm no dependency issue was created, "
            "then resume the issue and clear its conversation and episodes (README, "
            "'Fixture dependencies'). Reconciliation cannot recreate a record that was "
            "never saved."
        )
    logger.error("Issue #%s: %s", issue_id, message)
    telegram_notify(
        f"⚠️ Fixture dependency handling failed for issue <b>#{issue_id}</b> – "
        f"<i>{subject}</i>\n<code>{message}</code>"
    )
    logger.debug("← node_pause_dependency (error)")
    return {"dependency_status": "error", "failure_reason": message}


def node_on_layer_failure(state: IssueState) -> dict:
    """
    Append the failing layer's output to the conversation and escalate the
    coder tier.  Runs between any red gate and the next code attempt.

    One node serves all four layers (PHPUnit, OpenAPI, Vitest, Playwright).
    They previously had two near-identical escalation nodes that differed only
    in wording and in which flags they reset; folding them together keeps the
    feedback format and the 2000-char budget defined in exactly one place —
    ``ConversationStore.append_test_failure``.

    Every layer flag is reset so the next attempt is judged on its own results
    rather than inheriting a stale pass from the previous round.

    The retry prompt must carry the standards of the layer that failed, so a
    red layer outside the scope widens it: a frontend scope whose change broke
    PHPUnit becomes fullstack. An unapplied coding response says nothing about
    the backend or frontend and never widens the scope.
    """
    logger.debug("→ node_on_layer_failure")

    quota = tool_quota_check()
    if quota["success"]:
        for name, usage in quota["result"].items():
            remaining = usage.get("remaining")
            limit = usage.get("limit")
            # A provider with no quota-introspection API (see
            # scripts.oauth.CopilotProvider) reports remaining=None honestly
            # rather than a guessed number — that must read as "unknown",
            # never as "critically low".
            if remaining is None:
                continue
            if remaining < 3 or (limit and limit > 0 and (remaining / limit) < 0.1):
                telegram_notify(
                    f"⚠️ Low Quota Warning: Provider '{name}' has only {remaining} requests left."
                )
                logger.warning("Low Quota Warning for %s: %d left", name, remaining)
    else:
        logger.warning("Failed to check provider usage quota: %s", quota["error"])

    layer, failure_output = _last_failure_output(state)
    scope = state.get("scope", "fullstack")
    widened = scope
    if state.get("files_written", False):
        side = "frontend" if layer.startswith(("Vitest", "Playwright")) else "backend"
        widened = widen(scope, side)
    logger.info(
        "Retry %d/%d – %s failed, escalating coder tier%s …",
        state.get("attempt", 0),
        state.get("max_attempts", _ENV_MAX_ATTEMPTS) - 1,
        layer,
        f"; scope widened {scope} → {widened}" if widened != scope else "",
    )
    messages = _store.append_test_failure(
        state["issue_id"], failure_output, layer=layer
    )
    # After the conversation append on purpose: a memory outage must never cost
    # the pipeline its primary corrective feedback.
    stored = tool_memory_remember_failure(
        state["issue_id"], state.get("attempt", 0), layer, failure_output
    )
    if not stored["success"]:
        logger.warning("Failed to store episodic memory: %s", stored["error"])
    _llm.escalate_coder()
    logger.debug("← node_on_layer_failure (%s)", layer)
    return {
        "messages": messages,
        "scope": widened,
        "test_passed": False,
        "openapi_passed": False,
        "vitest_passed": False,
        "playwright_passed": False,
    }


def node_commit(state: IssueState) -> dict:
    """Commit, push, open MR, close the issue, drop the history."""
    logger.debug("→ node_commit")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")

    commit_message = (
        f"feat: resolve issue #{issue_id} – {subject}\n\n"
        f"Automated implementation by AI Developer.\n"
        f"Closes #{issue_id}"
    )
    pushed = tool_gitlab_commit_and_push(
        state.get("git_root") or state["repo_path"], state["branch_name"], commit_message
    )
    if not pushed["success"]:
        # Unexpected git error – outer handler would have reopened
        # the issue; do the same here so the cleanup edge still runs.
        reason = f"Commit/push failed: {pushed['error']}"
        logger.error("%s (issue #%s)", reason, issue_id)
        telegram_notify(
            f"💥 Commit/push failed for issue <b>#{issue_id}</b> – "
            f"<i>{subject}</i>\n<code>{pushed['error']}</code>"
        )
        tool_issue_set_status(issue_id, "new", note=f"AI Developer crashed: {pushed['error']}")
        logger.debug("← node_commit (push error)")
        return {"failure_reason": reason, "error": pushed["error"]}

    if not pushed["result"]["pushed"]:
        # Nothing was staged – reopened with the same note.
        logger.warning("Nothing was pushed for issue #%s.", issue_id)
        tool_issue_set_status(issue_id, "new", note="AI Developer: no files were generated.")
        logger.debug("← node_commit (nothing pushed)")
        return {"failure_reason": "No files were generated."}

    # The attribution line is the first thing under "## Summary" on purpose:
    # a reviewer opening the MR must see which AI produced the change, and
    # whether it came from a consumer subscription or a billed platform API,
    # before reading a line of the plan.
    provider_line = (
        f"**AI provider:** {state.get('coder_provider', 'unknown')} — "
        f"{state.get('coder_billing', 'unknown')} "
        f"(model `{state.get('coder_model', 'unknown')}`)"
    )
    mr = tool_gitlab_open_mr(
        branch_name=state["branch_name"],
        issue_id=issue_id,
        subject=subject,
        description=(
            f"## Summary\n{provider_line}\n\n{state.get('plan', '')}\n\n"
            f"Application subdirectory: `{state.get('project_context', {}).get('application_root') or '.'}` "
            f"(clean configured GitLab target; no local rejected patch applied).\n\n"
            f"## Test output\n"
            f"_Stack: {state.get('stack', 'php')} · "
            f"scope: {state.get('scope', 'fullstack')} · "
            f"Laravel: {state.get('is_laravel', False)} · "
            f"bootstrapped: {state.get('bootstrapped', False)} · "
            f"memory: {state.get('retrieved_chunks', 0)} doc chunk(s), "
            f"{state.get('past_solutions', 0)} past solution(s)_\n\n"
            f"{_test_report(state)}"
        ),
    )
    if not mr["success"]:
        # parity: MR failure is logged and run_once returns False;
        # the issue stays in-progress for a human to inspect.
        logger.error("MR creation failed for issue #%s: %s", issue_id, mr["error"])
        logger.debug("← node_commit (MR failed)")
        return {"failure_reason": f"MR creation failed: {mr['error']}"}

    mr_url = mr["result"]["mr_url"]
    tool_issue_set_status(
        issue_id, "closed", note=f"AI Developer opened MR: {mr_url}"
    )
    # self-updating loop: the plan that produced this MR becomes the
    # next similar issue's "past experience".  Episodes die with the run —
    # a reopened issue reusing this iid must not recall them as its own.
    remembered = tool_memory_remember_solution(
        issue_id=issue_id,
        subject=subject,
        description=state["issue"].get("description", "") or "",
        plan=state.get("plan", ""),
        stack=state.get("stack", ""),
        mr_url=mr_url,
    )
    if not remembered["success"]:
        logger.warning(
            "Failed to store the solution of issue #%s: %s", issue_id, remembered["error"]
        )
    elif remembered["result"].get("stored"):
        logger.info("Solution of issue #%s stored in the solution cache.", issue_id)
    tool_memory_forget_episodes(issue_id)
    # Work is done – drop the conversation history for this issue.
    _store.delete(issue_id)
    logger.debug("← node_commit (mr=%s)", mr_url)
    return {"mr_url": mr_url}


def node_failure(state: IssueState) -> dict:
    """
    All attempts exhausted, planning failed, or an unrecoverable error.
    Return the issue to the pending pool with a failure note and alert Telegram.
    """
    logger.debug("→ node_failure")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")
    attempts = state.get("attempt", 0)

    if not state.get("plan", "").strip():
        reason = "Planning failed – all planning providers exhausted."
        note = (
            "AI Developer: all planning providers failed.\n"
            f"{state.get('error', '')}"
        )
        telegram_notify(
            f"❌ Planning failed for issue <b>#{issue_id}</b> – <i>{subject}</i>\n"
            f"<code>{state.get('error', '')}</code>\n"
            f"Reopening issue."
        )
    else:
        layer, failure_output = _last_failure_output(state)
        reason = f"{layer} failed after {attempts} attempt(s)."
        note = (
            f"AI Developer failed to produce passing tests ({layer}).\n\n"
            f"{condense(failure_output, _MAX_NOTE_CHARS)}"
        )
        telegram_notify(
            f"❌ Issue <b>#{issue_id}</b> – <i>{subject}</i>\n"
            f"All code generation attempts exhausted. Reopening."
        )
        logger.error("%s failed after %d attempt(s). Reopening issue #%s.", layer, attempts, issue_id)

    tool_issue_set_status(issue_id, "new", note=note)

    # Every reopened issue starts fresh, including failures before coding.
    _store.delete(issue_id)
    tool_memory_forget_episodes(issue_id)

    logger.debug("← node_failure (%s)", reason)
    return {"failure_reason": reason}


def node_cleanup(state: IssueState) -> dict:
    """Remove the tempdir workspace. Always runs (success or failure)."""
    logger.debug("→ node_cleanup")
    if state.get("workspace") and os.path.exists(state["workspace"]):
        shutil.rmtree(state["workspace"], ignore_errors=True)
        logger.info("Workspace %s removed.", state["workspace"])
    logger.debug("← node_cleanup")
    return {}
