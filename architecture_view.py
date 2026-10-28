"""Pinned D2 rendering and a fixed-asset, local-only project architecture view.

Run ``nesti /arch`` for the browser or ``nesti /arch --json`` for headless use.
Neither path runs project code, Boost inference, or a general filesystem server.
The base Compose service publishes port 8787 on host loopback. Keep the command
running while viewing; inside a container, open its printed URL on the Docker host.
"""

import html
import json
import logging
import os
import subprocess
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath

from project_architecture import collect_architecture
from project_context import inspect_project

logger = logging.getLogger(__name__)
_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"


def _directory_tree(paths: list[str]) -> str:
    tree: dict = {}
    for path in sorted(set(paths)):
        if path == "":
            continue
        parts = PurePosixPath(path).parts
        if not parts or path.startswith("/") or any(p in (".", "..") for p in parts):
            raise ValueError("Architecture paths must be relative and cannot traverse")
        branch = tree
        for part in parts:
            branch = branch.setdefault(part, {})

    def render(branch: dict) -> str:
        return "<ul>" + "".join(
            "<li><details><summary>" + html.escape(name) + "</summary>" + render(children) + "</details></li>"
            if children else "<li>" + html.escape(name) + "</li>"
            for name, children in sorted(branch.items())
        ) + "</ul>"

    return render(tree)


def _d2_source(snapshot: dict) -> str:
    # Only opaque generated identifiers and JSON-quoted labels enter D2 syntax.
    nodes = snapshot.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("Architecture nodes must be a list")
    selected = [n for n in nodes if n.get("kind") in ("module", "directory")]
    selected.sort(key=lambda n: (min((len(PurePosixPath(p).parts) for p in n.get("paths", [])), default=0), str(n.get("id", ""))))
    selected = selected[:40]
    ids = {str(node["id"]): f"n{index}" for index, node in enumerate(selected)}
    lines = ["direction: right"]
    for node in selected:
        label = str(node.get("label", node["id"]))
        lines.append(f"{ids[str(node['id'])]}: {json.dumps(label)}")
    for edge in snapshot.get("edges", []):
        source, target = ids.get(str(edge.get("from"))), ids.get(str(edge.get("to")))
        if source and target:
            kind = "contains" if edge.get("kind") == "contains" else "inferred"
            lines.append(f"{source} -> {target}: {json.dumps(kind)}")
    if not selected:
        lines.append('empty: "No eligible directory evidence"')
    return "\n".join(lines) + "\n"


def _page(snapshot: dict) -> str:
    project, source = snapshot["project"], snapshot["source"]
    escape = lambda value: html.escape(str(value))
    warnings = list(snapshot.get("warnings", [])) + list(snapshot.get("unresolved", []))
    if not snapshot.get("conventions") and not any("semantic" in str(w).lower() for w in warnings):
        warnings.append("No current Boost semantic evidence: this is a structural view, not a complete call graph.")
    rows = "".join(
        "<tr><td>" + escape(item.get("title", item.get("dimension", "Observed convention")))
        + "</td><td>" + escape(item.get("note", "")) + "</td><td><pre>"
        + escape(json.dumps(item.get("evidence", item.get("examples", [])), ensure_ascii=False, indent=2))
        + "</pre></td></tr>" for item in snapshot.get("conventions", [])
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Nesti project architecture</title><style>'
        'body{font:16px system-ui,sans-serif;margin:2rem;max-width:100rem;color:#20242a;background:#fff}'
        'summary{cursor:pointer}li{margin:.3rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}'
        'img{width:100%;max-height:40rem;border:1px solid #bbb}table{border-collapse:collapse;width:100%}'
        'td,th{border:1px solid #bbb;text-align:left;vertical-align:top;padding:.5rem}'
        '@media(prefers-color-scheme:dark){body{background:#181b20;color:#eee}a{color:#9dc7ff}}'
        '</style><h1>' + escape(project.get("path", "Project")) + '</h1><p>HEAD: <code>'
        + escape(source.get("head", "unknown")) + '</code> · branch: '
        + escape(source.get("branch") or "detached") + ' · dirty: ' + escape(source.get("dirty", False))
        + '</p><p>Fingerprint: <code>' + escape(source.get("fingerprint", "unknown"))
        + '</code></p><p><a href="/architecture.json" download="architecture.json">Download JSON</a></p>'
        + '<h2>Warnings and unresolved evidence</h2><ul>'
        + ''.join('<li>' + escape(w) + '</li>' for w in warnings) + '</ul>'
        + '<h2>Module overview</h2><p>Up to 40 directory/module nodes; the full directory view is below. '
        'Inferred relationships are not a complete call graph.</p>'
        '<img src="/architecture.svg" alt="Architecture module diagram"><h2>Directories</h2>'
        + _directory_tree(snapshot.get("directories", []))
        + '<h2>Inferred conventions and evidence</h2><table><thead><tr><th>Convention</th><th>Observation</th>'
        '<th>Source evidence</th></tr></thead><tbody>' + rows + '</tbody></table></html>'
    )


