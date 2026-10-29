"""mcp_server/tools/project.py – project layout tool exposed over MCP."""

from mcp_server.server import app
from graph.tools import tool_project_layout


@app.tool()
def project_layout() -> dict:
    """
    Return the orchestrator's layout.json record: the Laravel backend and Vue
    frontend folders of NESTI_PROJECT_PATH, the mode and the architecture scan.
    Fails when `nesti /arch` has not been run on the orchestrator.
    """
    return tool_project_layout()
