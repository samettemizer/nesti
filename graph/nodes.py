"""
graph/nodes.py – LangGraph node functions.

Each node is a function ``(state: IssueState) -> dict`` returning a *partial
state update* — only the fields it changes.  LangGraph merges the update into
the running state.

Conversation semantics (Phase 1 preserved)
──────────────────────────────────────────
Nodes call the same ConversationStore as Phase 1 and keep its ordering:

    append(user turn) → LLM call with the updated history → append(assistant turn)

The user turn is appended *before* the LLM call on purpose: llm_client uses
``messages`` verbatim when it is non-empty (ignoring ``user_prompt``), so the
current instruction must already be inside the history or the provider would
never see it on follow-up turns (e.g. the coding phase after planning, or a
reopened issue with surviving history).

Error strategy per node
───────────────────────
• node_setup      – raises on unrecoverable git errors (after removing its own
                    tempdir); TaskEngine's try/except reopens the issue.
• node_plan       – catches RuntimeError ("all planners failed"), leaves
                    ``plan`` empty; route_after_plan then routes to failure.
• node_code       – catches RuntimeError ("all coders exhausted") and jumps
                    ``attempt`` to ``max_attempts`` so route_after_phpunit
                    routes straight to failure (Phase 1 aborted immediately too).
• node_commit     – tool failures reopen the issue + notify instead of raising,
                    so the commit → cleanup edge still runs.

Test layering (Phase 4 + 5)
───────────────────────────
node_bootstrap runs right after node_setup and guarantees the clone is a
Laravel application; node_detect_stack then runs between node_code and the
test layers and decides which of them apply:

    php        → phpunit [→ openapi]
    vue        → vitest → playwright        (phpunit skipped entirely)
    fullstack  → phpunit [→ openapi] → vitest → playwright
    unknown    → phpunit                    (legacy default; never no-tests)

The optional openapi layer runs when the attempt touched routes/api.php or an
app/Http/{Controllers,Resources,Requests} file in a Laravel repo that has an
API surface.

Every layer failure funnels into one escalate-and-retry node
(node_on_layer_failure), so the retry budget (max_attempts) is shared across
all four layers rather than per layer.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

from graph.state import IssueState
from graph.tools import (
    tool_skill_fetch, tool_gitlab_clone, tool_gitlab_create_branch,
    tool_docker_run_tests, tool_gitlab_commit_and_push, tool_gitlab_open_mr,
    tool_issue_set_status, tool_detect_stack, tool_vitest_run_tests,
    tool_playwright_run_tests, tool_laravel_bootstrap, tool_openapi_export,
    tool_skill_catalog_select, tool_skill_catalog_status,
)
from llm_client import LLMClient
from conversation_store import ConversationStore
from prompt_builder import build_plan_prompt, build_code_prompt
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

# Fed into node_test's short-circuit when the coder produced no parseable
# files; on_test_failure then appends it to the history, replacing Phase 1's
# _NO_FILE_BLOCKS_FEEDBACK with the same corrective intent.
_NO_FILE_BLOCKS_OUTPUT = (
    "No files could be written or tested: the previous response did not "
    "contain any '### FILE: <path>' blocks. Output every affected file in "
    "full using the FILE format."
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _select_catalog_skills(
    text: str, max_component_docs: int, max_topic_docs: int
) -> list:
    """
    Pick vendored Laravel / PrimeVue reference docs matching *text*.

    Selection is deterministic and offline (see ``skill_catalog``).  A missing
    or broken corpus must never block a run, so any failure degrades to an
    empty list and the prompt is built without reference documentation.
    """
    result = tool_skill_catalog_select(text, max_component_docs, max_topic_docs)
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


def _prune_stale_files(
    previous: list[str], current: list[str], repo_path: str
) -> list[str]:
    """
    Delete files the previous attempt wrote that this attempt did not re-emit.

    The workspace persists across retries, so without this an attempt that
    renames a file leaves both versions behind.  For Laravel that is fatal
    rather than untidy: two ``*_create_tasks_table.php`` migrations both run
    and the second dies with "table already exists" — on every remaining
    attempt, for a reason the model cannot see in its own output.

    Retries are asked for the complete set of affected files (see
    ``ConversationStore.append_test_failure``), so anything the new response
    omits is genuinely obsolete.  Directories left empty are removed too, so a
    renamed package does not leave a stray tree in the Merge Request.
    """
    stale = [path for path in previous if path not in set(current)]
    removed: list[str] = []
    root = os.path.abspath(repo_path)

    for relative in stale:
        target = os.path.abspath(os.path.join(root, relative))
        # Never step outside the clone, whatever the model emitted as a path.
        if not target.startswith(root + os.sep) or not os.path.isfile(target):
            continue
        try:
            os.remove(target)
            removed.append(relative)
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

    return removed


# Directories whose contents the coder needs to know about, with the cap on how
# many entries each contributes. Migrations are listed in full: a duplicate
# create-table migration is the one mistake that cannot be recovered from.
_INVENTORY_DIRS = (
    ("database/migrations", 60),
    ("app/Models", 40),
    ("app/Http/Controllers", 40),
    ("app/Http/Resources", 40),
    ("app/Http/Requests", 40),
    ("app/Services", 40),
    ("resources/js/components", 40),
    ("tests/Feature", 40),
)

# Route files are quoted rather than listed: the coder must see which URIs are
# already registered, not merely that the file exists.
_INVENTORY_ROUTE_FILES = ("routes/api.php", "routes/web.php")
_MAX_ROUTE_FILE_CHARS = 1500


def _repo_inventory(repo_path: str) -> str:
    """
    Describe what the cloned repository already contains, for the prompts.

    The model otherwise sees only the issue text and cannot distinguish a
    greenfield clone from an application that already has the feature's
    foundations.  Observed consequence: on a repository that already had
    ``/api/tasks``, a frontend-only issue made the coder re-emit the whole
    backend including a second ``create_tasks_table`` migration, and the PHP
    layer then failed with "table already exists" on every attempt.

    Never raises: an unreadable workspace yields an empty string and the
    prompts are built without the section, exactly as before.
    """
    try:
        root = Path(repo_path)
        if not root.is_dir():
            return ""

        lines: list[str] = []
        for relative, cap in _INVENTORY_DIRS:
            directory = root / relative
            if not directory.is_dir():
                continue
            names = sorted(
                entry.name for entry in directory.rglob("*") if entry.is_file()
            )
            if not names:
                continue
            shown = names[:cap]
            suffix = f" … (+{len(names) - cap} more)" if len(names) > cap else ""
            lines.append(f"- {relative}/: {', '.join(shown)}{suffix}")

        for relative in _INVENTORY_ROUTE_FILES:
            route_file = root / relative
            if not route_file.is_file():
                continue
            body = route_file.read_text(encoding="utf-8", errors="replace").strip()
            if len(body) > _MAX_ROUTE_FILE_CHARS:
                body = body[:_MAX_ROUTE_FILE_CHARS] + "\n… (truncated)"
            lines.append(f"\nCurrent {relative}:\n```php\n{body}\n```")

        if not lines:
            return (
                "The repository is a freshly scaffolded Laravel application "
                "with no feature code yet."
            )
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
    Return ``(layer_label, output)`` for the test layer that ended the run.

    Layers are checked newest-first (Playwright → Vitest → OpenAPI → PHPUnit)
    so the retry turn and the reopen note carry the failure the model actually
    has to fix.  Without this, a Vue-only issue would reopen with an empty
    note: PHPUnit never ran, so ``test_output`` is blank.
    """
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
    Create tempdir workspace, clone repo, create branch.
    Lock the issue (status → in-progress) so no other worker picks it up.
    """
    logger.debug("→ node_setup")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")

    # Lock first so no other worker grabs the issue during the clone.
    # Phase 1 ignored the lock result as well – log and continue.
    lock = tool_issue_set_status(issue_id, "in_progress")
    if not lock["success"]:
        logger.warning("Could not lock issue #%s: %s", issue_id, lock["error"])

    workspace = tempfile.mkdtemp(prefix=f"ai-dev-{issue_id}-")
    repo_path = os.path.join(workspace, "repo")

    cloned = tool_gitlab_clone(repo_path)
    if not cloned["success"]:
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError(f"Repository clone failed: {cloned['error']}")

    branched = tool_gitlab_create_branch(repo_path, issue_id, subject)
    if not branched["success"]:
        shutil.rmtree(workspace, ignore_errors=True)
        raise RuntimeError(f"Branch creation failed: {branched['error']}")

    branch_name = branched["result"]["branch_name"]
    logger.debug("← node_setup (workspace=%s, branch=%s)", workspace, branch_name)
    return {
        "workspace": workspace,
        "repo_path": repo_path,
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
    logger.info("Phase 0 – Loading skill URLs for issue #%s …", issue_id)

    result = tool_skill_fetch(state["issue"])
    skills = result.get("result", []) if result["success"] else []
    if not result["success"]:
        # Phase 1 parity: unexpected skill-loading errors are reported but
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

    logger.info("Phase 0 – Loaded %d skill(s) for issue #%s.", len(skills), issue_id)
    logger.debug("← node_load_skills")
    return {"skills": skills}


def node_plan(state: IssueState) -> dict:
    """
    Generate implementation plan via LLM planner chain.
    Appends plan turns to the shared conversation history.
    """
    logger.debug("→ node_plan")
    issue_id = state["issue_id"]
    logger.info("Phase 1 – Generating plan for issue #%s …", issue_id)

    catalog_skills = _select_catalog_skills(
        f"{state.get('subject', '')}\n{state['issue'].get('description', '') or ''}",
        max_component_docs=3,
        max_topic_docs=2,
    )
    repo_context = _repo_inventory(state.get("repo_path", ""))
    system_prompt, user_prompt = build_plan_prompt(
        state["issue"],
        skills=state.get("skills", []),
        catalog_skills=catalog_skills,
        repo_context=repo_context,
    )
    prior = _store.load(issue_id)
    if prior:
        logger.info(
            "Loaded %d message(s) from conversation history for issue #%s.",
            len(prior),
            issue_id,
        )

    # Record the request first so the provider sees it inside the history.
    messages = _store.append(issue_id, "user", user_prompt)
    try:
        plan = _llm.generate_plan(system_prompt, user_prompt, messages=messages)
    except RuntimeError as exc:
        # All planners failed – route_after_plan will send us to node_failure.
        logger.error("All planners failed for issue #%s: %s", issue_id, exc)
        logger.debug("← node_plan (failed)")
        return {"plan": "", "error": str(exc), "messages": messages}

    logger.debug("Plan:\n%s", plan)
    messages = _store.append(issue_id, "assistant", plan)
    logger.debug("← node_plan")
    return {"plan": plan, "messages": messages}


def node_code(state: IssueState) -> dict:
    """
    Generate code via LLM coder chain.
    Writes FILE blocks into the repo. Appends code turns to the history.
    """
    logger.debug("→ node_code")
    issue_id = state["issue_id"]
    attempt = state.get("attempt", 0) + 1
    max_attempts = state.get("max_attempts", _ENV_MAX_ATTEMPTS)
    logger.info(
        "Phase 2 – Generating code (attempt %d/%d, provider: %s) …",
        attempt,
        max_attempts,
        _llm.current_coder_name,
    )

    # The plan is part of the haystack here: it names the PrimeVue components
    # and Laravel artefacts the issue text may only have implied.  One topic
    # doc instead of two keeps room for the plan itself in the coder context.
    catalog_skills = _select_catalog_skills(
        f"{state.get('subject', '')}\n"
        f"{state['issue'].get('description', '') or ''}\n"
        f"{state.get('plan', '')}",
        max_component_docs=3,
        max_topic_docs=1,
    )
    # Rebuilt every attempt: the previous attempt's own files are part of the
    # repository now, and a retry must see them rather than re-inventing them.
    repo_context = _repo_inventory(state.get("repo_path", ""))
    system_prompt, user_prompt = build_code_prompt(
        state["issue"],
        state.get("plan", ""),
        skills=state.get("skills", []),
        catalog_skills=catalog_skills,
        repo_context=repo_context,
    )
    messages = _store.append(issue_id, "user", user_prompt)

    try:
        code_response = _llm.generate_code(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            messages=messages,
        )
    except RuntimeError as exc:
        # Every reachable coder failed. Phase 1 aborted the retry loop
        # immediately; jumping attempt to max_attempts makes route_after_phpunit
        # deterministically route to node_failure (node_detect_stack keeps
        # run_phpunit=True when no files were written, so that is the router
        # this path reaches).
        logger.error("All coding providers exhausted on attempt %d: %s", attempt, exc)
        logger.debug("← node_code (providers exhausted)")
        return {
            "code_response": "",
            "messages": messages,
            "files_written": False,
            "attempt": max_attempts,
            "error": str(exc),
        }

    messages = _store.append(issue_id, "assistant", code_response)

    from docker_runner import DockerRunner
    # write_files is a @staticmethod – call it on the class; instantiating
    # DockerRunner would open a Docker socket that file writing doesn't need.
    files_written, written = DockerRunner.write_files(code_response, state["repo_path"])
    if files_written:
        logger.info("Wrote %d file(s): %s", len(written), ", ".join(written))
    else:
        logger.warning("No FILE blocks found in LLM output (attempt %d).", attempt)

    if files_written:
        pruned = _prune_stale_files(
            state.get("written_files") or [], written, state["repo_path"]
        )
        if pruned:
            logger.info(
                "Removed %d stale file(s) from the previous attempt: %s",
                len(pruned), ", ".join(pruned),
            )

    logger.debug("← node_code (attempt=%d, files_written=%s)", attempt, files_written)
    return {
        "code_response": code_response,
        "messages": messages,
        "files_written": files_written,
        "written_files": written,
        "attempt": attempt,
    }


def node_detect_stack(state: IssueState) -> dict:
    """
    Decide which test layers apply to the current workspace.

    Runs between node_code and the test layers.  Detection is automatic — the
    developer never declares the stack in the issue.
    """
    logger.debug("→ node_detect_stack")

    # No parseable FILE blocks this attempt: there is nothing new to classify.
    # Route to node_test anyway — its files_written guard turns the attempt
    # into a failure with corrective feedback (Phase 1 behaviour, preserved).
    if not state.get("files_written", False):
        logger.debug("← node_detect_stack (no files written – deferring to node_test guard)")
        return {
            "has_vue_files": False,
            "stack": "unknown",
            "run_phpunit": True,
            "run_openapi": False,
        }

    result = tool_detect_stack(state["repo_path"], state.get("written_files"))
    if not result["success"]:
        # Detection is advisory: a scan error must never strand an issue.
        # Fall back to the pre-Phase-4 behaviour and run the PHP layer.
        logger.warning("Stack detection failed: %s – assuming 'php'.", result["error"])
        logger.debug("← node_detect_stack (scan error)")
        return {
            "has_vue_files": False,
            "stack": "php",
            "run_phpunit": True,
            "run_openapi": False,
        }

    detected = result["result"]
    stack = detected["stack"]
    has_vue = detected["has_vue"]
    run_phpunit = detected["run_phpunit"]
    run_openapi = detected["run_openapi"]

    logger.info(
        "Stack detected: %s (%s) – PHPUnit: %s, OpenAPI: %s, frontend layers: %s%s",
        stack,
        detected["source"],
        "yes" if run_phpunit else "skipped",
        "yes" if run_openapi else "skipped",
        "yes" if has_vue else "skipped",
        f" [{len(detected['vue_files'])} .vue file(s)]" if has_vue else "",
    )
    logger.debug("← node_detect_stack (stack=%s)", stack)
    return {
        "has_vue_files": has_vue,
        "stack": stack,
        "run_phpunit": run_phpunit,
        "is_laravel": detected["is_laravel"],
        "has_api_routes": detected["has_api_routes"],
        "run_openapi": run_openapi,
    }


def node_test(state: IssueState) -> dict:
    """Run PHPUnit tests in the Docker sandbox."""
    logger.debug("→ node_test")

    # Guard: if the last code response yielded no files, running the suite
    # against the untouched clone would pass on the green baseline and lead
    # to an empty Merge Request. Short-circuit as a failed attempt instead,
    # with corrective output for the model (Phase 1 behaviour).
    if not state.get("files_written", False):
        logger.warning("Skipping test run – no files were written this attempt.")
        logger.debug("← node_test (short-circuit)")
        # When node_code hit "all coders exhausted" it stored the reason in
        # state["error"]; surface that instead of the generic no-blocks
        # message so node_failure's reopen note matches Phase 1's content.
        return {
            "test_passed": False,
            "test_output": state.get("error") or _NO_FILE_BLOCKS_OUTPUT,
        }

    logger.info("Running tests (attempt %d) …", state.get("attempt", 0))
    result = tool_docker_run_tests(state["repo_path"])
    passed = result.get("result", {}).get("passed", False) if result["success"] else False
    output = (
        result.get("result", {}).get("output", "")
        if result["success"]
        else result.get("error", "")
    )

    if passed:
        logger.info(
            "✓ Tests passed on attempt %d using %s",
            state.get("attempt", 0),
            _llm.current_coder_name,
        )
    else:
        logger.warning("Tests failed on attempt %d.", state.get("attempt", 0))

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

    result = tool_vitest_run_tests(state["repo_path"])
    passed = result.get("result", {}).get("passed", False) if result["success"] else False
    output = (
        result.get("result", {}).get("output", "")
        if result["success"]
        else result.get("error", "")
    )

    if passed:
        logger.info("✓ Vitest passed on attempt %d.", state.get("attempt", 0))
    else:
        logger.warning("Vitest failed on attempt %d.", state.get("attempt", 0))

    logger.debug("← node_vitest_test (passed=%s)", passed)
    return {"vitest_passed": passed, "vitest_output": output}


def node_playwright_test(state: IssueState) -> dict:
    """Run Playwright E2E tests in the browser sandbox."""
    logger.debug("→ node_playwright_test")
    logger.info("Running Playwright E2E tests (attempt %d) …", state.get("attempt", 0))

    result = tool_playwright_run_tests(state["repo_path"])
    passed = result.get("result", {}).get("passed", False) if result["success"] else False
    output = (
        result.get("result", {}).get("output", "")
        if result["success"]
        else result.get("error", "")
    )

    if passed:
        logger.info("✓ Playwright passed on attempt %d.", state.get("attempt", 0))
    else:
        logger.warning("Playwright failed on attempt %d.", state.get("attempt", 0))

    logger.debug("← node_playwright_test (passed=%s)", passed)
    return {"playwright_passed": passed, "playwright_output": output}


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
    """
    logger.debug("→ node_on_layer_failure")
    layer, failure_output = _last_failure_output(state)
    logger.info(
        "Retry %d/%d – %s failed, escalating coder tier …",
        state.get("attempt", 0),
        state.get("max_attempts", _ENV_MAX_ATTEMPTS) - 1,
        layer,
    )
    messages = _store.append_test_failure(
        state["issue_id"], failure_output, layer=layer
    )
    _llm.escalate_coder()
    logger.debug("← node_on_layer_failure (%s)", layer)
    return {
        "messages": messages,
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
        state["repo_path"], state["branch_name"], commit_message
    )
    if not pushed["success"]:
        # Unexpected git error – Phase 1's outer handler would have reopened
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
        # Nothing was staged – Phase 1 reopened with the same note.
        logger.warning("Nothing was pushed for issue #%s.", issue_id)
        tool_issue_set_status(issue_id, "new", note="AI Developer: no files were generated.")
        logger.debug("← node_commit (nothing pushed)")
        return {"failure_reason": "No files were generated."}

    mr = tool_gitlab_open_mr(
        branch_name=state["branch_name"],
        issue_id=issue_id,
        subject=subject,
        description=(
            f"## Summary\n{state.get('plan', '')}\n\n"
            f"## Test output\n"
            f"_Stack: {state.get('stack', 'php')} · "
            f"Laravel: {state.get('is_laravel', False)} · "
            f"bootstrapped: {state.get('bootstrapped', False)}_\n\n"
            f"{_test_report(state)}"
        ),
    )
    if not mr["success"]:
        # Phase 1 parity: MR failure is logged and run_once returns False;
        # the issue stays in-progress for a human to inspect.
        logger.error("MR creation failed for issue #%s: %s", issue_id, mr["error"])
        logger.debug("← node_commit (MR failed)")
        return {"failure_reason": f"MR creation failed: {mr['error']}"}

    mr_url = mr["result"]["mr_url"]
    tool_issue_set_status(
        issue_id, "closed", note=f"AI Developer opened MR: {mr_url}"
    )
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
        logger.error("Tests failed after %d attempt(s). Reopening issue #%s.", attempts, issue_id)

    tool_issue_set_status(issue_id, "new", note=note)

    # Phase 1 dropped the history after exhausted coding attempts (the issue
    # is retried fresh); after a planning failure no new turns were persisted
    # by that run, so the history is kept, matching Phase 1.
    if attempts > 0:
        _store.delete(issue_id)

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