def render_architecture(snapshot: dict, output_dir: str) -> dict:
    """Render fixed HTML/SVG/JSON assets, failing explicitly when D2 cannot render."""
    if snapshot.get("schema_version") != 1:
        raise ValueError("Unsupported architecture snapshot schema")
    d2, page = _d2_source(snapshot), _page(snapshot)
    directory = Path(output_dir)
    if directory.absolute() != directory.resolve():
        raise ValueError("Refusing symlink architecture output directory")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="render-", dir=directory) as scratch:
        source, rendered = Path(scratch) / "architecture.d2", Path(scratch) / "architecture.svg"
        source.write_text(d2, encoding="utf-8")
        try:
            result = subprocess.run(["d2", str(source), str(rendered)], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"D2 v0.9.0 is required to render /arch: {exc}") from exc
        if result.returncode:
            raise RuntimeError(f"D2 rendering failed: {result.stderr.strip()}")
        svg = rendered.read_bytes()
    assets = {
        "/": ("text/html; charset=utf-8", page.encode()),
        "/architecture.svg": ("image/svg+xml", svg),
        "/architecture.json": ("application/json; charset=utf-8", json.dumps(snapshot, ensure_ascii=False, indent=2).encode()),
    }
    for route, (_, body) in assets.items():
        target = directory / ("index.html" if route == "/" else route[1:])
        if target.is_symlink():
            raise ValueError(f"Refusing symlink output: {target}")
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as staged:
            staged.write(body)
            temporary = Path(staged.name)
        try:
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return assets


def _handler(assets: dict) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            asset = assets.get(self.path)
            if asset is None:
                self.send_error(404)
                return
            content_type, body = asset
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", _CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            logger.info(format, *args)

    return Handler


def serve_architecture(repo_path: str, *, port: int = 8787) -> None:
    """Serve only rendered assets until Ctrl-C; native mode binds loopback."""
    project = inspect_project(repo_path)
    snapshot = collect_architecture(repo_path, project)
    namespace = project["namespace"]
    if not isinstance(namespace, str) or len(namespace) != 64 or any(c not in "0123456789abcdef" for c in namespace):
        raise ValueError("A valid project namespace is required")
    output = Path(os.environ.get("NESTI_STATE_DIR", "/var/lib/nesti")) / "projects" / namespace / "architecture"
    assets = render_architecture(snapshot, str(output))
    container = os.environ.get("NESTI_CONTAINER") == "1"
    # Browsers preconnect idle sockets; one must not stall all asset requests.
    with ThreadingHTTPServer(("0.0.0.0" if container else "127.0.0.1", port), _handler(assets)) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(url, flush=True)
        if not container:
            # A browser launcher may wait for the page (or browser) to close.
            threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
