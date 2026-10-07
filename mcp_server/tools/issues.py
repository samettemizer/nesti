"""mcp_server/tools/issues.py – GitLab Issues tools exposed over MCP.

Each tool is a thin wrapper around the corresponding function in
``graph/tools.py``; the docstring becomes the tool description visible to
Claude, and the ``{"success": bool, ...}`` return contract passes through
unchanged.
"""

from mcp_server.server import app
from graph.tools import (
    tool_issue_get,
    tool_issue_list_pending,
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
