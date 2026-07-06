"""
mcp_server/server.py – Nesti MCP Server.

Exposes Redmine, GitLab, Docker, and skill tools via the Model Context Protocol.
Compatible with Claude Code CLI, VS Code Claude extension, and Cursor.

Run directly:
    python -m mcp_server.server

Or via Docker (see docker-compose.yml nesti-mcp service).

Implementation notes
────────────────────
• ``FastMCP`` is the decorator-based server API of the official ``mcp`` SDK:
  it provides the ``@app.tool()`` registration used by the modules in
  ``mcp_server/tools/``.  Tool descriptions come from the docstrings and the
  input schemas are derived from the type hints — nothing else is needed.
• The tool modules import ``app`` from this module, so they MUST be imported
  *after* the ``app`` assignment below (import order is load-bearing).
• When executed as ``python -m mcp_server.server`` this file runs under the
  module name ``__main__`` while the tool modules register their tools on the
  canonical ``mcp_server.server`` module instance.  The ``__main__`` guard
  therefore delegates to the canonical instance so every registered tool is
  actually served.
"""

import asyncio

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP  # noqa: E402  (after load_dotenv)

app = FastMCP("nesti")

# Importing the tool modules runs their @app.tool() decorators, which
# registers every tool on ``app``.  Keep this below the ``app`` assignment.
from mcp_server.tools import redmine, gitlab, docker, skills  # noqa: E402,F401


async def main() -> None:
    """Serve the MCP app over stdio until the client disconnects."""
    await app.run_stdio_async()


if __name__ == "__main__":
    # Delegate to the canonical module instance – see module docstring.
    from mcp_server.server import main as _canonical_main

    asyncio.run(_canonical_main())
