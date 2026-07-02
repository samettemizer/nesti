"""
graph – LangGraph pipeline for the AI Developer orchestrator (Phase 2).

Modules:
    state    – IssueState TypedDict flowing through every node.
    tools    – MCP-compatible atomic tool functions (Phase 3 reuses these).
    nodes    – LangGraph node functions (partial state updates).
    edges    – conditional routing functions.
    builder  – graph assembly; exposes the compiled ``graph`` object.

This package intentionally has NO import side effects: importing ``graph``
alone constructs nothing.  Heavier singletons (LLMClient, ConversationStore)
are created only when ``graph.nodes`` / ``graph.builder`` are imported, which
happens after ``load_dotenv()`` in main.py — same lifecycle as Phase 1.
"""
