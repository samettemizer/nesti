"""Transport, CLI and local viewer boundary regressions; never uses live issues."""

import asyncio
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout, redirect_stderr
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

import architecture_view
from architecture_view import _directory_tree, _handler, _page, _d2_source


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_untrusted_labels_are_text_not_html_or_d2_statements(self) -> None:
        label = '<script>alert(1)</script>"\nmalicious: {link: https://example.org}'
        snapshot = {
            "schema_version": 1,
            "project": {"path": label}, "source": {"fingerprint": "a" * 64},
            "nodes": [{"id": "x; injected", "kind": "directory", "label": label, "paths": ["app"]}],
            "edges": [], "directories": ["app/<script>"], "warnings": [label],
        }
        page = _page(snapshot)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        lines = _d2_source(snapshot).splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[1].split(": ", 1)[1]), label)
        with self.assertRaises(ValueError):
            _directory_tree(["../outside"])

    def test_http_only_serves_fixed_assets(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _handler({"/": ("text/html", b"safe")}))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(base) as response:
                self.assertEqual(response.read(), b"safe")
                self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            for path in ("/../.env", "/%2e%2e/.env", "/etc/passwd", "/?file=.env"):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_browser_can_load_assets_with_an_idle_preconnection(self) -> None:
        accepted, opened = threading.Event(), threading.Event()
        servers, failures = [], []
        handler = _handler({"/": ("text/html", b"page"), "/architecture.svg": ("image/svg+xml", b"diagram")})

        class Handler(handler):
            def handle(self) -> None:
                accepted.set()
                super().handle()

        server_type = architecture_view.ThreadingHTTPServer

        def make_server(address, handler):
            server = server_type(address, handler)
            servers.append(server)
            return server

        def open_browser(url):
            try:
                with socket.create_connection(servers[0].server_address, timeout=2):
                    self.assertTrue(accepted.wait(2))
                    for path, expected in (("", b"page"), ("architecture.svg", b"diagram")):
                        with urllib.request.urlopen(url + path, timeout=2) as response:
                            self.assertEqual(response.read(), expected)
            except Exception as exc:
                failures.append(exc)
            finally:
                opened.set()

        with (
            tempfile.TemporaryDirectory() as state,
            patch.dict(os.environ, {"NESTI_CONTAINER": "0", "NESTI_STATE_DIR": state}),
            patch.object(architecture_view, "inspect_project", return_value={"namespace": "a" * 64}),
            patch.object(architecture_view, "collect_architecture", return_value={}),
            patch.object(architecture_view, "render_architecture", return_value={}),
            patch.object(architecture_view, "_handler", return_value=Handler),
            patch.object(architecture_view, "ThreadingHTTPServer", side_effect=make_server),
            patch.object(architecture_view.webbrowser, "open", side_effect=open_browser),
            redirect_stdout(io.StringIO()),
        ):
            serving = threading.Thread(
                target=architecture_view.serve_architecture, args=(state,), kwargs={"port": 0}, daemon=True,
            )
            serving.start()
            try:
                self.assertTrue(opened.wait(8), "Browser launch did not finish")
                self.assertEqual(failures, [])
            finally:
                for server in servers:
                    server.shutdown()
                serving.join(timeout=3)
            self.assertFalse(serving.is_alive())

    def test_project_cli_invalid_root_fails_before_redis(self) -> None:
        from scripts import oauth

        for command in ("/boost", "/arch"):
            with (
                patch.dict(os.environ, {"NESTI_PROJECT_PATH": "/nonexistent-nesti-fixture"}),
                patch("dotenv.load_dotenv"),
                patch.object(sys, "argv", ["nesti", command]),
                patch.object(oauth, "TokenStore", side_effect=AssertionError("Redis must not be constructed")),
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errors,
                self.assertRaises(SystemExit) as exit_result,
            ):
                oauth.main()
            self.assertEqual(exit_result.exception.code, 1)
            self.assertIn("Project command failed", errors.getvalue())


class MCPTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_inventory_and_project_failure_are_json(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        with tempfile.TemporaryDirectory(prefix="nesti-mcp-test-") as directory:
            environment = {
                "PATH": os.environ.get("PATH", ""), "HOME": directory,
                "NESTI_MEMORY_ENABLED": "false", "NESTI_RERANKER_ENABLED": "false",
                "NESTI_PROJECT_PATH": directory + "/absent", "NESTI_STATE_DIR": directory + "/state",
                "GITLAB_URL": "https://gitlab.invalid", "GITLAB_PROJECT_PATH": "fixtures/project",
                "GITLAB_TOKEN": "test-only", "PYTHONPATH": str(Path(__file__).parent),
            }
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], env=environment, cwd=directory)
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                    for name in ("project_architecture", "issue_history", "issue_escalation_create", "issue_escalation_complete", "issue_escalation_handoff"):
                        self.assertIn(name, tools)
                        json.dumps(tools[name].inputSchema)
                    result = await session.call_tool("project_architecture", {})
                    payload = json.loads(next(item.text for item in result.content if item.type == "text"))
                    self.assertFalse(payload["success"])
                    self.assertIsInstance(payload["error"], str)
                    self.assertFalse(Path(directory, "state").exists())


if __name__ == "__main__":
    unittest.main()
