"""mcp_server/tools/memory.py – hierarchical vector memory tools exposed over MCP.

Thin wrappers over the ``tool_memory_*`` functions in graph/tools.py:
Shared Qdrant document memory plus project-scoped Redis solutions and episodes.
Results pass through unchanged. Read tools may initialize server-side indices;
an unavailable tier is not evidence of an empty history (see ``memory_status``).
"""

from mcp_server.server import app
from graph.tools import (
    tool_memory_find_similar,
    tool_memory_forget_episodes,
    tool_memory_recall_failures,
    tool_memory_remember_failure,
    tool_memory_remember_solution,
    tool_memory_search_docs,
    tool_memory_status,
)


@app.tool()
def memory_search_docs(text: str, stack: str = "", limit: int = 6) -> dict:
    """
    Semantic search over the vendored Laravel / PrimeVue corpus indexed in
    Qdrant. stack "php" narrows to Laravel docs, "vue" to PrimeVue docs; any
    other value searches both stacks, interleaved rank by rank. Returns
    result: [{doc_title, doc_url, doc_path, source, stack, heading, text,
    score, version, doc_hash, chunk_index}]; [] when the memory layer is unavailable.
    """
    return tool_memory_search_docs(text, stack=stack, limit=limit)


@app.tool()
def memory_find_similar_issues(text: str, limit: int = 2) -> dict:
    """
    Find this project's MR-opened precedents, not verified merged results.
    Returns result: [{issue_id, subject, plan, mr_url, stack, created_at, similarity}]
    most similar first; rows below NESTI_SOLUTION_MIN_SCORE are dropped.
    """
    return tool_memory_find_similar(text, limit=limit)


@app.tool()
def memory_remember_solution(
    issue_id: int, subject: str, description: str, plan: str, stack: str, mr_url: str
) -> dict:
    """
    Store the plan that produced an opened MR in this project's solution cache,
    without asserting merge status. Returns result: {stored: bool}
    plus reason when not stored.
    """
    return tool_memory_remember_solution(issue_id, subject, description, plan, stack, mr_url)


@app.tool()
def memory_remember_failure(issue_id: int, attempt: int, layer: str, output: str) -> dict:
    """
    Store one failed attempt of an issue (test layer name + its output) in
    episodic memory. Returns result: {stored: bool} plus reason when not stored.
    """
    return tool_memory_remember_failure(issue_id, attempt, layer, output)


@app.tool()
def memory_recall_failures(issue_id: int, text: str, attempt: int, limit: int = 2) -> dict:
    """
    Recall this project's older failed attempts similar to text. attempt is the
    attempt about to run; the attempt that just failed (attempt - 1) is
    excluded. Returns result: [{issue_id, attempt, layer, summary, created_at, similarity}].
    """
    return tool_memory_recall_failures(issue_id, text, attempt=attempt, limit=limit)


@app.tool()
def memory_forget_episodes(issue_id: int) -> dict:
    """
    Drop this project's episodic-memory rows for an issue. Returns {deleted: int}.
    """
    return tool_memory_forget_episodes(issue_id)


@app.tool()
def memory_status() -> dict:
    """
    Report both memory tiers. Returns result: {qdrant: {available, url,
    collection, points, model, dim, error}, redis: {available, url, namespace,
    solutions, episodes, engine}}. Counts are null, never guessed, when unreadable.
    """
    return tool_memory_status()
