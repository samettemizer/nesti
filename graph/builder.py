"""
graph/builder.py – assembles and compiles the LangGraph pipeline.

Topology
────────
    setup → load_skills → plan ─┬→ code → test ─┬→ commit ──┐
                                │      ▲        │           ├→ cleanup → END
                                │      └─ on_test_failure   │
                                │           ▲    (loop)     │
                                │           └──── test ─────┤
                                └────────────→ failure ─────┘

``cleanup`` is reached from both ``commit`` and ``failure``, so the tempdir
workspace is always removed regardless of outcome.
"""

from langgraph.graph import StateGraph, END

from graph.state import IssueState
from graph.nodes import (
    node_setup, node_load_skills, node_plan, node_code,
    node_test, node_on_test_failure, node_commit,
    node_failure, node_cleanup,
)
from graph.edges import route_after_test, route_after_plan


def build_graph():
    g = StateGraph(IssueState)

    # ── Register nodes ────────────────────────────────────────────────────
    g.add_node("setup",           node_setup)
    g.add_node("load_skills",     node_load_skills)
    g.add_node("plan",            node_plan)
    g.add_node("code",            node_code)
    g.add_node("test",            node_test)
    g.add_node("on_test_failure", node_on_test_failure)
    g.add_node("commit",          node_commit)
    g.add_node("failure",         node_failure)
    g.add_node("cleanup",         node_cleanup)

    # ── Entry point ───────────────────────────────────────────────────────
    g.set_entry_point("setup")

    # ── Linear edges ──────────────────────────────────────────────────────
    g.add_edge("setup",           "load_skills")
    g.add_edge("load_skills",     "plan")
    g.add_edge("code",            "test")
    g.add_edge("on_test_failure", "code")     # loop back after failure
    g.add_edge("commit",          "cleanup")
    g.add_edge("failure",         "cleanup")
    g.add_edge("cleanup",         END)

    # ── Conditional edges ─────────────────────────────────────────────────
    g.add_conditional_edges(
        "plan",
        route_after_plan,
        {"code": "code", "failure": "failure"},
    )
    g.add_conditional_edges(
        "test",
        route_after_test,
        {
            "commit":          "commit",
            "on_test_failure": "on_test_failure",
            "failure":         "failure",
        },
    )

    return g.compile()


# Module-level compiled graph — import this from task_engine.py
graph = build_graph()
