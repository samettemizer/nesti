"""mcp_server/tools/docker.py – sandbox test tools exposed over MCP.

One tool per test layer (PHPUnit, Vitest, Playwright) plus the stack detector
that says which layers apply to a workspace.  ``detect_stack`` lives here
rather than in a module of its own because it exists to answer exactly one
question: which sandbox image should run next.

Note: this module is named ``docker`` inside the ``mcp_server.tools`` package;
Python 3 absolute imports guarantee the underlying ``graph/tools.py`` still
resolves the top-level ``docker`` SDK package correctly.
"""

from mcp_server.server import app
from graph.tools import (
    tool_detect_stack,
    tool_docker_run_tests,
    tool_vitest_run_tests,
    tool_playwright_run_tests,
)


@app.tool()
def detect_stack(workspace_path: str) -> dict:
    """
    Detect which test layers apply to the code at workspace_path.
    Returns stack ("php" | "vue" | "fullstack" | "unknown"), has_vue, has_php,
    run_phpunit, and the list of .vue files found.
    Call this first to decide which of the run tools below to use.
    """
    return tool_detect_stack(workspace_path)


@app.tool()
def docker_run_phpunit(workspace_path: str) -> dict:
    """
    Run PHPUnit tests in the PHP sandbox against the code at workspace_path.
    Runs composer install first, then phpunit --testdox.
    Returns passed: bool and output: str.
    """
    return tool_docker_run_tests(workspace_path)


@app.tool()
def docker_run_vitest(workspace_path: str) -> dict:
    """
    Run Vitest component tests in the Node sandbox against workspace_path.
    Installs npm dependencies first, then runs vitest.
    Returns passed: bool and output: str.
    """
    return tool_vitest_run_tests(workspace_path)


@app.tool()
def docker_run_playwright(workspace_path: str) -> dict:
    """
    Run Playwright E2E tests against workspace_path in a headless Chromium
    sandbox. Installs dependencies, builds the app, and serves it via the
    webServer entry in playwright.config.js automatically.
    Returns passed: bool and output: str.
    """
    return tool_playwright_run_tests(workspace_path)
