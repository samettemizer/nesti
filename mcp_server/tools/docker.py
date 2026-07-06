"""mcp_server/tools/docker.py – Docker sandbox test tool exposed over MCP.

Note: this module is named ``docker`` inside the ``mcp_server.tools`` package;
Python 3 absolute imports guarantee the underlying ``graph/tools.py`` still
resolves the top-level ``docker`` SDK package correctly.
"""

from mcp_server.server import app
from graph.tools import tool_docker_run_tests


@app.tool()
def docker_run_tests(workspace_path: str) -> dict:
    """
    Run PHPUnit tests inside the Docker sandbox against the code at workspace_path.
    Runs composer install first, then phpunit --testdox.
    Returns passed: bool and output: str.
    """
    return tool_docker_run_tests(workspace_path)
