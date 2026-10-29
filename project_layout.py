"""
Project layout resolution, ``state/layout.json`` persistence and the
architecture scan behind ``nesti /arch``.

``NESTI_PROJECT_PATH`` names a project root holding one Laravel API folder and,
optionally, one separate Vue SPA folder. A root Laravel app is resolved
deterministically; anything else is resolved once by the active LLM provider
and persisted. Never imports ``graph.tools`` (which imports this module).
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_DIR = Path(__file__).resolve().parent / "state"
LAYOUT_FILE = STATE_DIR / "layout.json"

# The first twelve names copy graph.tools._STACK_SCAN_PRUNE (not imported: circular).
_PRUNE = {
    ".git", "node_modules", "vendor", "dist", "build", ".next", "out",
    "coverage", "playwright-report", "test-results", ".nuxt", ".output",
    "storage", ".idea", ".claude", ".omp", ".ai",
}

_LARAVEL_SKELETON = {"Http", "Models", "Providers"}
_LARAVEL_GENERATED = {
    "Console", "Exceptions", "Jobs", "Events", "Listeners", "Mail", "Notifications",
    "Policies", "Rules", "Observers", "Casts", "Enums", "Broadcasting", "View", "Scopes",
}
_DEFAULT_PSR4 = {"app/", "database/factories/", "database/seeders/", "tests/"}
_LISTING_CAP = 200
_TREE_DEPTH = 4

_LAYOUT_SYSTEM_PROMPT = (
    "You identify the folders of a web project. Nesti supports exactly one Laravel API "
    "backend folder and, optionally, one separate Vue single-page application folder. "
    "Answer with ONE JSON object and nothing else: "
    '{"backend": "<folder>", "frontend": "<folder>" or null, "reason": "<one sentence>"}. '
    "Use folder names exactly as listed. backend contains artisan and composer.json. "
    "frontend is a Vue SPA with its own package.json; use null when there is none. "
    "A frontend is never a folder inside the backend."
)


class LayoutError(ValueError):
    """The project layout is missing, invalid or could not be resolved."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _adopt(path: Path, ref: Path) -> None:
    """Give *path* the owner of *ref* when running as root (never recursive)."""
    if os.geteuid() == 0:
        st = ref.stat()
        os.chown(path, st.st_uid, st.st_gid)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Unreadable JSON %s: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _visible(root: Path) -> list[Path]:
    """Non-dot entries of *root*, sorted by name."""
    return sorted((p for p in root.iterdir() if not p.name.startswith(".")), key=lambda p: p.name)


def _has_plugin_vue(root: Path) -> bool:
    for name in ("vite.config.js", "vite.config.ts"):
        try:
            if "@vitejs/plugin-vue" in (root / name).read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            continue
    return False


def _packages(pkg: dict) -> dict:
    deps: dict = {}
    for key in ("dependencies", "devDependencies"):
        if isinstance(pkg.get(key), dict):
            deps.update(pkg[key])
    return deps


def _walk_files(path: Path) -> list[Path]:
    """Every file below *path*, pruning ``_PRUNE`` dirs; symlinked dirs not followed."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE]
        found.extend(Path(dirpath) / f for f in filenames)
    return found


def _subdirs(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted((p for p in path.iterdir() if p.is_dir() and not p.is_symlink()
                   and p.name not in _PRUNE), key=lambda p: p.name)


def _mode(layout: dict) -> str:
    backend, frontend = layout.get("backend"), layout.get("frontend")
    if backend is None and frontend is None:
        return "greenfield"
    if backend == "." and frontend == ".":
        return "integrated"
    if frontend is None:
        return "backend-only"
    return "separated"


# ---------------------------------------------------------------------------
# Layout resolution
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Return ``NESTI_PROJECT_PATH`` as a Path; raise LayoutError unless it is a real absolute dir."""
    raw = os.environ.get("NESTI_PROJECT_PATH", "").strip()
    if not raw:
        raise LayoutError("NESTI_PROJECT_PATH is not set")
    path = Path(raw)
    if not path.is_absolute():
        raise LayoutError(f"NESTI_PROJECT_PATH must be absolute: {raw}")
    if path.is_symlink():
        raise LayoutError(f"NESTI_PROJECT_PATH must not be a symlink: {raw}")
    if not path.is_dir():
        raise LayoutError(f"NESTI_PROJECT_PATH is not an existing directory: {raw}")
    return path


def _deterministic(root: Path) -> tuple[dict, str] | None:
    if (root / "artisan").is_file():
        if _has_plugin_vue(root):
            return {"backend": ".", "frontend": "."}, "root Laravel app with @vitejs/plugin-vue"
        return {"backend": ".", "frontend": None}, "root Laravel app"
    if not _visible(root):
        return {"backend": None, "frontend": None}, "empty project"
    return None


