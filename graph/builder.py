"""
graph/builder.py – assembles and compiles the LangGraph pipeline.

Topology
────────
    setup → load_skills → plan ─┬→ code → detect_stack ─┬→ phpunit_test ─┐
                                │                       └→ vitest_test ←─┤
                                │                                        │
                                │   phpunit_test ─→ vitest_test ─→ playwright_test ─→ commit ─┐
                                │        │               │                │                   ├→ cleanup → END
                                │        ↓               ↓                ↓                   │
                                │  on_test_failure   on_frontend_test_failure                 │
                                │        └───────────────┴────→ code (loop)                   │
                                └──────────────────────────────→ failure ─────────────────────┘

``detect_stack`` picks the entry layer: PHP-bearing stacks start at
``phpunit_test``; a frontend-only stack jumps straight to ``vitest_test`` so a
repository without composer.json is never forced through PHPUnit.  Each layer
then either advances to the next applicable one or funnels into its escalation
node, which loops back to ``code``.

``cleanup`` is reached from both ``commit`` and ``failure``, so the tempdir
workspace is always removed regardless of outcome.
"""

from langgraph.graph import StateGraph, END

from graph.state import IssueState
from graph.nodes import (
    node_setup, node_load_skills, node_plan, node_code,
    node_detect_stack,
    node_test, node_on_test_failure,
    node_vitest_test, node_playwright_test, node_on_frontend_test_failure,
    node_commit, node_failure, node_cleanup,
)
from graph.edges import (
    route_after_plan,
    route_after_detect_stack,
    route_after_phpunit,
    route_after_vitest,
    route_after_playwright,
)


def build_graph():
    g = StateGraph(IssueState)

    # ── Register nodes ────────────────────────────────────────────────────
    g.add_node("setup",                    node_setup)
    g.add_node("load_skills",              node_load_skills)
    g.add_node("plan",                     node_plan)
    g.add_node("code",                     node_code)
    g.add_node("detect_stack",             node_detect_stack)
    g.add_node("phpunit_test",             node_test)
    g.add_node("on_test_failure",          node_on_test_failure)
    g.add_node("vitest_test",              node_vitest_test)
    g.add_node("playwright_test",          node_playwright_test)
    g.add_node("on_frontend_test_failure", node_on_frontend_test_failure)
    g.add_node("commit",                   node_commit)
    g.add_node("failure",                  node_failure)
    g.add_node("cleanup",                  node_cleanup)

    # ── Entry point ───────────────────────────────────────────────────────
    g.set_entry_point("setup")

    # ── Linear edges ──────────────────────────────────────────────────────
    g.add_edge("setup",                    "load_skills")
    g.add_edge("load_skills",              "plan")
    g.add_edge("code",                     "detect_stack")
    g.add_edge("on_test_failure",          "code")     # loop back after failure
    g.add_edge("on_frontend_test_failure", "code")     # same loop, frontend layers
    g.add_edge("commit",                   "cleanup")
    g.add_edge("failure",                  "cleanup")
    g.add_edge("cleanup",                  END)

    # ── Conditional edges ─────────────────────────────────────────────────
    g.add_conditional_edges(
        "plan",
        route_after_plan,
        {"code": "code", "failure": "failure"},
    )
    g.add_conditional_edges(
        "detect_stack",
        route_after_detect_stack,
        {
            "phpunit_test": "phpunit_test",
            "vitest_test":  "vitest_test",
        },
    )
    g.add_conditional_edges(
        "phpunit_test",
        route_after_phpunit,
        {
            "commit":          "commit",
            "vitest_test":     "vitest_test",
            "on_test_failure": "on_test_failure",
            "failure":         "failure",
        },
    )
    g.add_conditional_edges(
        "vitest_test",
        route_after_vitest,
        {
            "playwright_test":          "playwright_test",
            "on_frontend_test_failure": "on_frontend_test_failure",
            "failure":                  "failure",
        },
    )
    g.add_conditional_edges(
        "playwright_test",
        route_after_playwright,
        {
            "commit":                   "commit",
            "on_frontend_test_failure": "on_frontend_test_failure",
            "failure":                  "failure",
        },
    )

    return g.compile()


# Module-level compiled graph — import this from task_engine.py
graph = build_graph()
