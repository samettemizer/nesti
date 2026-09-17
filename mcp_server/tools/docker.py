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
    tool_openapi_export,
    tool_laravel_bootstrap,
)


@app.tool()
def detect_stack(workspace_path: str, written_files: list[str] | None = None) -> dict:
    """
    Detect which test layers apply to the code at workspace_path.
    Returns stack ("php" | "vue" | "fullstack" | "unknown"), has_vue, has_php,
    run_phpunit, the list of .vue files found, and the Laravel / OpenAPI markers
    is_laravel, has_api_routes, and run_openapi.
    Pass written_files (the paths the coder just wrote) so run_openapi is True
    only when the change actually touched the /api surface; omitting written_files
    yields the conservative answer that assumes the surface was touched.
    Call this first to decide which of the run tools below to use.
    """
    return tool_detect_stack(workspace_path, written_files)


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


@app.tool()
def openapi_export(workspace_path: str) -> dict:
    """
    Export and verify the OpenAPI document for the Laravel app at workspace_path.
    Runs `php artisan scramble:export --path=openapi.json` plus
    `php artisan route:list --json` in the PHP sandbox and compares the two.
    Returns passed: bool, output: str, paths: list[str], and undocumented:
    list[str]. passed is False when any route under /api is missing from the
    exported document.
    """
    return tool_openapi_export(workspace_path)


@app.tool()
def laravel_bootstrap(repo_path: str) -> dict:
    """
    Ensure repo_path is a Laravel 13 + Scramble + PrimeVue application.
    Three outcomes: a greenfield directory (no artisan, no composer.json) is
    scaffolded (mode "scaffold"); an existing Laravel app (artisan present) is
    topped up with only the missing configs and Scramble wiring (mode "top-up");
    a non-Laravel PHP project (composer.json without artisan) is refused with
    success=False rather than scaffolded over.
    Returns created: bool, mode: str, reason: str, and output: str.
    """
    return tool_laravel_bootstrap(repo_path)