def deterministic_layout(root: Path) -> dict | None:
    """Layout of a root Laravel app or an empty root; ``None`` when the LLM must decide."""
    found = _deterministic(root)
    return found[0] if found else None


def _segment(root: Path, name: object, side: str) -> Path:
    if not isinstance(name, str) or not name or "/" in name or "\\" in name or name in (".", ".."):
        raise LayoutError(f"{side} must be a single folder name, got {name!r}")
    path = root / name
    if path.is_symlink() or not path.is_dir():
        raise LayoutError(f"{side} folder {name!r} is not a directory")
    return path


def validate_layout(root: Path, layout: dict) -> None:
    """Raise LayoutError(reason) unless *layout* describes *root*."""
    if not isinstance(layout, dict):
        raise LayoutError("layout must be an object")
    backend, frontend = layout.get("backend"), layout.get("frontend")
    if backend is None:
        if frontend is not None:
            raise LayoutError("a frontend without a backend is not supported")
        if _visible(root):
            raise LayoutError("greenfield layout but the project is not empty")
        return
    if backend == ".":
        if not (root / "artisan").is_file():
            raise LayoutError("backend '.' but the root has no artisan")
        expected = "." if _has_plugin_vue(root) else None
        if frontend != expected:
            raise LayoutError(f"a root Laravel app has frontend {expected!r}, not {frontend!r}")
        return
    back = _segment(root, backend, "backend")
    for name in ("artisan", "composer.json"):
        if not (back / name).is_file():
            raise LayoutError(f"backend folder {backend!r} has no {name}")
    if frontend is None:
        return
    if frontend == backend:
        raise LayoutError("frontend and backend must be different folders")
    front = _segment(root, frontend, "frontend")
    if (front / "artisan").exists():
        raise LayoutError(f"frontend folder {frontend!r} is a Laravel app")
    if not (front / "package.json").is_file():
        raise LayoutError(f"frontend folder {frontend!r} has no package.json")
    if "vue" not in _packages(_read_json(front / "package.json")):
        raise LayoutError(f"frontend folder {frontend!r} does not depend on vue")


def _listing(root: Path) -> str:
    lines = ["$ ls -A ."]
    lines += [p.name + ("/" if p.is_dir() else "") for p in sorted(root.iterdir(), key=lambda p: p.name)]
    for child in _visible(root):
        if not child.is_dir() or child.name in _PRUNE:
            continue
        names = [p.name + ("/" if p.is_dir() else "")
                 for p in sorted(child.iterdir(), key=lambda p: p.name) if p.name not in _PRUNE]
        lines += ["", f"$ ls -A {child.name}"] + names[:_LISTING_CAP]
    return "\n".join(lines)


def _parse_reply(root: Path, reply: str) -> tuple[dict, str]:
    text = re.sub(r"```[a-zA-Z]*", "", reply or "")
    start = text.find("{")
    if start < 0:
        raise LayoutError("no JSON object in the reply")
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError as exc:
        raise LayoutError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LayoutError("the reply is not a JSON object")
    layout = {"backend": data.get("backend"), "frontend": data.get("frontend")}
    if layout["backend"] is None:
        raise LayoutError("backend is missing")
    validate_layout(root, layout)
    return layout, str(data.get("reason") or "")


def _record(root: Path, layout: dict, resolved_by: str, reason: str) -> dict:
    return {
        "schema": 1, "project_path": str(root), "layout": layout, "mode": _mode(layout),
        "resolved_by": resolved_by, "reason": reason, "resolved_at": _now(),
    }


def resolve_layout(root: Path, llm) -> dict:
    """Resolve *root*'s layout (deterministically, else via *llm*), save and return the record."""
    found = _deterministic(root)
    if found:
        record = _record(root, found[0], f"deterministic: {found[1]}", found[1])
    else:
        user = _listing(root)
        reply = llm.generate_plan(_LAYOUT_SYSTEM_PROMPT, user)
        try:
            layout, reason = _parse_reply(root, reply)
        except LayoutError as exc:
            messages = [
                {"role": "user", "content": user},
                {"role": "assistant", "content": reply},
                {"role": "user", "content": f"Invalid: {exc}. Reply with the corrected JSON object only."},
            ]
            reply = llm.generate_plan(_LAYOUT_SYSTEM_PROMPT, user, messages=messages)
            try:
                layout, reason = _parse_reply(root, reply)
            except LayoutError as retry_exc:
                raise LayoutError(f"{retry_exc}; reply: {(reply or '')[:500]}") from retry_exc
        record = _record(root, layout, str(getattr(llm, "last_planner_label", "") or "llm"), reason)
    save_layout(record)
    logger.info("Project layout resolved: %s (%s)", record["layout"], record["resolved_by"])
    return record


