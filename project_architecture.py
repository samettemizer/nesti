"""Read-only, secret-pruned source evidence shared by CLI, pipeline and MCP."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import yaml

logger = logging.getLogger(__name__)

STACK_SCAN_PRUNE = frozenset({
    ".git", "node_modules", "vendor", "dist", "build", ".next", "out",
    "coverage", "playwright-report", "test-results", ".nuxt", ".output",
    ".idea", ".cache", "__pycache__", ".venv", "venv", "logs",
})
_SOURCE_SUFFIXES = {".php", ".vue", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".jsx", ".tsx", ".css", ".scss", ".sass", ".less", ".html", ".txt"}
_CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".xml", ".toml"}
_MANIFESTS = {"composer.json", "composer.lock", "package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock"}
_SECRET_NAME = re.compile(r"(?:^|[._-])(?:credentials?|secrets?|private[-_]?key|id_rsa|id_ed25519)(?:[._-]|$)", re.I)
_MAX_FILE_BYTES = 4 * 1024 * 1024
_RULE_METADATA_BYTES = 16 * 1024


def _kind(path: str) -> str | None:
    parts = PurePosixPath(path).parts
    name = parts[-1]
    if (any(part.startswith(".env") or _SECRET_NAME.search(part) for part in parts)
            or name in {".npmrc", ".pypirc", ".netrc", "auth.json"}
            or PurePosixPath(name).suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}):
        return None
    if "storage" in parts or any(parts[index:index + 2] == ("bootstrap", "cache") for index in range(len(parts) - 1)):
        return None
    for index, part in enumerate(parts[:-1]):
        if part in {".omp", ".ai", ".claude"}:
            if len(parts) != index + 3 or parts[index + 1] != "rules" or PurePosixPath(name).suffix not in {".md", ".mdc"}:
                return None
            if part == ".omp" and name.startswith("nesti-boost-"):
                return None
            return "rule"
    if name in _MANIFESTS:
        return "manifest"
    if PurePosixPath(name).suffix in _SOURCE_SUFFIXES or name == "artisan":
        return "source"
    if PurePosixPath(name).suffix in _CONFIG_SUFFIXES or name in {".prettierrc", ".editorconfig", ".eslintrc"}:
        return "config"
    return None


def _eligible_paths(root: Path):
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = sorted(name for name in names if name not in STACK_SCAN_PRUNE
                          and name != "storage"
                          and not (Path(directory) / name).is_symlink()
                          and (Path(directory).name, name) not in {
                              ("bootstrap", "cache"), (".omp", "agents"), (".ai", "nesti-boost-skills")})
        for name in sorted(files):
            file = Path(directory) / name
            path = file.relative_to(root).as_posix()
            kind = _kind(path)
            if kind and not file.is_symlink() and file.is_file():
                yield path, file, kind

def _read_bytes(root: Path, path: str, limit: int = _MAX_FILE_BYTES) -> bytes:
    """Read a bounded regular file without following a swapped symlink component."""
    parts = PurePosixPath(path).parts
    if not root.is_absolute() or not parts or PurePosixPath(path).is_absolute() or ".." in parts:
        raise ValueError("Source path must be relative and remain inside the absolute application root")
    descriptor = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in (*root.parts[1:], *parts[:-1]):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        with os.fdopen(file_descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("Source is not a regular file")
            data = source.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Source exceeds the complete-file byte limit")
            return data
    finally:
        os.close(descriptor)



def inventory_listing(directory: Path) -> list[str]:
    """List only eligible readable text files, pruning dependencies and symlinks."""
    return list(collect_inventory(str(directory))["files"])


def _json_file(files: dict, path: str, warnings: list[str]) -> dict:
    item = files.get(path)
    if not item:
        return {}
    try:
        value = json.loads(item["content"])
        if isinstance(value, dict):
            return value
    except (ValueError, TypeError):
        pass
    warnings.append(f"Cannot parse object metadata: {path}")
    return {}


def collect_inventory(repo_path: str, *, application_root: str = "") -> dict:
    """Collect safe text and backend PSR-4 mappings in inventory-root coordinates."""
    root = Path(repo_path)
    if not root.is_dir() or root.is_symlink() or root.absolute() != root.resolve():
        raise ValueError("Inventory root must be an existing non-symlink absolute directory")
    application = PurePosixPath(application_root)
    if application.is_absolute() or ".." in application.parts or "\\" in application_root:
        raise ValueError("Application root must remain relative to the inventory root")
    files: dict[str, dict] = {}
    warnings: list[str] = []
    for path, file, kind in _eligible_paths(root):
        try:
            data = _read_bytes(root, path)
            if b"\x00" in data:
                warnings.append(f"Omitted binary file: {path}")
                continue
            content = data.decode("utf-8")
            if re.search(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----|https?://[^\s/\"'<>]+:[^\s/\"'<>]+@", content):
                warnings.append(f"Omitted credential-bearing file: {path}")
                continue
            if any(ord(char) < 32 and char not in "\t\n\r\f" for char in content):
                warnings.append(f"Omitted non-text file: {path}")
                continue
            files[path] = {"content": content, "hash": hashlib.sha256(data).hexdigest(), "kind": kind}
        except (OSError, UnicodeError, ValueError):
            warnings.append(f"Omitted unsafe, oversized or unreadable text file: {path}")
    files = dict(sorted(files.items()))
    composer = _json_file(files, (application / "composer.json").as_posix(), warnings)
    mappings: list[dict] = []
    unresolved: list[str] = []
    for section in ("autoload", "autoload-dev"):
        autoload = composer.get(section, {})
        psr4 = autoload.get("psr-4", {}) if isinstance(autoload, dict) else {}
        if not isinstance(psr4, dict):
            unresolved.append(f"Invalid Composer {section}.psr-4 metadata")
            continue
        for namespace, locations in psr4.items():
            for location in locations if isinstance(locations, list) else [locations]:
                valid = (isinstance(namespace, str) and isinstance(location, str)
                         and not Path(location).is_absolute() and "\\" not in location
                         and ".." not in PurePosixPath(location).parts)
                normalized = (application / location).as_posix().rstrip("/") if valid else str(location)
                target = root / normalized if valid else root
                resolved = bool(valid and target.is_dir() and target.resolve().is_relative_to(root)
                                and target.absolute() == target.resolve()
                                and not any(part in STACK_SCAN_PRUNE for part in PurePosixPath(normalized).parts))
                mappings.append({"namespace": str(namespace), "path": normalized, "dev": section == "autoload-dev", "resolved": resolved})
                if not resolved:
                    unresolved.append(f"Unresolved Composer PSR-4 mapping {namespace}: {normalized}")
    mappings.sort(key=lambda item: (-len(item["namespace"]), item["namespace"], item["path"]))
    manifest = [(path, item["hash"]) for path, item in files.items()]
    return {"files": files, "fingerprint": hashlib.sha256(json.dumps(manifest, separators=(",", ":")).encode()).hexdigest(),
            "psr4": mappings, "unresolved": sorted(unresolved), "warnings": sorted(warnings)}


def _safe_json(path: Path) -> dict:
    if path.is_symlink() or path.absolute() != path.resolve() or not path.is_file():
        return {}
    try:
        if path.stat().st_size > 16 * 1024 * 1024:
            return {}
        value = json.loads(_read_bytes(path.parent, path.name, 16 * 1024 * 1024))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def _boost_receipt(namespace: str) -> dict:
    if not isinstance(namespace, str) or not re.fullmatch(r"[a-f0-9]{64}", namespace):
        return {}
    state = Path(os.getenv("NESTI_STATE_DIR", "/var/lib/nesti")) / "projects" / namespace
    return _safe_json(state / "boost-receipt.json")


def _generation_complete(receipt: dict, manifest: dict) -> bool:
    identity = receipt.get("snapshot_identity")
    return (receipt.get("schema_version") == 1 and receipt.get("status") == "completed"
            and manifest.get("schema_version") == 1 and manifest.get("status") == "completed"
            and isinstance(identity, str) and re.fullmatch(r"[a-f0-9]{64}", identity) is not None
            and manifest.get("snapshot_identity") == identity
            and manifest.get("source_fingerprint") == receipt.get("source_fingerprint"))


def _evidence_valid(evidence: object, files: dict) -> bool:
    if not isinstance(evidence, list) or not evidence:
        return False
    for cite in evidence:
        if not isinstance(cite, dict):
            return False
        path = cite.get("path")
        file = files.get(path) if isinstance(path, str) else None
        start, end = cite.get("start_line"), cite.get("end_line")
        if not file or cite.get("hash") != file["hash"] or type(start) is not int or type(end) is not int:
            return False
        lines = file["content"].splitlines()
        if not 1 <= start <= end <= len(lines) or cite.get("quote") != "\n".join(lines[start - 1:end]):
            return False
    return True


def _convention_valid(convention: object, files: dict) -> bool:
    return (isinstance(convention, dict)
            and _evidence_valid(convention.get("evidence"), files)
            and len({cite["path"] for cite in convention["evidence"]}) >= 3)


def _source_metadata(root: Path, fallback: dict) -> dict:
    from git import Repo
    try:
        repo = Repo(root, search_parent_directories=True)
        return {"head": repo.head.commit.hexsha if repo.head.is_valid() else None,
                "branch": None if repo.head.is_detached else repo.active_branch.name,
                "dirty": repo.is_dirty(untracked_files=True)}
    except Exception:
        return {key: fallback.get(key) for key in ("head", "branch", "dirty")}


def _node_id(kind: str, path: str) -> str:
    return hashlib.sha256(f"{kind}:{path}".encode()).hexdigest()[:24]


def _frontend_evidence(files: dict) -> tuple[list[dict], list[str]]:
    patterns = {
        "entry_mount": r"\bcreateApp\s*\(|\.mount\s*\(",
        "plugin_theme": r"\.use\s*\(|\b(?:PrimeVue|Aura|theme|preset)\b",
        "router": r"\b(?:createRouter|createWebHistory|RouterView|routes)\b",
        "store": r"\b(?:defineStore|createPinia|createStore)\b",
        "api_client": r"\b(?:axios|fetch)\s*[.(]",
        "alias": r"\b(?:alias|paths|baseUrl)\b",
        "root_component": r"\bimport\s+.+?from\s*['\"][^'\"]+\.vue['\"]",
        "blade_entry": r"@vite\s*\(|<[^>]+\bid=['\"]app['\"]",
        "component_registration": r"\.component\s*\(",
        "composable": r"\b(?:export\s+)?(?:function|const)\s+use[A-Z]\w*",
        "test": r"\b(?:describe|it|test)\s*\(",
    }
    evidence, unresolved = [], []
    for path, file in files.items():
        if (file["kind"] not in {"source", "config"}
                or (path.endswith(".php") and not path.endswith(".blade.php"))):
            continue
        for number, line in enumerate(file["content"].splitlines(), 1):
            for kind, pattern in patterns.items():
                if re.search(pattern, line):
                    evidence.append({"kind": kind, "path": path, "start_line": number, "end_line": number,
                                     "quote": line, "hash": file["hash"]})
            if re.search(r"\.(?:use|component)\s*\(\s*(?:\.\.\.|\w+\s*\[)|\.(?:component|mount)\s*\(\s*[^'\"\s]|import\s*\(\s*[^'\"\s]", line):
                unresolved.append(f"Dynamic frontend registration/import: {path}:{number}")
    return evidence, unresolved


def collect_architecture(repo_path: str, project: dict) -> dict:
    """Return a current structural snapshot; stale inferred claims never survive refresh."""
    root = Path(repo_path)
    project_root = Path(project.get("project_root", project.get("root", repo_path)))
    backend = Path(project.get("root", repo_path)).relative_to(project_root)
    if root == Path(project.get("root", repo_path)):
        root = project_root
    inventory = collect_inventory(str(root), application_root=backend.as_posix())
    files = inventory["files"]
    warnings = list(inventory["warnings"])
    unresolved = list(inventory["unresolved"])
    frontend = backend
    if project.get("frontend_root"):
        frontend = (Path(project["git_root"]) / project["frontend_root"]).relative_to(project_root)
    composer = _json_file(files, (backend / "composer.json").as_posix(), warnings)
    composer_lock = _json_file(files, (backend / "composer.lock").as_posix(), warnings)
    package = _json_file(files, (frontend / "package.json").as_posix(), warnings)
    npm_lock = _json_file(files, (frontend / "package-lock.json").as_posix(), warnings)
    dependencies = {}
    for data in (composer, package):
        for section in ("require", "require-dev", "dependencies", "devDependencies"):
            if isinstance(data.get(section), dict):
                dependencies.update(data[section])
    for section in ("packages", "packages-dev"):
        for item in composer_lock.get(section, []) if isinstance(composer_lock.get(section), list) else []:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                dependencies[item.get("name")] = item.get("version")
    for key, item in npm_lock.get("packages", {}).items() if isinstance(npm_lock.get("packages"), dict) else []:
        if key.startswith("node_modules/") and isinstance(item, dict):
            dependencies[key.removeprefix("node_modules/")] = item.get("version")
    directories = {""}
    for path in files:
        directories.update("/".join(PurePosixPath(path).parts[:index]) for index in range(1, len(PurePosixPath(path).parts)))
    nodes = [{"id": _node_id("directory", path), "kind": "directory", "label": path or ".", "paths": [path]}
             for path in sorted(directories)]
    edges = []
    for path in sorted(directories - {""}):
        parent = str(PurePosixPath(path).parent)
        edges.append({"from": _node_id("directory", "" if parent == "." else parent),
                      "to": _node_id("directory", path), "kind": "contains", "evidence": []})
    conventions = []
    receipt = _boost_receipt(project.get("namespace", ""))
    manifest_root = root
    configured_root = os.getenv("NESTI_PROJECT_PATH", "").strip()
    if configured_root and configured_root != str(root):
        from project_context import project_namespace
        try:
            if project.get("namespace") == project_namespace():
                manifest_root = Path(configured_root)
        except ValueError:
            pass
    manifest = _safe_json(manifest_root / ".omp" / "nesti-boost.json")
    published = _generation_complete(receipt, manifest)
    stale = bool(receipt) and (not published or receipt.get("source_fingerprint") != inventory["fingerprint"])
    if not published:
        warnings.append("Boost semantic context unavailable or unpublished; this is a structural view, not a complete call graph")
    elif stale:
        warnings.append("Boost semantic context stale: source fingerprint changed; inferred claims omitted")
    else:
        cached_conventions = receipt.get("conventions", [])
        cached_edges = receipt.get("edges", [])
        if not isinstance(cached_conventions, list) or not isinstance(cached_edges, list):
            stale = True
        for convention in cached_conventions if isinstance(cached_conventions, list) else []:
            if _convention_valid(convention, files):
                conventions.append({**convention, "inferred": True})
            else:
                stale = True
        ids = {node["id"] for node in nodes}
        for edge in cached_edges if isinstance(cached_edges, list) else []:
            if (isinstance(edge, dict) and isinstance(edge.get("from"), str)
                    and isinstance(edge.get("to"), str) and edge["from"] in ids and edge["to"] in ids
                    and _evidence_valid(edge.get("evidence"), files)):
                edges.append({**edge, "kind": "inferred"})
            else:
                stale = True
        if stale:
            warnings.append("Some cached semantic evidence is stale or invalid and was omitted")
    frontend, dynamic = _frontend_evidence(files)
    unresolved.extend(dynamic)
    app = "" if project.get("project_root") else project.get("application_root", "")
    return {
        "schema_version": 1,
        "project": {key: project.get(key) for key in ("id", "namespace", "path", "target_branch", "application_root", "root", "git_root", "project_root", "frontend_root")},
        "source": {**_source_metadata(root, project.get("source", {})), "fingerprint": inventory["fingerprint"]},
        "stack": {name: dependencies.get(package) if isinstance(dependencies.get(package), str) else None
                  for name, package in (("laravel", "laravel/framework"), ("vue", "vue"), ("primevue", "primevue"))},
        "directories": sorted("/".join(filter(None, (app, path))) for path in directories),
        "nodes": nodes, "edges": sorted(edges, key=lambda edge: (edge["from"], edge["to"], edge["kind"])),
        "conventions": conventions, "psr4": inventory["psr4"], "frontend": frontend,
        "files": [{"path": path, "kind": item["kind"], "hash": item["hash"]} for path, item in files.items()],
        "semantic_stale": stale, "unresolved": sorted(set(unresolved)), "warnings": sorted(set(warnings)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _matches(glob: str, path: str) -> bool:
    brace = re.search(r"\{([^{}]+)\}", glob)
    if brace:
        return any(_matches(glob[:brace.start()] + choice + glob[brace.end():], path)
                   for choice in brace[1].split(","))
    parts, target = glob.split("/"), path.removeprefix("./").split("/")

    def match(pattern: list[str], names: list[str]) -> bool:
        if not pattern:
            return not names
        if pattern[0] == "**":
            return match(pattern[1:], names) or bool(names and match(pattern, names[1:]))
        return bool(names and fnmatch.fnmatchcase(names[0], pattern[0]) and match(pattern[1:], names[1:]))

    return match(parts, target)


def load_project_rules(repo_path: str, task_text: str = "", paths: list[str] | None = None,
                       *, evidence_repo_path: str | None = None) -> list[dict]:
    """Load exact OMP bodies; generated rules require completed, current receipt evidence."""
    root = Path(repo_path)
    if not root.is_dir() or root.absolute() != root.resolve():
        raise ValueError("Rules root must be an existing non-symlink absolute directory")
    directory = root / ".omp" / "rules"
    if not directory.is_dir() or directory.absolute() != directory.resolve():
        return []
    manifest = _safe_json(root / ".omp" / "nesti-boost.json")
    inventory = None
    receipt = {}
    rules = []
    for file in sorted(directory.iterdir()):
        if file.is_symlink() or not file.is_file() or file.suffix not in {".md", ".mdc"}:
            continue
        path = file.relative_to(root).as_posix()
        try:
            if file.stat().st_size > _MAX_FILE_BYTES:
                raise ValueError("oversized rule")
            raw = _read_bytes(directory, file.name)
            text = raw.decode("utf-8")
            lines = text.splitlines(keepends=True)
            if not lines or lines[0].strip() != "---":
                raise ValueError("missing YAML frontmatter")
            closing = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
            if closing is None:
                raise ValueError("unclosed YAML frontmatter")
            metadata_text = "".join(lines[1:closing])
            if len(metadata_text.encode()) > _RULE_METADATA_BYTES:
                raise ValueError("oversized YAML metadata")
            metadata = yaml.safe_load(metadata_text)
            if not isinstance(metadata, dict):
                raise ValueError("metadata must be an object")
            for key in ("enabled", "alwaysApply"):
                if key in metadata and type(metadata[key]) is not bool:
                    raise ValueError(f"{key} must be boolean")
            if metadata.get("enabled", True) is False:
                continue
            description = metadata.get("description", "")
            globs = metadata.get("globs", [])
            if isinstance(globs, str):
                globs = [glob.strip() for glob in re.split(r",(?![^{}]*\})", globs) if glob.strip()]
            if not isinstance(description, str) or not description.strip():
                raise ValueError("description must be nonempty text")
            if not isinstance(globs, list) or any(not isinstance(glob, str) or not glob or glob.startswith("/") or "\\" in glob or ".." in PurePosixPath(glob).parts for glob in globs):
                raise ValueError("globs must be relative glob strings")
            generated = file.name.startswith("nesti-boost-")
            digest = hashlib.sha256(raw).hexdigest()
            selected = bool(metadata.get("alwaysApply", False) or any(_matches(glob, item) for glob in globs for item in (paths or [])))
            words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", description.lower()))
            selected = selected or bool(words.intersection(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", task_text.lower())))
            omission = ""
            if generated:
                if inventory is None:
                    from project_context import project_namespace
                    inventory = collect_inventory(evidence_repo_path or repo_path)
                    receipt = _boost_receipt(project_namespace())
                owned = manifest.get("generated_rules", {})
                conventions = receipt.get("conventions", [])
                linked = [item for item in conventions
                          if isinstance(item, dict) and item.get("generated_rule") == path] if isinstance(conventions, list) else []
                if (not _generation_complete(receipt, manifest)
                        or not isinstance(owned, dict) or owned.get(path) != digest
                        or manifest.get("source_fingerprint") != inventory["fingerprint"]
                        or receipt.get("source_fingerprint") != inventory["fingerprint"]
                        or len(linked) != 1 or not _convention_valid(linked[0], inventory["files"])):
                    selected, omission = False, "Generated rule omitted: ownership or completed source evidence is stale or invalid"
            rules.append({"path": path, "description": description, "globs": globs,
                          "alwaysApply": metadata.get("alwaysApply", False), "enabled": True,
                          "body": "".join(lines[closing + 1:]), "hash": digest, "generated": generated,
                          "selected": selected, "omission": omission})
        except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError) as exc:
            rules.append({"path": path, "description": "Invalid rule metadata", "globs": [],
                          "selected": False, "body": "", "generated": file.name.startswith("nesti-boost-"),
                          "omission": f"Rule omitted: {type(exc).__name__}"})
    return rules


def format_project_context(snapshot: dict, rules: list[dict]) -> str:
    """Format bounded facts and complete selected rules with explicit authority/omissions."""
    lines = ["PROJECT ARCHITECTURE (observed source; not a complete call graph)",
             "Current source and human rules outrank inferred facts. Migration/security/test invariants remain mandatory.",
             json.dumps({
                 "project": {key: value for key, value in snapshot.get("project", {}).items()
                             if key not in {"root", "git_root", "project_root"}},
                 **{key: snapshot.get(key) for key in ("source", "stack", "psr4", "unresolved", "warnings")},
             }, ensure_ascii=False),
             "Inferred conventions: " + json.dumps([
                 {key: item.get(key) for key in ("dimension", "glob", "title", "note", "inferred")}
                 for item in snapshot.get("conventions", [])
             ], ensure_ascii=False),
             "Frontend evidence locations: " + json.dumps({
                 kind: sorted({item["path"] for item in snapshot.get("frontend", []) if item["kind"] == kind})
                 for kind in sorted({item["kind"] for item in snapshot.get("frontend", [])})
             }, ensure_ascii=False),
             "Directories: " + ", ".join(snapshot.get("directories", [])), "OMP RULE INDEX:"]
    used = 0
    bodies = []
    for rule in rules:
        lines.append(f"- {rule['path']}: {rule.get('description', '')}; globs={rule.get('globs', [])}")
        if rule.get("omission"):
            lines.append(f"  {rule['omission']}")
        elif rule.get("selected"):
            body = rule.get("body", "")
            if used + len(body) > 48000:
                lines.append(f"  Complete body omitted due to instruction budget: {rule['path']}")
            else:
                bodies.append(f"\nPROJECT RULE {rule['path']} ({'inferred' if rule.get('generated') else 'human authoritative'}):\n{body}")
                used += len(body)
    return "\n".join(lines + bodies)
