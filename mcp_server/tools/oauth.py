"""mcp_server/tools/oauth.py – OAuth consumer-provider quota tool exposed over MCP.

Mirrors graph/tools.py's tool_quota_check() so an MCP client can check the
same '/provider login'-authenticated quotas the orchestrator's
node_on_layer_failure safety check reads, without shelling into the
container to run `nesti /usage`.
"""

from mcp_server.server import app
from graph.tools import tool_quota_check


@app.tool()
def quota_check() -> dict:
    """
    Report remaining usage/quota for every OAuth consumer provider
    authenticated via `nesti /provider login` (scripts/oauth.py).
    Returns result: {"<provider>": {"remaining": int|None, "limit": int|None,
    "reset_time": int|None, ...}, ...}. A provider never logged in is
    omitted. remaining/limit are None when the provider has no public
    quota-introspection API (reported honestly rather than guessed) — treat
    None as "unknown", never as "critically low".
    """
    return tool_quota_check()
