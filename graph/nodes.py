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
                    ``attempt`` to ``max_attempts`` so route_after_test routes
                    straight to failure (Phase 1 aborted immediately too).
• node_commit     – tool failures reopen the issue + notify instead of raising,
                    so the commit → cleanup edge still runs.
"""

import logging
import os
import shutil
import tempfile

from graph.state import IssueState
from graph.tools import (
    tool_skill_fetch, tool_gitlab_clone, tool_gitlab_create_branch,
    tool_docker_run_tests, tool_gitlab_commit_and_push, tool_gitlab_open_mr,
    tool_redmine_set_status,
)
from llm_client import LLMClient
from conversation_store import ConversationStore
from prompt_builder import build_plan_prompt, build_code_prompt
from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)

_llm = LLMClient()
_store = ConversationStore()

# Phase 1 truncation limits, unchanged.
_MAX_NOTE_CHARS = 1000
_MAX_MR_TEST_OUTPUT_CHARS = 2000

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
# Nodes
# ─────────────────────────────────────────────────────────────────────────────

def node_setup(state: IssueState) -> dict:
    """
    Create tempdir workspace, clone repo, create branch.
    Lock the Redmine issue (status → in-progress).
    """
    logger.debug("→ node_setup")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")

    # Lock first so no other worker grabs the issue during the clone.
    # Phase 1 ignored the lock result as well – log and continue.
    lock = tool_redmine_set_status(issue_id, "in_progress")
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

    system_prompt, user_prompt = build_plan_prompt(
        state["issue"], skills=state.get("skills", [])
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

    system_prompt, user_prompt = build_code_prompt(
        state["issue"], state.get("plan", ""), skills=state.get("skills", [])
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
        # immediately; jumping attempt to max_attempts makes route_after_test
        # deterministically route to node_failure.
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

    logger.debug("← node_code (attempt=%d, files_written=%s)", attempt, files_written)
    return {
        "code_response": code_response,
        "messages": messages,
        "files_written": files_written,
        "attempt": attempt,
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


def node_on_test_failure(state: IssueState) -> dict:
    """
    Append the test failure to the conversation and escalate the coder tier.
    Runs between a failed test and the next code attempt.
    """
    logger.debug("→ node_on_test_failure")
    logger.info(
        "Retry %d/%d – escalating coder tier …",
        state.get("attempt", 0),
        state.get("max_attempts", _ENV_MAX_ATTEMPTS) - 1,
    )
    messages = _store.append_test_failure(state["issue_id"], state.get("test_output", ""))
    _llm.escalate_coder()
    logger.debug("← node_on_test_failure")
    return {"messages": messages}


def node_commit(state: IssueState) -> dict:
    """Commit, push, open MR, close the Redmine issue, drop the history."""
    logger.debug("→ node_commit")
    issue_id = state["issue_id"]
    subject = state.get("subject", f"issue-{issue_id}")

    commit_message = (
        f"feat: resolve issue #{issue_id} – {subject}\n\n"
        f"Automated implementation by AI Developer.\n"
        f"Redmine issue: #{issue_id}"
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
        tool_redmine_set_status(issue_id, "new", note=f"AI Developer crashed: {pushed['error']}")
        logger.debug("← node_commit (push error)")
        return {"failure_reason": reason, "error": pushed["error"]}

    if not pushed["result"]["pushed"]:
        # Nothing was staged – Phase 1 reopened with the same note.
        logger.warning("Nothing was pushed for issue #%s.", issue_id)
        tool_redmine_set_status(issue_id, "new", note="AI Developer: no files were generated.")
        logger.debug("← node_commit (nothing pushed)")
        return {"failure_reason": "No files were generated."}

    mr = tool_gitlab_open_mr(
        branch_name=state["branch_name"],
        issue_id=issue_id,
        subject=subject,
        description=(
            f"## Summary\n{state.get('plan', '')}\n\n"
            f"## Test output\n```\n"
            f"{state.get('test_output', '')[:_MAX_MR_TEST_OUTPUT_CHARS]}\n```"
        ),
    )
    if not mr["success"]:
        # Phase 1 parity: MR failure is logged and run_once returns False;
        # the issue stays in-progress for a human to inspect.
        logger.error("MR creation failed for issue #%s: %s", issue_id, mr["error"])
        logger.debug("← node_commit (MR failed)")
        return {"failure_reason": f"MR creation failed: {mr['error']}"}

    mr_url = mr["result"]["mr_url"]
    tool_redmine_set_status(
        issue_id, "closed", note=f"AI Developer opened MR: {mr_url}"
    )
    # Work is done – drop the conversation history for this issue.
    _store.delete(issue_id)
    logger.debug("← node_commit (mr=%s)", mr_url)
    return {"mr_url": mr_url}


def node_failure(state: IssueState) -> dict:
    """
    All attempts exhausted, planning failed, or an unrecoverable error.
    Reopen the Redmine issue with a failure note and send a Telegram alert.
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
        reason = f"Tests failed after {attempts} attempt(s)."
        note = (
            "AI Developer failed to produce passing tests.\n\n"
            f"{state.get('test_output', '')[:_MAX_NOTE_CHARS]}"
        )
        telegram_notify(
            f"❌ Issue <b>#{issue_id}</b> – <i>{subject}</i>\n"
            f"All code generation attempts exhausted. Reopening."
        )
        logger.error("Tests failed after %d attempt(s). Reopening issue #%s.", attempts, issue_id)

    tool_redmine_set_status(issue_id, "new", note=note)

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
