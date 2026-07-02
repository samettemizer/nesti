"""
graph/edges.py – conditional routing logic.

Each function inspects the current state and returns a string matching a key
of the corresponding ``add_conditional_edges`` mapping in graph/builder.py.
"""

import logging
import os

from graph.state import IssueState

logger = logging.getLogger(__name__)

# Fallback when the state lacks max_attempts (e.g. isolated node tests);
# TaskEngine always seeds max_attempts from the same env var.
MAX_ATTEMPTS = int(os.environ.get("MAX_CODE_RETRIES", "2")) + 1


def route_after_test(state: IssueState) -> str:
    """
    After node_test:
      - tests passed → "commit"
      - tests failed + retries remain → "on_test_failure"
      - tests failed + no retries → "failure"
    """
    if state.get("test_passed", False):
        logger.debug("route_after_test → commit")
        return "commit"
    if state.get("attempt", 0) < state.get("max_attempts", MAX_ATTEMPTS):
        logger.debug("route_after_test → on_test_failure")
        return "on_test_failure"
    logger.debug("route_after_test → failure")
    return "failure"


def route_after_plan(state: IssueState) -> str:
    """
    After node_plan:
      - plan is non-empty → "code"
      - plan is empty (all planners failed) → "failure"
    """
    if state.get("plan", "").strip():
        logger.debug("route_after_plan → code")
        return "code"
    logger.debug("route_after_plan → failure")
    return "failure"
