"""mcp_server/tools/gitlab.py – GitLab tools exposed over MCP.

Thin wrappers around the GitLab functions in ``graph/tools.py``.  All git
state is re-opened from ``repo_path`` inside the underlying tools, so every
call here works with plain string/int arguments only.
"""

from mcp_server.server import app
from graph.tools import (
    tool_gitlab_clone,
    tool_gitlab_create_branch,
    tool_gitlab_commit_and_push,
    tool_gitlab_open_mr,
)


@app.tool()
def gitlab_clone(target_path: str) -> dict:
    """Clone the configured GitLab repository into target_path."""
    return tool_gitlab_clone(target_path)


@app.tool()
def gitlab_create_branch(repo_path: str, issue_id: int, subject: str) -> dict:
    """
    Create and checkout a feature branch named feature/issue-{issue_id}-{slug}.
    Returns the branch_name created.
    """
    return tool_gitlab_create_branch(repo_path, issue_id, subject)


@app.tool()
def gitlab_commit_and_push(repo_path: str, branch_name: str, message: str) -> dict:
    """Stage all modified files, commit with the given message, and push to origin."""
    return tool_gitlab_commit_and_push(repo_path, branch_name, message)


@app.tool()
def gitlab_open_merge_request(
    branch_name: str,
    issue_id: int,
    subject: str,
    description: str = "",
) -> dict:
    """
    Open a GitLab Merge Request from branch_name into the default branch.
    Returns the MR web_url on success.
    """
    return tool_gitlab_open_mr(branch_name, issue_id, subject, description)
