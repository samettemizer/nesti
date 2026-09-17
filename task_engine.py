"""
task_engine.py – thin wrapper around the LangGraph pipeline (Phase 2).

All flow control now lives in graph/builder.py:

    setup → bootstrap → load_skills → plan → code → detect_stack ⇄ phpunit /
                                              ↑                    openapi /
                                              │                    vitest /
                                              │                    playwright
                                              └── retry loop via
                                                  on_layer_failure
                                  ↓ all layers pass    ↓ retries exhausted
                                commit               failure
                                    └──→ cleanup ←──────┘

bootstrap guarantees the clone is a Laravel application; detect_stack selects
the applicable layers, so a PHP-only change never starts a Node container, a
frontend-only change never runs PHPUnit, and a change that did not touch the
API surface never pays for a Scramble export.

TaskEngine only:
  1. Polls GitLab Issues for the next pending issue (via graph.tools – no
     direct GitLabIssuesClient / GitLabClient / DockerRunner imports here).
  2. Seeds the initial IssueState and invokes the compiled graph.
  3. Acts as the crash net: if the graph itself raises, the issue is
     reopened and a Telegram alert is sent.

main.py is unchanged: it still constructs TaskEngine() and calls run_once().
"""

import logging
import os

from graph.builder import graph
from graph.state import IssueState
from graph.tools import tool_issue_list_pending, tool_issue_set_status
from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)


class TaskEngine:
    def __init__(self) -> None:
        # All clients live behind graph/tools.py now; nothing to construct.
        pass

    def run_once(self) -> bool:
        """
        Pick up one pending issue and process it end-to-end via the graph.

        Returns True if a Merge Request was successfully opened, False otherwise.
        """
        # ── 1. Fetch next pending issue ───────────────────────────────────
        listing = tool_issue_list_pending()
        if not listing["success"]:
            logger.error("Failed to query GitLab for pending issues: %s", listing["error"])
            return False

        issues = listing["result"]
        if not issues:
            logger.info("No work to do. Exiting.")
            return False

        issue = issues[0]  # oldest first (sort id:asc)
        issue_id: int = issue["id"]
        subject: str = issue.get("subject", f"issue-{issue_id}")
        logger.info("Fetched issue #%s: %s", issue_id, subject)

        max_attempts = int(os.environ.get("MAX_CODE_RETRIES", "2")) + 1

        # ── 2. Seed initial state ─────────────────────────────────────────
        initial_state: IssueState = {
            "issue":          issue,
            "issue_id":       issue_id,
            "subject":        subject,
            "skills":         [],
            "plan":           "",
            "code_response":  "",
            "repo_path":      "",
            "branch_name":    "",
            "workspace":      "",
            "messages":       [],
            "attempt":        0,
            "max_attempts":   max_attempts,
            "files_written":  False,
            "written_files":  [],
            "has_vue_files":  False,
            "stack":          "php",
            "run_phpunit":    True,
            "is_laravel":        False,
            "bootstrapped":      False,
            "has_api_routes":    False,
            "run_openapi":       False,
            "test_output":    "",
            "test_passed":    False,
            "openapi_passed":    False,
            "openapi_output":    "",
            "openapi_paths":     [],
            "vitest_passed":     False,
            "vitest_output":     "",
            "playwright_passed": False,
            "playwright_output": "",
            "mr_url":         "",
            "failure_reason": "",
            "error":          "",
        }

        # ── 3. Run the graph ──────────────────────────────────────────────
        try:
            # A fullstack retry cycle now traverses 7 nodes (on_layer_failure →
            # code → detect_stack → phpunit_test → openapi_test → vitest_test →
            # playwright_test), and setup → bootstrap → load_skills → plan adds
            # a fixed prologue; size the recursion limit so large
            # MAX_CODE_RETRIES values never trip LangGraph's default of 25.
            final_state = graph.invoke(
                initial_state,
                config={"recursion_limit": max(25, 16 + 9 * max_attempts)},
            )
            if final_state.get("mr_url"):
                logger.info("Issue #%s done – MR: %s", issue_id, final_state["mr_url"])
                return True
            logger.info(
                "Issue #%s finished without MR: %s",
                issue_id,
                final_state.get("failure_reason") or final_state.get("error") or "unknown",
            )
            return False
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Graph execution failed for issue #%s: %s", issue_id, exc)
            telegram_notify(
                f"💥 Graph crashed on issue <b>#{issue_id}</b> – <i>{subject}</i>\n"
                f"<code>{type(exc).__name__}: {exc}</code>"
            )
            tool_issue_set_status(issue_id, "new", note=f"AI Developer crashed: {exc}")
            return False
