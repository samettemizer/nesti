"""
graph/edges.py – conditional routing logic.

Each function inspects the current state and returns a string matching a key
of the corresponding ``add_conditional_edges`` mapping in graph/builder.py.

Test layering (Phase 4 + 5)
───────────────────────────
``route_after_test`` was replaced by one router per layer:

    detect_stack ─→ phpunit_test ─→ openapi_test ─→ vitest_test
                                                 ─→ playwright_test ─→ commit

Each router skips forward over the layers that do not apply to *this change*
(the ``run_*`` gates node_detect_stack derives from the files the coder wrote):
a backend change never starts a Node container even in a repository full of
.vue files, a frontend-only change never starts a PHP one, and a change that
did not touch the API surface never pays for a Scramble export.  Every layer
shares the same retry budget: ``attempt`` is incremented once per node_code
run, not once per layer, and every red gate routes to the same escalation node.

Fixture dependencies
────────────────────
``route_after_playwright`` sends a verified missing-seeder report to
``pause_dependency`` before it looks at the budget; that node either pauses
the issue (→ cleanup) or finds the prerequisite belongs to the change itself
(→ the shared retry budget).  ``route_after_setup`` lets only a verified claim
reach the clone and the LLMs.
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


def route_after_setup(state: IssueState) -> str:
    """
    After node_setup:
      - the issue was claimed and cloned → "bootstrap"
      - the claim was refused            → "cleanup"

    Only a verified claim may clone, bootstrap or reach an LLM: an issue that
    stopped being pending between listing and locking (paused, held by a
    dependency record, taken by someone else) is left exactly as it is.
    """
    if state.get("failure_reason"):
        logger.debug("route_after_setup → cleanup (%s)", state["failure_reason"])
        return "cleanup"
    return "bootstrap"


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
      - run_phpunit (the change touched PHP, or nothing else applies) → "phpunit_test"
      - frontend-only change, or a "vue" stack                          → "vitest_test"

    The "vue" branch is the whole point of stack detection: a repository with
    no composer.json cannot run PHPUnit, and forcing it through that layer
    burned every retry and drove the issue to permanent failure.  run_phpunit
    is True whenever the frontend layers do not run, so an unclassified change
    is still tested rather than waved through to commit.

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
      - passed + frontend touched    → "vitest_test"
      - passed + backend only        → "commit"
      - failed + retries remain      → "on_layer_failure"
      - failed + no retries          → "failure"
    """
    if state.get("test_passed", False):
        if state.get("run_openapi", False):
            logger.debug("route_after_phpunit → openapi_test")
            return "openapi_test"
        if state.get("run_frontend", False):
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
      - passed + frontend touched   → "vitest_test"
      - passed + backend only       → "commit"
      - failed + retries remain     → "on_layer_failure"
      - failed + no retries         → "failure"

    A red gate here means an /api route exists that the exported OpenAPI
    document does not describe.  That is a code defect the coder can fix, so it
    consumes a retry exactly like a failing assertion.
    """
    if state.get("openapi_passed", False):
        if state.get("run_frontend", False):
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
      - passed                              → "commit"
      - verified missing-seeder fixture     → "pause_dependency" (before the budget)
      - failed + retries remain             → "on_layer_failure"
      - failed + no retries                 → "failure"

    A fixture request means the browser never started because a declared
    seeder genuinely does not exist; no code attempt can fix a prerequisite
    that belongs to the target branch, so it is checked before the budget —
    even on the last attempt.
    """
    if state.get("playwright_passed", False):
        logger.debug("route_after_playwright → commit")
        return "commit"
    if state.get("fixture_request"):
        logger.debug("route_after_playwright → pause_dependency")
        return "pause_dependency"
    target = _retry_or_fail(state, "on_layer_failure")
    logger.debug("route_after_playwright → %s", target)
    return target


def route_after_dependency_pause(state: IssueState) -> str:
    """
    After node_pause_dependency:
      - ineligible (the prerequisite is this change's own backend work)
        → the shared retry budget: "on_layer_failure" or "failure"
      - paused, or a transport error already reported → "cleanup"

    A paused or errored parent never reaches node_failure: reopening it would
    undo the hold, and another code attempt cannot create a merged seeder.
    """
    if state.get("dependency_status") == "ineligible":
        target = _retry_or_fail(state, "on_layer_failure")
        logger.debug("route_after_dependency_pause → %s", target)
        return target
    logger.debug("route_after_dependency_pause → cleanup (%s)", state.get("dependency_status"))
    return "cleanup"
