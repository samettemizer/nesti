"""Read-only architecture for the configured shared project; no LLM or filesystem writes."""

from graph.tools import tool_project_architecture
from mcp_server.server import app


@app.tool()
def project_architecture() -> dict:
    """Read verified project identity and current structural/evidence snapshot."""
    return tool_project_architecture()
