"""mcp_server/tools/issues.py – GitLab Issues tools exposed over MCP.

Each tool is a thin wrapper around the corresponding function in
``graph/tools.py``; the docstring becomes the tool description visible to
Claude, and the ``{"success": bool, ...}`` return contract passes through
unchanged.
"""

from mcp_server.server import app
from graph.tools import (
    tool_issue_create,
    tool_issue_get,
    tool_issue_handoff,
    tool_issue_list_pending,
    tool_issue_notes,
    tool_issue_resolve,
    tool_issue_set_status,
)


@app.tool()
def issue_get(issue_id: int) -> dict:
    """
    Fetch a single issue by its project-scoped iid.
    Returns id, subject, description, state, labels, and web_url.
    """
    return tool_issue_get(issue_id)


@app.tool()
def issue_list_pending() -> dict:
    """
    List the pending issues in the configured GitLab project, oldest first.
    Pending means the issue is open, carries the opt-in GITLAB_ISSUE_LABEL,
    carries neither the "<label>::in-progress" lock nor the "<label>::pause"
    hold, and no unresolved fixture-dependency record holds it.
    """
    return tool_issue_list_pending()


@app.tool()
def issue_set_status(issue_id: int, status: str, note: str = "") -> dict:
    """
    Move a GitLab issue through the intake lifecycle.
    status must be one of: "new", "in_progress", "closed", "paused"
    GitLab has no in-progress or paused state, so the mapping is by label:
    "in_progress" adds the "<label>::in-progress" lock label (only while the
    issue is pending), "closed" closes the issue, "new" removes the lock label
    to return the issue to the pending pool (refused for a paused or
    dependency-held issue), and "paused" adds the "<label>::pause" hold label
    (refused for a closed or opted-out issue).
    Optionally add a note to the issue.
    """
    return tool_issue_set_status(issue_id, status, note)


@app.tool()
def issue_create(title: str, description: str) -> dict:
    """
    Create one GitLab issue WITHOUT any label, so Nesti ignores it until it is
    handed off. Title and description must be non-blank.
    Returns id, web_url and labels (empty).
    """
    return tool_issue_create(title, description)


@app.tool()
def issue_resolve(issue_id: int, model: str) -> dict:
    """
    Close an open issue that does not carry the opt-in label, after posting
    exactly the comment "omp-developer / model: <model>". model is one
    non-blank line of at most 200 characters. When the comment cannot be
    posted the issue stays open and success is false. Refused for a closed
    issue or one already handed to Nesti.
    """
    return tool_issue_resolve(issue_id, model)


@app.tool()
def issue_handoff(issue_id: int, report: str) -> dict:
    """
    Transfer an open, unlabelled issue to Nesti: append
    "## Third attempt (OMP team, advised) — rejected" followed by the report to
    the description and add the opt-in GITLAB_ISSUE_LABEL, verified by
    read-back. Nesti owns the issue afterwards.
    """
    return tool_issue_handoff(issue_id, report)


@app.tool()
def issue_notes(issue_id: int) -> dict:
    """
    List the non-system notes of an issue, oldest first, as
    {id, author, created_at, body}.
    """
    return tool_issue_notes(issue_id)
