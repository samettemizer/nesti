"""mcp_server/tools/redmine.py – Redmine tools exposed over MCP.

Each tool is a thin wrapper around the corresponding function in
``graph/tools.py``; the docstring becomes the tool description visible to
Claude, and the ``{"success": bool, ...}`` return contract passes through
unchanged.
"""

from mcp_server.server import app
from graph.tools import (
    tool_redmine_get_issue,
    tool_redmine_list_pending,
    tool_redmine_set_status,
)


@app.tool()
def redmine_get_issue(issue_id: int) -> dict:
    """
    Fetch a single Redmine issue by its ID.
    Returns all fields: id, subject, description, status, assignee.
    """
    return tool_redmine_get_issue(issue_id)


@app.tool()
def redmine_list_pending() -> dict:
    """
    List all pending (status=New) issues in the configured Redmine project.
    Returns a list sorted by ID ascending.
    """
    return tool_redmine_list_pending()


@app.tool()
def redmine_set_status(issue_id: int, status: str, note: str = "") -> dict:
    """
    Update a Redmine issue status.
    status must be one of: "new", "in_progress", "closed"
    Optionally add a comment to the issue.
    """
    return tool_redmine_set_status(issue_id, status, note)