def load_layout() -> dict | None:
    """Return the saved layout record, or None when absent or unreadable."""
    path = LAYOUT_FILE
    if not path.is_file():
        return None
    data = _read_json(path)
    return data or None


def save_layout(record: dict) -> None:
    """Atomically write *record* to ``layout.json``."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    target = LAYOUT_FILE
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    _adopt(target, STATE_DIR)


def ensure_layout(root: Path) -> dict:
    """Load and validate the saved record, else resolve it; refresh the architecture scan."""
    record = load_layout()
    valid = False
    if record and record.get("project_path") == str(root):
        try:
            validate_layout(root, record.get("layout"))
            valid = True
        except LayoutError as exc:
            logger.info("Saved layout is stale (%s); resolving again.", exc)
    if not valid:
        from llm_client import LLMClient
        record = resolve_layout(root, LLMClient())
    return refresh_architecture(record)


def refresh_architecture(record: dict) -> dict:
    """Rescan the architecture of *record*'s project, save and return the record."""
    record["architecture"] = scan_architecture(Path(record["project_path"]), record["layout"])
    save_layout(record)
    return record


def clone_layout(clone: Path) -> dict:
    """Layout of a pipeline clone: deterministic, else the saved layout validated against it."""
    layout = deterministic_layout(clone)
    if layout is not None:
        return layout
    record = load_layout()
    if not record:
        raise LayoutError("layout.json not found: run nesti /arch")
    layout = record.get("layout") or {}
    try:
        validate_layout(clone, layout)
    except LayoutError as exc:
        raise LayoutError(f"layout.json does not match the repository: {exc}; run nesti /arch") from exc
    return {"backend": layout.get("backend"), "frontend": layout.get("frontend")}


# ---------------------------------------------------------------------------
# Architecture scan
# ---------------------------------------------------------------------------

def _names(items: list[str]) -> str:
    return ", ".join(items[:8]) + (", …" if len(items) > 8 else "")


def _scan_backend(back: Path) -> dict:
    composer = _read_json(back / "composer.json")
    require = composer.get("require") if isinstance(composer.get("require"), dict) else {}
    dev = composer.get("require-dev") if isinstance(composer.get("require-dev"), dict) else {}
    psr4 = (composer.get("autoload") or {}).get("psr-4") or {}
    app_dirs = [p.name for p in _subdirs(back / "app")]
    custom_dirs = [d for d in app_dirs if d not in _LARAVEL_SKELETON | _LARAVEL_GENERATED]

    domain_root, domains = None, []
    candidates = sorted(custom_dirs, key=lambda d: -len(_subdirs(back / "app" / d)))
    if candidates:
        best = back / "app" / candidates[0]
        subs = _subdirs(best)
        with_php = [s for s in subs if any(f.suffix == ".php" for f in _walk_files(s))]
        if len(with_php) >= 2:
            domain_root = candidates[0]
            domains = [{"name": s.name, "files": len(_walk_files(s)),
                        "layers": [p.name for p in _subdirs(s)]} for s in subs]
    counts: dict[str, int] = {}
    for d in domains:
        for layer in d["layers"]:
            counts[layer] = counts.get(layer, 0) + 1
    common = sorted(l for l, n in counts.items() if domains and n * 2 >= len(domains))
    targets: list[str] = []
    for value in psr4.values() if isinstance(psr4, dict) else []:
        targets += value if isinstance(value, list) else [value]
    extra = [t for t in targets if isinstance(t, str) and t.rstrip("/") + "/" not in _DEFAULT_PSR4]
    style = "domain" if domain_root else "custom" if custom_dirs or extra else "default"
    return {
        "php": require.get("php"), "laravel": require.get("laravel/framework"),
        "packages": {**require, **dev}, "psr4": psr4, "app_dirs": app_dirs,
        "custom_dirs": custom_dirs, "domain_root": domain_root, "domains": domains,
        "common_layers": common,
        "custom_layers": [l for l in common if l not in _LARAVEL_SKELETON | _LARAVEL_GENERATED],
        "extra_psr4": extra, "style": style,
    }


def _role(rel: str, layout: dict, domain_path: str | None) -> str:
    if rel == layout.get("backend"):
        return "backend"
    if rel == layout.get("frontend"):
        return "frontend"
    if domain_path and (rel == domain_path or rel.startswith(domain_path + "/")):
        return "domain"
    name = rel.rsplit("/", 1)[-1]
    if name.startswith("Http"):
        return "http"
    if name.startswith("Models") or name.startswith("database"):
        return "data"
    if name == "routes":
        return "routes"
    if name.startswith("tests") or name.startswith("e2e"):
        return "tests"
    return "other"


