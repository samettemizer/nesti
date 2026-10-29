"""
``nesti /arch``: renders ``layout.json`` as one self-contained offline Plotly page
(plotly.js embedded, no CDN, no server) or prints the record as JSON.
"""

import json
import logging
import os
import sys
import webbrowser
from html import escape
from pathlib import Path
from string import Template

import project_layout
from project_layout import LayoutError, ensure_layout, project_root

logger = logging.getLogger(__name__)

_ROLE_COLORS = {
    "backend": "#e4572e", "frontend": "#41b883", "domain": "#7e57c2", "http": "#29b6f6",
    "data": "#ffa726", "routes": "#ef5350", "tests": "#9ccc65", "other": "#b0bec5",
}

_PAGE = Template("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>$title — Nesti architecture</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f5f6f8;color:#222}
header{background:#263238;color:#fff;padding:16px 24px}header h1{margin:0 0 4px;font-size:22px}
header p{margin:0;font-size:13px;opacity:.8}main{padding:16px 24px;display:grid;gap:16px}
.card{background:#fff;border-radius:8px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
h2{font-size:16px;margin:0 0 8px}table{border-collapse:collapse;width:100%;font-size:13px}
td,th{border-bottom:1px solid #eee;padding:4px 8px;text-align:left}code{background:#eef;padding:0 3px}
</style></head><body>
<header><h1>$title</h1><p>mode: $mode · resolved by: $resolved_by · scanned: $scanned_at</p></header>
<main>
<section class="card"><h2>Summary</h2>$summary</section>
<section class="cards">$cards</section>
<section class="card"><h2>Directory tree</h2>$figure</section>
$domains
<section class="card"><h2>Conventions (.omp/rules)</h2>$conventions</section>
<p><a href="layout.json">layout.json</a></p>
</main></body></html>
""")


def _figure(tree: dict) -> str:
    import plotly.graph_objects as go
    import plotly.io as pio

    ids, labels, parents, values, colors = [], [], [], [], []

    def walk(node: dict, parent: str) -> None:
        ids.append(node["path"])
        labels.append(node["name"])
        parents.append(parent)
        values.append(node["files"])
        colors.append(_ROLE_COLORS.get(node["role"], _ROLE_COLORS["other"]))
        for child in node["children"]:
            walk(child, node["path"])

    walk(tree, "")
    fig = go.Figure(go.Icicle(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
        marker=dict(colors=colors), hovertemplate="%{id}<br>%{value} files<extra></extra>",
    ))
    fig.update_layout(margin=dict(t=8, l=8, r=8, b=8), height=560)
    return pio.to_html(fig, include_plotlyjs=True, full_html=False,
                       config={"displayModeBar": False, "responsive": True})


def _card(title: str, rows: list[tuple[str, object]]) -> str:
    body = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f'<div class="card"><h2>{escape(title)}</h2><table>{body}</table></div>'


def _conventions(root: Path) -> str:
    items = []
    for rule in sorted((root / ".omp" / "rules").glob("*.md")):
        description = ""
        try:
            lines = rule.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        if lines and lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    if description.startswith('"'):
                        try:
                            description = json.loads(description)
                        except ValueError:
                            pass
        items.append(f"<li><code>{escape(rule.stem)}</code> — {escape(str(description))}</li>")
    return f"<ul>{''.join(items)}</ul>" if items else "<p>No .omp rules yet (run nesti /boost).</p>"


def render_page(record: dict, out: Path) -> Path:
    """Render *record* (a layout.json record with ``architecture``) into the HTML file *out*."""
    arch = record.get("architecture") or {}
    root = Path(record.get("project_path", "."))
    backend, frontend = arch.get("backend"), arch.get("frontend")
    cards = []
    if backend:
        cards.append(_card("Backend", [("path", backend["path"]), ("php", backend.get("php")),
                                       ("laravel/framework", backend.get("laravel")),
                                       ("style", backend.get("style"))]))
    if frontend:
        pk = frontend.get("packages") or {}
        rows = [("path", frontend["path"])] + [(n, pk[n]) for n in
                                               ("vue", "primevue", "vue-router", "pinia", "typescript") if n in pk]
        if frontend.get("integrated"):
            rows.append(("integrated", "resources/js"))
        cards.append(_card("Frontend", rows))
    cards.append(_card("Other", [("folders", ", ".join(arch.get("other_dirs") or []) or "—")]))
    domains = ""
    if backend and backend.get("domains"):
        rows = "".join(f"<tr><td>{escape(d['name'])}</td><td>{d['files']}</td>"
                       f"<td>{escape(', '.join(d['layers']))}</td></tr>" for d in backend["domains"])
        domains = ('<section class="card"><h2>Domains</h2><table><tr><th>name</th><th>files</th>'
                   f"<th>layers</th></tr>{rows}</table></section>")
    page = _PAGE.substitute(
        title=escape(root.name),
        mode=escape(str(record.get("mode", ""))),
        resolved_by=escape(str(record.get("resolved_by", ""))),
        scanned_at=escape(str(arch.get("scanned_at", ""))),
        summary="".join(f"<p>{escape(s)}</p>" for s in arch.get("summary") or []),
        cards="".join(cards),
        figure=_figure(arch["tree"]) if arch.get("tree") else "",
        domains=domains,
        conventions=_conventions(root),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def cli_arch(args: list[str]) -> int:
    """``nesti /arch [--json]``: resolve the layout, then render the page or print the record."""
    if args not in ([], ["--json"]):
        print("Usage: nesti /arch [--json]")
        return 2
    try:
        root = project_root()
        record = ensure_layout(root)
        if args:
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        page = render_page(record, project_layout.STATE_DIR / "architecture.html")
        project_layout._adopt(page, project_layout.STATE_DIR)
    except (LayoutError, RuntimeError) as exc:
        print(f"Architecture failed: {exc}", file=sys.stderr)
        return 1
    for sentence in record["architecture"]["summary"]:
        print(sentence)
    layout = record["layout"]
    print(f"Layout: backend={layout['backend']} frontend={layout['frontend']} "
          f"(resolved by {record['resolved_by']})")
    print(f"Architecture view: {page}")
    if not os.path.exists("/.dockerenv"):
        webbrowser.open(page.as_uri())
    return 0
