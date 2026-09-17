"""
graph/edges.py – conditional routing logic.

Each function inspects the current state and returns a string matching a key
of the corresponding ``add_conditional_edges`` mapping in graph/builder.py.

Test layering (Phase 4 + 5)
───────────────────────────
``route_after_test`` was replaced by one router per layer:

    detect_stack ─→ phpunit_test ─→ openapi_test ─→ vitest_test
                                                 ─→ playwright_test ─→ commit

Each router skips forward over the layers that do not apply to the detected
stack, so a PHP-only change never starts a Node container, a frontend-only
change never starts a PHP one, and a change that did not touch the API surface
never pays for a Scramble export.  Every layer shares the same retry budget:
``attempt`` is incremented once per node_code run, not once per layer, and
every red gate routes to the same escalation node.
"""

import logging
import os

from graph.state import IssueState

logger = logging.getLogger(__name__)

# Fallback when the state lacks max_attempts (e.g. isolated node tests);
# TaskEngine always seeds max_attempts from the same env var.
MAX_ATTEMPTS = int(os.environ.get("MAX_CODE_RETRIES", "2")) + 1


def _retry_or_fail(state: IssueState, retry_target: str) -> str:
    """Shared tail for every test router: retry while the budget allows."""
    if state.get("attempt", 0) < state.get("max_attempts", MAX_ATTEMPTS):
        return retry_target
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


def route_after_detect_stack(state: IssueState) -> str:
    """
    After node_detect_stack:
      - stack includes PHP (php / fullstack / unknown) → "phpunit_test"
      - frontend-only stack (vue)                      → "vitest_test"

    The "vue" branch is the whole point of stack detection: a repository with
    no composer.json cannot run PHPUnit, and forcing it through that layer
    burned every retry and drove the issue to permanent failure.  "unknown"
    keeps the PHP layer so an unclassified change is still tested rather than
    waved through to commit.

    node_detect_stack pins run_phpunit=True when no files were written, which
    routes here to node_test's short-circuit guard — the attempt then fails
    with corrective feedback exactly as it did before Phase 4.
    """
    if state.get("run_phpunit", True):
        logger.debug("route_after_detect_stack → phpunit_test (stack=%s)", state.get("stack"))
        return "phpunit_test"
    logger.debug("route_after_detect_stack → vitest_test (stack=%s)", state.get("stack"))
    return "vitest_test"


def route_after_phpunit(state: IssueState) -> str:
    """
    After node_test (PHPUnit):
      - passed + API surface touched → "openapi_test"
      - passed + .vue files present  → "vitest_test"
      - passed + backend only        → "commit"
      - failed + retries remain      → "on_layer_failure"
      - failed + no retries          → "failure"
    """
    if state.get("test_passed", False):
        if state.get("run_openapi", False):
            logger.debug("route_after_phpunit → openapi_test")
            return "openapi_test"
        if state.get("has_vue_files", False):
            logger.debug("route_after_phpunit → vitest_test")
            return "vitest_test"
        logger.debug("route_after_phpunit → commit")
        return "commit"
    target = _retry_or_fail(state, "on_layer_failure")
    logger.debug("route_after_phpunit → %s", target)
    return target


def route_after_openapi(state: IssueState) -> str:
    """
    After node_openapi_test:
      - passed + .vue files present → "vitest_test"
      - passed + backend only       → "commit"
      - failed + retries remain     → "on_layer_failure"
      - failed + no retries         → "failure"

    A red gate here means an /api route exists that the exported OpenAPI
    document does not describe.  That is a code defect the coder can fix, so it
    consumes a retry exactly like a failing assertion.
    """
    if state.get("openapi_passed", False):
        if state.get("has_vue_files", False):
            logger.debug("route_after_openapi → vitest_test")
            return "vitest_test"
        logger.debug("route_after_openapi → commit")
        return "commit"
    target = _retry_or_fail(state, "on_layer_failure")
    logger.debug("route_after_openapi → %s", target)
    return target


def route_after_vitest(state: IssueState) -> str:
    """
    After node_vitest_test:
      - passed                  → "playwright_test"
      - failed + retries remain → "on_layer_failure"
      - failed + no retries     → "failure"
    """
    if state.get("vitest_passed", False):
        logger.debug("route_after_vitest → playwright_test")
        return "playwright_test"
    target = _retry_or_fail(state, "on_layer_failure")
    logger.debug("route_after_vitest → %s", target)
    return target


def route_after_playwright(state: IssueState) -> str:
    """
    After node_playwright_test:
      - passed                  → "commit"
      - failed + retries remain → "on_layer_failure"
      - failed + no retries     → "failure"
    """
    if state.get("playwright_passed", False):
        logger.debug("route_after_playwright → commit")
        return "commit"
    target = _retry_or_fail(state, "on_layer_failure")
    logger.debug("route_after_playwright → %s", target)
    return target