def _tree(path: Path, rel: str, depth: int, layout: dict, domain_path: str | None) -> dict:
    children = []
    if depth > 0:
        children = [_tree(sub, f"{rel}/{sub.name}" if rel != "." else sub.name,
                          depth - 1, layout, domain_path) for sub in _subdirs(path)]
    return {"name": path.name, "path": rel, "files": len(_walk_files(path)),
            "role": _role(rel, layout, domain_path), "children": children}


def _summary(backend_dir: str | None, frontend_dir: str | None,
             backend: dict | None, frontend: dict | None) -> list[str]:
    if backend is None:
        return ["The project is empty; Nesti scaffolds a Laravel application with the first issue."]
    bp = "" if backend_dir == "." else f"{backend_dir}/"
    sentences = []
    if backend["style"] == "domain":
        names = [d["name"] for d in backend["domains"]]
        sentences.append(
            f"The backend uses a custom domain-oriented architecture: `{bp}app/{backend['domain_root']}/*` "
            f"splits the code into {len(names)} domains ({_names(names)})."
        )
        second = f"Each domain repeats the same layers ({_names(backend['common_layers'])})"
        if backend["custom_layers"]:
            second += f" and adds non-Laravel layers: {_names(backend['custom_layers'])}"
        second += "."
        others = [f"{bp}app/{d}" for d in backend["custom_dirs"] if d != backend["domain_root"]]
        if others:
            second += f" Other non-default folders: {_names(others)}."
        sentences.append(second)
    elif backend["style"] == "custom":
        text = "The backend keeps Laravel's default structure plus custom folders: "
        text += _names([f"`{bp}app/{d}`" for d in backend["custom_dirs"]]) or "none"
        if backend["extra_psr4"]:
            text += f"; extra PSR-4 roots: {_names(backend['extra_psr4'])}"
        sentences.append(text + ".")
    else:
        sentences.append("The backend follows Laravel's default application structure; "
                         "no custom domain or module layer was found.")
    if frontend and frontend.get("integrated"):
        sentences.append("The Vue frontend is integrated in the Laravel app (resources/js), "
                         "the layout of Nesti's own scaffold.")
    elif frontend:
        pk = frontend["packages"]
        parts = [f"vue {pk.get('vue', '?')}", f"primevue {pk.get('primevue', '?')}"]
        if frontend["typescript"]:
            parts.append("TypeScript")
        if "vue-router" in pk:
            parts.append("vue-router")
        if "pinia" in pk:
            parts.append("Pinia")
        sentences.append(f"The frontend is a separate Vue SPA in `{frontend_dir}/` ({', '.join(parts)}).")
    else:
        sentences.append("There is no frontend SPA.")
    return sentences


def scan_architecture(root: Path, layout: dict) -> dict:
    """Scan *root* under *layout*: backend/frontend facts, directory tree and summary sentences."""
    backend_dir, frontend_dir = layout.get("backend"), layout.get("frontend")
    backend = None
    if backend_dir is not None:
        backend = {"path": backend_dir, **_scan_backend(root / backend_dir)}
    frontend = None
    if frontend_dir == ".":
        frontend = {"path": ".", "integrated": True}
    elif frontend_dir:
        spa = root / frontend_dir
        frontend = {"path": frontend_dir, "packages": _packages(_read_json(spa / "package.json")),
                    "typescript": (spa / "tsconfig.json").is_file(),
                    "src_dirs": [p.name for p in _subdirs(spa / "src")]}
    managed = {backend_dir, frontend_dir}
    other_dirs = [p.name for p in _subdirs(root) if not p.name.startswith(".") and p.name not in managed]

    domain_path = None
    if backend and backend["domain_root"]:
        domain_path = f"app/{backend['domain_root']}" if backend_dir == "." \
            else f"{backend_dir}/app/{backend['domain_root']}"
    if backend_dir == ".":
        tree = _tree(root, ".", _TREE_DEPTH, layout, domain_path)
        tree["role"] = "backend"
    else:
        children = [_tree(root / d, d, _TREE_DEPTH, layout, domain_path)
                    for d in (backend_dir, frontend_dir) if d]
        children += [_tree(root / d, d, 1, layout, domain_path) for d in other_dirs]
        direct = sum(1 for p in root.iterdir() if p.is_file())
        tree = {"name": root.name, "path": ".", "files": direct + sum(c["files"] for c in children),
                "role": "other", "children": children}
    return {
        "backend": backend, "frontend": frontend, "other_dirs": other_dirs, "scanned_at": _now(),
        "tree": tree, "summary": _summary(backend_dir, frontend_dir, backend, frontend),
    }
