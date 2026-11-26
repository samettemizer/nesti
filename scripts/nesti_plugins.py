#!/usr/bin/env python3
"""Host-side ``nesti /plugin``: install, enable, list, disable, update, remove plugins and switch their settings.

Runs on the host through ``scripts/nesti`` with Python 3.6+ and the standard
library only; it never imports a Nesti container module and needs neither
Redis nor the orchestrator. Sources come from the operator's Git (host SSH /
credential helpers); service packages run through host Docker Compose.

Native manifests declare multiple ``settings`` with a ``key`` and optional
``choices`` or ``secret: true``. Plain skill packages expose one inferred ``args``
setting. Secret values are accepted only through ``-`` (hidden prompt or stdin).

Storage below the Nesti root:
  .private/plugins/packages/<name>/<sha>/      installed sources, read-only by contract
  .private/plugins/work/<name>/<sha>/          build artifacts of a service revision's prepare step
  .private/plugins/config/<name>/              bindings.json and the package's .env (never deleted)
  .private/plugins/secrets/<name>/<event>.key  event signing key copied from .env while enabled
  state/plugins/registry.json                  non-secret revision/activation records
  state/plugins/runtime/active.json            compiled skill bindings and event subscriptions

The sources directory is read-only by contract: a prepare step writes build artifacts to
NESTI_PLUGIN_WORK_DIR. ``active.json`` (atomic replace) is what the container reads:
  {"version": 1,
   "skills": [{"package", "revision" (full SHA), "ref", "skill", "path" (under CONTAINER_PACKAGES_DIR),
               "phases" (subset of plan/code), "arguments" ({str: str})}],
   "subscriptions": [{"package", "revision", "event", "url" (on the nesti-plugins network),
                      "secret_file" (under CONTAINER_SECRETS_DIR)}]}

A service's optional ``configure`` step runs at every enable, before Compose starts, with the
package's .env values, the NESTI_PLUGIN_* paths, NESTI_PROJECT_PATH (Nesti's .env) and
NESTI_PLUGIN_CONTEXT: a temporary JSON file, removed afterwards, holding the runtime context
  {"version": 1, "project_path", "skills": [{"package", "skill", "revision", "ref", "arguments",
                                            "phases", "text"}]}
with the enabled skill bindings of every other package in runtime order. Enable recreates the
services, so they always run on the configuration just generated; when that context changes
later, ``list`` and every mutating command report the service as stale until it is re-enabled.
"""

import argparse
import contextlib
import getpass
import hashlib
import json
import logging
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

try:
    import fcntl
except ImportError:  # Windows Python (Git Bash): byte-range locks instead
    fcntl = None
    import msvcrt

logger = logging.getLogger(__name__)

MANIFEST = "nesti-plugin.json"
SCHEMA_VERSION = 1
PLUGIN_API = 1
REGISTRY_VERSION = 1
RUNTIME_VERSION = 1
CONTEXT_VERSION = 1
NETWORK = "nesti-plugins"
PROBE_IMAGE = "nesti-orchestrator:latest"
CONTAINER_PACKAGES_DIR = "/orchestrator/plugins/packages"
CONTAINER_SECRETS_DIR = "/orchestrator/plugins/secrets"
EVENTS = ("github.pull_request.ready",)
PHASES = ("plan", "code")
PHASE_BINDING_CHAR_LIMIT = 8000
BINDINGS_MAX_BYTES = 16 * 1024
MAX_ARGUMENTS = 8
MAX_ARGUMENT_CHARS = 64
MAX_PREPARE_ARGS = 32
READY_TIMEOUT = 120
PROBE_TIMEOUT = 30
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
HEX_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
ARG_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SETTING_VALUE_RE = re.compile(r"[^\s'\"#$\\\x00-\x1f\x7f]{1,128}")  # fullmatch; '$' would interpolate in Compose
URL_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/%-]*$")
_MANIFEST_KEYS = {"schema_version", "name", "nesti_plugin_api", "compose", "prepare", "configure", "config",
                  "skills", "events", "settings"}
_EVENT_KEYS = {"name", "service", "port", "path", "readiness_path", "secret_key"}
_PROBE_CODE = (
    "import sys, urllib.request\n"
    "with urllib.request.urlopen(sys.argv[1], timeout=5) as r:\n"
    "    sys.exit(0 if 200 <= r.status < 300 else 1)\n"
)

Runner = Callable[..., Tuple[int, str]]


class PluginError(Exception):
    """A plugin operation failed; the message is shown to the operator."""


class UsageError(PluginError):
    """A rejected command-line value (exit 2)."""


class Paths(object):
    """Plugin storage locations below one Nesti root."""

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        self.private = os.path.join(self.root, ".private", "plugins")
        self.tmp = os.path.join(self.private, "tmp")
        self.state = os.path.join(self.root, "state", "plugins")
        self.registry = os.path.join(self.state, "registry.json")
        self.lock = os.path.join(self.state, "registry.lock")
        self.runtime = os.path.join(self.state, "runtime", "active.json")

    def package(self, name: str, sha: Optional[str] = None) -> str:
        """Sources of one revision, or the package's directory of revisions."""
        return os.path.join(self.private, "packages", name, *([sha] if sha else []))

    def work(self, name: str, sha: Optional[str] = None) -> str:
        """Prepare-step work directory of one revision, or of every revision."""
        return os.path.join(self.private, "work", name, *([sha] if sha else []))

    def config(self, name: str) -> str:
        """Operator settings: bindings.json and .env."""
        return os.path.join(self.private, "config", name)

    def secrets(self, name: str) -> str:
        """Derived event signing keys of an enabled package."""
        return os.path.join(self.private, "secrets", name)


# ---------------------------------------------------------------------------
# Files, registry, lock
# ---------------------------------------------------------------------------

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _rmtree(path: str) -> None:
    def _retry(func: Callable[[str], Any], target: str, _exc: Any) -> None:
        os.chmod(target, stat.S_IWRITE)  # read-only git objects on Windows
        func(target)

    if os.path.lexists(path):
        shutil.rmtree(path, onerror=_retry)


def _rmdir_empty(path: str) -> None:
    with contextlib.suppress(OSError):
        os.rmdir(path)


def _write_atomic(path: str, data: bytes, mode: int = 0o644) -> None:
    """Replace ``path`` in one step so readers see the old or the new content, never a part."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.tmp-%d" % (path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _write_json(path: str, value: Any) -> None:
    _write_atomic(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _read_text(path: str, what: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise PluginError("cannot read %s %s: %s" % (what, path, exc)) from exc


@contextlib.contextmanager
def _locked(paths: Paths) -> Any:
    """Exclusive lock for one mutating command; the OS releases it if the process dies."""
    os.makedirs(paths.state, exist_ok=True)
    handle = open(paths.lock, "a+")
    try:
        waited = False
        while True:
            try:
                if fcntl:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if not waited:
                    print("Waiting for another 'nesti /plugin' command to finish...", file=sys.stderr)
                    waited = True
                time.sleep(0.2)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()


def load_registry(paths: Paths) -> Dict[str, Any]:
    """The registry, or an empty one when nothing is installed yet."""
    try:
        with open(paths.registry, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {"version": REGISTRY_VERSION, "packages": {}}
    except (OSError, ValueError) as exc:
        raise PluginError("cannot read %s: %s" % (paths.registry, exc)) from exc
    if not isinstance(data, dict) or data.get("version") != REGISTRY_VERSION \
            or not isinstance(data.get("packages"), dict):
        raise PluginError("%s is not a version %d plugin registry" % (paths.registry, REGISTRY_VERSION))
    return data


def compile_runtime(registry: Dict[str, Any]) -> Dict[str, Any]:
    """The ``active.json`` contract: bindings and subscriptions of enabled packages, in package order."""
    skills, subscriptions = [], []
    for name in sorted(registry["packages"]):
        record = registry["packages"][name]
        if not record.get("enabled"):
            continue
        for binding in record.get("bindings", []):
            skills.append({
                "package": name, "revision": record["sha"], "ref": record["ref"], "skill": binding["skill"],
                "path": "/".join((CONTAINER_PACKAGES_DIR, name, record["sha"], binding["path"])),
                "phases": binding["phases"], "arguments": binding["arguments"],
            })
        for sub in record.get("subscriptions", []):
            subscriptions.append({
                "package": name, "revision": record["sha"], "event": sub["event"], "url": sub["url"],
                "secret_file": "%s/%s/%s.key" % (CONTAINER_SECRETS_DIR, name, sub["event"]),
            })
    return {"version": RUNTIME_VERSION, "skills": skills, "subscriptions": subscriptions}


def _save(paths: Paths, registry: Dict[str, Any], enabling: bool = False) -> None:
    """Write registry and runtime; a crash between the two can only leave subscriptions off."""
    if enabling:
        _write_json(paths.registry, registry)
        _write_json(paths.runtime, compile_runtime(registry))
    else:
        _write_json(paths.runtime, compile_runtime(registry))
        _write_json(paths.registry, registry)


def _record(registry: Dict[str, Any], name: str) -> Dict[str, Any]:
    record = registry["packages"].get(name)
    if record is None:
        raise PluginError("%s is not installed (see 'nesti /plugin list')" % name)
    return record


# ---------------------------------------------------------------------------
# Source URL, ref, checkout
# ---------------------------------------------------------------------------

def check_url(url: str) -> None:
    """Reject URLs that carry credentials or select a command-running Git transport."""
    if not url or url.startswith("-") or any(ord(c) < 32 or ord(c) == 127 for c in url):
        raise PluginError("invalid repository URL")
    if re.match(r"^[A-Za-z0-9+.-]+::", url):
        raise PluginError("Git transport helpers (<transport>::...) are not accepted")
    if "://" in url:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in ("https", "ssh", "file"):
            raise PluginError("repository URLs must use https://, ssh://, file://, user@host:path or a local path")
        if parts.query or parts.fragment:
            raise PluginError("repository URLs must not carry a query or fragment")
        if scheme == "https" and "@" in parts.netloc:
            raise PluginError("token-bearing repository URLs are rejected: use the host's Git credentials")
        if scheme == "ssh" and parts.password is not None:
            raise PluginError("repository URLs must not carry a password")
        if scheme != "file" and not parts.hostname:
            raise PluginError("repository URL has no host")
        return
    head = url.split("/", 1)[0]
    if "@" in head and ":" in head.rsplit("@", 1)[0]:
        raise PluginError("repository URLs must not carry a password")


def check_ref(ref: str) -> None:
    """A tag name or commit id, never an option or a ref expression."""
    if not REF_RE.match(ref) or ".." in ref or "@{" in ref or ref.endswith(("/", ".lock")):
        raise PluginError("invalid --ref %r: give a tag or a commit id" % ref)


def absolute_local(url: str) -> str:
    """Expand GitHub shorthand or make a local path absolute; existing local paths take precedence."""
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*", url) and not os.path.exists(url):
        return "https://github.com/" + url + ("" if url.endswith(".git") else ".git")
    head = url.split("/", 1)[0]
    drive = os.name == "nt" and re.match(r"^[A-Za-z]:[\\/]", url)  # POSIX git reads C:/x as scp-like host C
    if "://" not in url and (drive or ":" not in head):
        return os.path.abspath(url)
    return url  # URL or scp-like user@host:path / SSH alias


def normalize_source(url: str) -> str:
    """Package identity of a repository URL: the URL without a trailing slash or ``.git``."""
    source = url.rstrip("/")
    return source[:-4] if source.endswith(".git") else source


def _normalize_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower()).strip("-_")[:48]
    if not NAME_RE.match(name):
        raise PluginError("cannot derive a package name from %r" % value)
    return name


def _git(args: List[str]) -> str:
    try:
        proc = subprocess.run(["git"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise PluginError("git is not installed") from exc
    if proc.returncode:
        raise PluginError("git %s failed: %s" % (args[0], proc.stderr.strip()[-800:]))
    return proc.stdout.strip()


def _resolve(checkout: str, ref: str) -> str:
    candidates = ["refs/tags/%s^{commit}" % ref] + (["%s^{commit}" % ref] if HEX_RE.match(ref) else [])
    for candidate in candidates:
        try:
            sha = _git(["-C", checkout, "rev-parse", "--verify", "--quiet", candidate])
        except PluginError:
            continue
        if candidate.startswith("refs/") or sha.startswith(ref.lower()):
            return sha
    raise PluginError("ref %r is not a tag or commit of the repository" % ref)


def _fetch(paths: Paths, url: str, ref: Optional[str]) -> Tuple[str, str, str]:
    """Clone at a tag/commit or default HEAD; returns (scratch, checkout, sha)."""
    os.makedirs(paths.tmp, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="fetch-", dir=paths.tmp)
    checkout = os.path.join(scratch, "src")
    try:
        _git(["clone", "--no-checkout", "--quiet", "--", url, checkout])
        sha = _resolve(checkout, ref) if ref is not None else _git(["-C", checkout, "rev-parse", "--verify", "HEAD^{commit}"])
        _git(["-C", checkout, "checkout", "--quiet", "--detach", sha])
        _rmtree(os.path.join(checkout, ".git"))
    except BaseException:
        _rmtree(scratch)
        raise
    return scratch, checkout, sha


def _inside(root: str, path: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _check_tree(root: str) -> None:
    real_root = os.path.realpath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        for entry in dirnames + filenames:
            path = os.path.join(dirpath, entry)
            if os.path.islink(path) and (os.path.isabs(os.readlink(path))
                                         or not _inside(real_root, os.path.realpath(path))):
                raise PluginError("symlink %s escapes the package" % os.path.relpath(path, root))


def _package_path(root: str, rel: Any, what: str) -> str:
    """Absolute path of an existing package-relative file that stays inside ``root``."""
    if not isinstance(rel, str) or not rel or "\\" in rel or rel.startswith("/") \
            or re.match(r"^[A-Za-z]:", rel) or any(part in ("", "..") for part in rel.split("/")):
        raise PluginError("%s path %r must be package-relative without '..'" % (what, rel))
    path = os.path.join(root, *rel.split("/"))
    if not _inside(os.path.realpath(root), os.path.realpath(path)):
        raise PluginError("%s path %r escapes the package" % (what, rel))
    if not os.path.isfile(path):
        raise PluginError("%s %r does not exist in the package" % (what, rel))
    return path


# ---------------------------------------------------------------------------
# Package discovery
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> Dict[str, str]:
    """Top-level ``key: value`` pairs of a leading ``---`` block; limited metadata, not YAML."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}
    meta, key, block = {}, None, None  # type: Dict[str, str], Optional[str], Optional[List[str]]
    for line in lines[1:end]:
        if block is not None and (line[:1] in (" ", "\t") or not line.strip()):
            block.append(line.strip())
            continue
        if block is not None and key:
            meta[key] = " ".join(part for part in block if part)
            block = None
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            meta[key] = value[1:-1]
        else:
            meta[key] = value
    if block is not None and key:
        meta[key] = " ".join(part for part in block if part)
    return meta


def _check_phases(value: Any, where: str) -> List[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or any(p not in PHASES for p in value):
        raise PluginError("%s: phases must be a list drawn from %s without repeats" % (where, ", ".join(PHASES)))
    return [phase for phase in PHASES if phase in value]


def _check_arguments(value: Any, where: str) -> Dict[str, str]:
    if not isinstance(value, dict) or len(value) > MAX_ARGUMENTS:
        raise PluginError("%s: arguments must be an object of at most %d entries" % (where, MAX_ARGUMENTS))
    for key, item in value.items():
        if not ARG_KEY_RE.match(key) or not isinstance(item, str) or len(item) > MAX_ARGUMENT_CHARS:
            raise PluginError("%s: argument %r must be a lowercase name with a string value of at most %d characters"
                              % (where, key, MAX_ARGUMENT_CHARS))
    return dict(value)


def _check_argv(root: str, argv: Any, step: str) -> None:
    """A step is a fixed argv: 1 to MAX_PREPARE_ARGS strings, a path entry point inside the package."""
    if not isinstance(argv, list) or not 1 <= len(argv) <= MAX_PREPARE_ARGS \
            or any(not isinstance(a, str) or not a or "\0" in a for a in argv):
        raise PluginError("%s must be a fixed argv list of 1 to %d strings" % (step, MAX_PREPARE_ARGS))
    if "/" in argv[0]:
        _package_path(root, argv[0], "%s entry point" % step)


def _step_argv(source_dir: str, argv: List[str], step: str) -> List[str]:
    """A validated step argv with a path entry point made absolute."""
    argv = list(argv)
    if "/" in argv[0]:
        argv[0] = _package_path(source_dir, argv[0], "%s entry point" % step)
    return argv


def _load_manifest(root: str) -> Dict[str, Any]:
    path = _package_path(root, MANIFEST, "manifest")
    try:
        data = json.loads(_read_text(path, "manifest"))
    except ValueError as exc:
        raise PluginError("%s is not valid JSON: %s" % (MANIFEST, exc)) from exc
    if not isinstance(data, dict):
        raise PluginError("%s must be a JSON object" % MANIFEST)
    unknown = sorted(set(data) - _MANIFEST_KEYS)
    if unknown:
        raise PluginError("%s has unknown keys: %s" % (MANIFEST, ", ".join(unknown)))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise PluginError("%s schema_version must be %d" % (MANIFEST, SCHEMA_VERSION))
    if data.get("nesti_plugin_api") != PLUGIN_API:
        raise PluginError("package needs plugin API %r; this Nesti supports %d" % (data.get("nesti_plugin_api"), PLUGIN_API))
    if not isinstance(data.get("name"), str) or not NAME_RE.match(data["name"]):
        raise PluginError("%s name must match %s" % (MANIFEST, NAME_RE.pattern))
    compose = data.get("compose")
    if compose is not None:
        _package_path(root, compose, "compose")
    for step in ("prepare", "configure"):
        if data.get(step) is not None:
            if compose is None:
                raise PluginError("%s needs a compose file" % step)
            _check_argv(root, data[step], step)
    config = data.get("config", {})
    if not isinstance(config, dict) or set(config) - {"env_example", "required"}:
        raise PluginError("config may hold only env_example and required")
    required = config.get("required", [])
    if not isinstance(required, list) or any(not isinstance(k, str) or not ENV_KEY_RE.match(k) for k in required):
        raise PluginError("config.required must list environment variable names")
    if "env_example" in config:
        _package_path(root, config["env_example"], "env_example")
    settings = data.get("settings", [])
    if not isinstance(settings, list) or (settings and compose is None) or any(
            not isinstance(s, dict) or set(s) - {"key", "choices", "secret"} or not isinstance(s.get("key"), str)
            or not ENV_KEY_RE.match(s["key"]) or ("secret" in s and not isinstance(s["secret"], bool))
            or (s.get("secret") and "choices" in s) or ("choices" in s and (
                not isinstance(s["choices"], list) or not s["choices"]
                or any(not isinstance(c, str) or not SETTING_VALUE_RE.fullmatch(c) for c in s["choices"])))
            for s in settings) or len({s["key"] for s in settings}) != len(settings):
        raise PluginError('settings must list distinct {"key": <env name>, "choices": [<values>]} or '
                          '{"key": <env name>, "secret": true} entries and need a compose file')
    skills, seen = data.get("skills", []), set()
    if not isinstance(skills, list):
        raise PluginError("skills must be a list")
    for skill in skills:
        if not isinstance(skill, dict) or set(skill) - {"name", "path", "phases", "arguments"} \
                or not isinstance(skill.get("name"), str) or not SKILL_RE.match(skill["name"]):
            raise PluginError("each skill needs a valid name, a path and optional phases/arguments")
        if skill["name"] in seen:
            raise PluginError("skill %r is declared twice" % skill["name"])
        seen.add(skill["name"])
        _package_path(root, skill.get("path"), "skill %s" % skill["name"])
        _check_phases(skill.get("phases", []), "skill %s" % skill["name"])
        _check_arguments(skill.get("arguments", {}), "skill %s" % skill["name"])
    events, seen = data.get("events", []), set()
    if not isinstance(events, list) or (events and compose is None):
        raise PluginError("events must be a list and need a compose file")
    for event in events:
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise PluginError("each event needs exactly: %s" % ", ".join(sorted(_EVENT_KEYS)))
        if event["name"] not in EVENTS or event["name"] in seen:
            raise PluginError("event %r is unknown or repeated (known: %s)" % (event["name"], ", ".join(EVENTS)))
        seen.add(event["name"])
        port = event["port"]
        if not isinstance(event["service"], str) or not event["service"] \
                or not isinstance(port, int) or isinstance(port, bool) or not 0 < port < 65536 \
                or not all(isinstance(event[k], str) and URL_PATH_RE.match(event[k]) for k in ("path", "readiness_path")) \
                or not isinstance(event["secret_key"], str) or not ENV_KEY_RE.match(event["secret_key"]):
            raise PluginError("event %s has an invalid service, port, path, readiness_path or secret_key" % event["name"])
    if compose is None and not skills:
        raise PluginError("%s declares neither compose nor skills" % MANIFEST)
    return data


def _discover_skills(root: str) -> List[Dict[str, Any]]:
    base = os.path.join(root, "skills")
    if not os.path.isdir(base):
        return []
    found, names = [], set()
    for entry in sorted(os.listdir(base)):
        if not os.path.isfile(os.path.join(base, entry, "SKILL.md")):
            continue
        rel = "skills/%s/SKILL.md" % entry
        meta = parse_frontmatter(_read_text(_package_path(root, rel, "skill"), "skill"))
        name = meta.get("name") or entry
        if not SKILL_RE.match(name):
            raise PluginError("skill %s has an invalid name %r" % (rel, name))
        if name in names:
            raise PluginError("two skills are named %r" % name)
        names.add(name)
        found.append({"name": name, "path": rel})
    return found


def _plain_name(root: str, source: str) -> str:
    for rel in ("plugin.json", ".claude-plugin/plugin.json", "package.json"):
        path = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        name = data.get("name") if isinstance(data, dict) else None
        if isinstance(name, str) and name.strip():
            return _normalize_name(name.split("/")[-1])
    return _normalize_name(re.split(r"[/:\\]", source)[-1])


def inspect_package(root: str, source: str) -> Dict[str, Any]:
    """Validate a checkout and describe it: name, kind, skills (main flag) and the native manifest."""
    _check_tree(root)
    if os.path.lexists(os.path.join(root, MANIFEST)):
        manifest = _load_manifest(root)
        skills = [{"name": s["name"], "path": s["path"], "main": False} for s in manifest.get("skills", [])]
        return {"name": manifest["name"], "kind": "service" if manifest.get("compose") else "skills",
                "skills": skills, "manifest": manifest}
    skills = _discover_skills(root)
    if not skills:
        raise PluginError("no %s and no skills/*/SKILL.md found" % MANIFEST)
    name = _plain_name(root, source)
    for skill in skills:
        skill["main"] = skill["name"] == name
    return {"name": name, "kind": "skills", "skills": skills, "manifest": None}


# ---------------------------------------------------------------------------
# Skill bindings
# ---------------------------------------------------------------------------

def _default_bindings(info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if info["manifest"]:
        return {s["name"]: {"phases": _check_phases(s.get("phases", []), s["name"]),
                            "arguments": dict(s.get("arguments", {}))}
                for s in info["manifest"].get("skills", [])}
    return {s["name"]: {"phases": list(PHASES) if s["main"] else [], "arguments": {}} for s in info["skills"]}


def _bindings_file(paths: Paths, name: str) -> str:
    return os.path.join(paths.config(name), "bindings.json")


def _load_bindings(paths: Paths, name: str) -> Dict[str, Any]:
    """bindings.json as written, with its top-level shape checked; {} when absent."""
    path = _bindings_file(paths, name)
    if not os.path.isfile(path):
        return {}
    if os.path.getsize(path) > BINDINGS_MAX_BYTES:
        raise PluginError("%s is larger than %d bytes" % (path, BINDINGS_MAX_BYTES))
    try:
        data = json.loads(_read_text(path, "bindings"))
    except ValueError as exc:
        raise PluginError("%s is not valid JSON: %s" % (path, exc)) from exc
    if not isinstance(data, dict) or set(data) - {"skills"} or not isinstance(data.get("skills", {}), dict):
        raise PluginError('%s must look like {"skills": {"<skill>": {"phases": [...], "arguments": {...}}}}' % path)
    return data


def effective_bindings(paths: Paths, name: str, info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Bound skills in package order: defaults overridden per skill by bindings.json."""
    effective = _default_bindings(info)
    path = _bindings_file(paths, name)
    for skill, entry in _load_bindings(paths, name).get("skills", {}).items():
        if skill not in effective:
            raise PluginError("%s names unknown skill %r (available: %s)"
                              % (path, skill, ", ".join(sorted(effective))))
        if not isinstance(entry, dict) or set(entry) - {"phases", "arguments"}:
            raise PluginError("%s: skill %s may hold only phases and arguments" % (path, skill))
        if "phases" in entry:
            effective[skill]["phases"] = _check_phases(entry["phases"], "%s: skill %s" % (path, skill))
        if "arguments" in entry:
            effective[skill]["arguments"] = _check_arguments(entry["arguments"], "%s: skill %s" % (path, skill))
    return [{"skill": s["name"], "path": s["path"], "phases": effective[s["name"]]["phases"],
             "arguments": effective[s["name"]]["arguments"]}
            for s in info["skills"] if effective[s["name"]]["phases"]]


def _compile_bindings(paths: Paths, registry: Dict[str, Any], name: str, info: Dict[str, Any],
                      source_dir: str) -> List[Dict[str, Any]]:
    """Bound skills with their sizes; refuses a phase total above the limit instead of truncating."""
    bound = effective_bindings(paths, name, info)
    if info["kind"] == "skills" and not bound:
        hint = "" if any(s["main"] for s in info["skills"]) else "no skill is named %r; " % name
        raise PluginError("%sno skill is bound: set its phases in %s" % (hint, _bindings_file(paths, name)))
    totals = dict((phase, 0) for phase in PHASES)
    for other, record in registry["packages"].items():
        if other != name and record.get("enabled"):
            for binding in record.get("bindings", []):
                for phase in binding["phases"]:
                    totals[phase] += binding["chars"]
    settings = [] if info["manifest"] else _declared_settings(source_dir, info)
    setting = settings[0] if settings else None
    for binding in bound:
        if setting and setting.get("default") and binding["skill"] == setting["skill"] and not binding["arguments"]:
            binding["arguments"] = {"args": setting["default"]}
        text = _read_text(_package_path(source_dir, binding["path"], "skill %s" % binding["skill"]), "skill")
        if not text.strip():
            raise PluginError("skill %s is empty" % binding["skill"])
        binding["chars"] = len(text)
        for phase in binding["phases"]:
            totals[phase] += binding["chars"]
    for phase in PHASES:
        if totals[phase] > PHASE_BINDING_CHAR_LIMIT:
            raise PluginError("enabled %s-phase skills would total %d characters, above the %d limit "
                              "(nothing is truncated): unbind a skill in %s"
                              % (phase, totals[phase], PHASE_BINDING_CHAR_LIMIT, _bindings_file(paths, name)))
    return bound


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

def run_command(argv: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
                timeout: Optional[float] = None, stream: bool = False, merge_output: bool = False) -> Tuple[int, str]:
    """Run argv; capture stdout (plus errors on failure), or merge diagnostics for redaction. 124 = timeout."""
    full_env = None
    if env:
        full_env = dict(os.environ)
        full_env.update(env)
    try:
        if stream:
            return subprocess.run(argv, cwd=cwd, env=full_env, timeout=timeout).returncode, ""
        proc = subprocess.run(argv, cwd=cwd, env=full_env, timeout=timeout, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT if merge_output else subprocess.PIPE, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return 127, "%s: command not found" % argv[0]
    except subprocess.TimeoutExpired:
        return 124, "timed out after %s s" % timeout
    return proc.returncode, proc.stdout if proc.returncode == 0 or merge_output else proc.stdout + proc.stderr


class Docker(object):
    """Docker and Compose argv builders over an injectable runner."""

    def __init__(self, runner: Optional[Runner] = None, compose: Optional[List[str]] = None,
                 redactions: Optional[Dict[str, str]] = None) -> None:
        self.runner = runner or run_command
        self._compose = compose
        self._redactions = redactions or {}

    def compose(self) -> List[str]:
        """``docker-compose`` when installed, else ``docker compose`` (install.sh's order)."""
        if self._compose is None:
            self._compose = ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
        return self._compose

    def _check(self, argv: List[str], what: str, **kwargs: Any) -> str:
        code, output = self.runner(argv, **kwargs)
        if code:
            raise PluginError("%s failed (exit %d): %s" % (what, code, _redact(output, self._redactions).strip()[-800:]))
        return output

    def config(self, source_dir: str, compose_file: str) -> Dict[str, Any]:
        """The package's Compose model without interpolation (no settings needed)."""
        output = self._check(self.compose() + ["-f", compose_file, "config", "--no-interpolate", "--format", "json"],
                             "docker compose config", cwd=source_dir)
        try:
            data = json.loads(output)
        except ValueError as exc:
            raise PluginError("docker compose config did not print JSON (Compose v2 is required)") from exc
        if not isinstance(data, dict):
            raise PluginError("docker compose config did not print a JSON object")
        return data

    def up(self, project: str, compose_file: str, env_file: str, source_dir: str, env: Dict[str, str]) -> None:
        """Start prepared images, recreating running containers so they load the current configuration; never builds."""
        argv = self.compose() + ["-p", project, "-f", compose_file]
        if os.path.isfile(env_file):
            argv += ["--env-file", env_file]
        self._check(argv + ["up", "-d", "--no-build", "--force-recreate", "--remove-orphans"], "docker compose up",
                    cwd=source_dir, env=env)

    def containers(self, project: str) -> List[Tuple[str, str, str]]:
        """(name, state, compose service) of every container of a Compose project."""
        output = self._check(["docker", "ps", "-a", "--filter", "label=com.docker.compose.project=%s" % project,
                              "--format", '{{.Names}}\t{{.State}}\t{{.Label "com.docker.compose.service"}}'],
                             "docker ps")
        rows = []
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0]:
                rows.append((parts[0], parts[1], parts[2]))
        return rows

    def stop(self, names: List[str]) -> None:
        """Stop containers; data stays."""
        if names:
            self._check(["docker", "stop"] + names, "docker stop")

    def remove(self, names: List[str]) -> None:
        """Remove stopped containers; volumes stay (no -v)."""
        if names:
            self._check(["docker", "rm"] + names, "docker rm")

    def ensure_network(self) -> None:
        """Create the internal event network when missing."""
        if self.runner(["docker", "network", "inspect", NETWORK])[0]:
            self._check(["docker", "network", "create", "--internal", NETWORK], "docker network create")

    def ensure_probe_image(self) -> None:
        """The readiness probe runs from the orchestrator image."""
        if self.runner(["docker", "image", "inspect", PROBE_IMAGE])[0]:
            raise PluginError("the readiness probe needs the %s image: build Nesti first (run install.sh)" % PROBE_IMAGE)

    def probe(self, url: str) -> bool:
        """GET ``url`` from a throwaway container on the event network; the container never survives."""
        name = "nesti-plugin-probe-%s" % secrets.token_hex(4)
        code, _ = self.runner(["docker", "run", "--rm", "--name", name, "--network", NETWORK,
                               "--entrypoint", "python", PROBE_IMAGE, "-c", _PROBE_CODE, url], timeout=PROBE_TIMEOUT)
        if code == 124:
            self.runner(["docker", "rm", "-f", name])
        return code == 0


def _project(name: str) -> str:
    return "nesti-plugin-%s" % name


def _project_path(paths: Paths) -> str:
    """NESTI_PROJECT_PATH from Nesti's own .env: the managed project Nesti mounts; '' when unset."""
    return _read_env(os.path.join(paths.root, ".env")).get("NESTI_PROJECT_PATH", "")


def _plugin_env(paths: Paths, name: str, sha: str) -> Dict[str, str]:
    env = {"NESTI_PLUGIN_NAME": name, "NESTI_PLUGIN_SHA": sha, "NESTI_PLUGIN_DIR": paths.package(name, sha),
           "NESTI_PLUGIN_CONFIG_DIR": paths.config(name), "NESTI_PLUGIN_WORK_DIR": paths.work(name, sha),
           "NESTI_PLUGIN_NETWORK": NETWORK}
    project_path = _project_path(paths)
    if project_path:
        env["NESTI_PROJECT_PATH"] = project_path
    return env


def plugin_context(paths: Paths, registry: Dict[str, Any], name: str) -> Dict[str, Any]:
    """The runtime context a service's configure step sees: project path and other packages' enabled skills."""
    skills = []
    for other in sorted(registry["packages"]):
        record = registry["packages"][other]
        if other == name or not record.get("enabled"):
            continue
        source_dir = paths.package(other, record["sha"])
        for binding in record.get("bindings", []):
            where = "skill %s/%s" % (other, binding["skill"])
            skills.append({
                "package": other, "skill": binding["skill"], "revision": record["sha"], "ref": record["ref"],
                "arguments": dict(binding["arguments"]), "phases": list(binding["phases"]),
                "text": _read_text(_package_path(source_dir, binding["path"], where), where),
            })
    return {"version": CONTEXT_VERSION, "project_path": _project_path(paths), "skills": skills}


def _digest(context: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode("utf-8")).hexdigest()


def _redact(text: str, values: Dict[str, str]) -> str:
    for value in sorted(set(values.values()) - {""}, key=len, reverse=True):
        text = text.replace(value, "[redacted]")
    return text


def _configure(paths: Paths, docker: Docker, registry: Dict[str, Any], name: str, sha: str,
               argv: List[str], values: Dict[str, str]) -> str:
    """Run the package's configure step with settings and runtime context; returns the context digest."""
    context = plugin_context(paths, registry, name)
    os.makedirs(paths.tmp, exist_ok=True)
    fd, context_file = tempfile.mkstemp(prefix="context-", suffix=".json", dir=paths.tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(context, handle, indent=2, sort_keys=True)
        env = dict(values)
        env.update(_plugin_env(paths, name, sha))
        env["NESTI_PLUGIN_CONTEXT"] = context_file
        os.makedirs(paths.work(name, sha), exist_ok=True)
        source_dir = paths.package(name, sha)
        code, output = docker.runner(_step_argv(source_dir, argv, "configure"), cwd=source_dir, env=env, merge_output=True)
        if output:
            print(_redact(output, values), end="" if output.endswith("\n") else "\n")
    finally:
        with contextlib.suppress(OSError):
            os.unlink(context_file)
    if code:
        raise PluginError("configure step failed (exit %d)" % code)
    return _digest(context)


def stale_note(paths: Paths, registry: Dict[str, Any], name: str) -> str:
    """Why an enabled, configured service runs on an outdated runtime context; '' when current."""
    record = registry["packages"][name]
    if not record.get("enabled") or not record.get("context_digest"):
        return ""
    try:
        current = _digest(plugin_context(paths, registry, name))
    except PluginError as exc:
        return "cannot read its runtime context: %s" % exc
    if current == record["context_digest"]:
        return ""
    return ("author skills or the project path changed since it was enabled; "
            "run 'nesti /plugin enable %s' to regenerate its configuration and restart it" % name)


def _print_stale(paths: Paths) -> None:
    registry = load_registry(paths)
    for name in sorted(registry["packages"]):
        note = stale_note(paths, registry, name)
        if note:
            print("Stale: %s: %s." % (name, note))


def _read_env(path: str) -> Dict[str, str]:
    values = {}
    if not os.path.isfile(path):
        return values
    for raw in _read_text(path, "settings").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, sep, value = line.partition("=")
        if not sep or line.startswith("#"):
            continue
        value = value.strip()
        if value[:1] in ("'", '"') and value.find(value[0], 1) > 0:
            value = value[1:value.find(value[0], 1)]  # quoted: '#' is literal, text after the quote is ignored
        else:
            value = re.split(r"\s#", value, maxsplit=1)[0].rstrip()  # unquoted: ' #' starts a comment, as in Compose
        values[key.strip()] = value
    return values


def _settings(paths: Paths, name: str, manifest: Dict[str, Any]) -> Dict[str, str]:
    """The package's .env values; fails naming (never printing) missing required keys."""
    env_file = os.path.join(paths.config(name), ".env")
    values = _read_env(env_file)
    required = list(manifest.get("config", {}).get("required", []))
    required += [event["secret_key"] for event in manifest.get("events", [])]
    missing = sorted(set(key for key in required if not values.get(key)))
    if missing:
        raise PluginError("missing settings in %s: %s" % (env_file, ", ".join(missing)))
    return values


def _describe_compose(config: Dict[str, Any], compose_dir: str) -> List[str]:
    lines = []
    services = config.get("services") or {}
    for sname in sorted(services):
        svc = services[sname] or {}
        build = svc.get("build")
        what = svc.get("image") or ""
        if build:
            context = build.get("context") if isinstance(build, dict) else build
            what = (what + ", " if what else "") + "built from %s" % context
        lines.append("  service %s: %s" % (sname, what or "no image"))
        for volume in svc.get("volumes") or []:
            if isinstance(volume, dict):
                source = str(volume.get("source", "(anonymous)"))
                prefix = compose_dir.rstrip("/\\") + os.sep
                if source.startswith(prefix) and source[len(prefix):].startswith("$"):
                    source = source[len(prefix):]  # Compose prefixes a $VAR source with the compose file's dir
                desc = "%s %s -> %s%s" % (volume.get("type", "volume"), source,
                                          volume.get("target"), " (read-only)" if volume.get("read_only") else "")
            else:
                desc = str(volume)
            lines.append("    mount: %s" % desc)
            if "docker.sock" in desc:
                lines.append("    WARNING: mounts the Docker socket")
        networks = svc.get("networks")
        lines.append("    network: %s" % (svc.get("network_mode") or ", ".join(sorted(networks or {})) or "default"))
        for port in svc.get("ports") or []:
            lines.append("    published port: %s" % (json.dumps(port, sort_keys=True) if isinstance(port, dict) else port))
        flags = (["privileged"] if svc.get("privileged") else []) + ["cap_add %s" % c for c in svc.get("cap_add") or []]
        flags += ["%s=%s" % (k, svc[k]) for k in ("network_mode", "pid", "ipc") if svc.get(k) == "host"]
        if flags:
            lines.append("    WARNING: %s" % ", ".join(flags))
    for vname in sorted(config.get("volumes") or {}):
        volume = (config.get("volumes") or {})[vname] or {}
        lines.append("  volume %s%s" % (vname, " (external: %s)" % volume.get("name", vname) if volume.get("external") else ""))
    for nname in sorted(config.get("networks") or {}):
        network = (config.get("networks") or {})[nname] or {}
        kind = "external" if network.get("external") else "internal" if network.get("internal") else "with outbound access"
        lines.append("  network %s (%s)" % (nname, kind))
    return lines


def _trust_and_prepare(paths: Paths, docker: Docker, info: Dict[str, Any], source: str, ref: str, sha: str,
                       trust: bool) -> None:
    """Show what the revision will run, require approval, then run its fixed-argv prepare step."""
    name, manifest = info["name"], info["manifest"]
    source_dir = paths.package(name, sha)
    compose_file = _package_path(source_dir, manifest["compose"], "compose")
    config = docker.config(source_dir, compose_file)
    services = config.get("services") or {}
    for event in manifest.get("events", []):
        if event["service"] not in services:
            raise PluginError("event %s names service %r, which the compose file lacks" % (event["name"], event["service"]))
    prepare = manifest.get("prepare")
    print("Trust check for %s" % name)
    print("  repository: %s" % source)
    print("  revision:   %s (ref %s)" % (sha, ref))
    print("  prepare:    %s" % (" ".join(shlex.quote(a) for a in prepare) if prepare else "none"))
    if manifest.get("configure"):
        print("  configure:  %s (runs at every enable, with the package settings and Nesti's runtime context)"
              % " ".join(shlex.quote(a) for a in manifest["configure"]))
    for line in _describe_compose(config, os.path.dirname(compose_file)):
        print(line)
    print("Package code (prepare, Compose builds and services) runs with this host's Docker privileges; "
          "trusting it is not a sandbox.")
    if trust:
        print("Trusted with --trust.")
    elif not sys.stdin.isatty():
        raise PluginError("this revision runs package code: review the summary above and re-run with --trust")
    elif input("Trust this revision%s? [y/N] " % (" and run its prepare step" if prepare else "")).strip().lower() \
            not in ("y", "yes"):
        raise PluginError("not trusted; nothing was run")
    if prepare:
        os.makedirs(paths.work(name, sha), exist_ok=True)
        code, _ = docker.runner(_step_argv(source_dir, prepare, "prepare"), cwd=source_dir,
                                env=_plugin_env(paths, name, sha), stream=True)
        if code:
            raise PluginError("prepare step failed (exit %d)" % code)


def _wait_ready(docker: Docker, urls: List[str]) -> None:
    deadline = time.time() + READY_TIMEOUT
    pending = list(urls)
    while True:
        pending = [url for url in pending if not docker.probe(url)]
        if not pending:
            return
        if time.time() >= deadline:
            raise PluginError("not ready after %d s: %s" % (READY_TIMEOUT, ", ".join(pending)))
        time.sleep(2)


def _write_secret(paths: Paths, name: str, event: str, value: str) -> None:
    os.makedirs(paths.secrets(name), mode=0o700, exist_ok=True)
    _write_atomic(os.path.join(paths.secrets(name), "%s.key" % event), value.encode("utf-8"), mode=0o600)


def _stop_project(docker: Docker, project: str) -> str:
    """Stop the project's live containers; returns '' or a 'state unknown' / 'still running' note."""
    try:
        containers = docker.containers(project)
    except PluginError as exc:
        return "; service state unknown: %s" % exc
    try:
        docker.stop([n for n, state, _ in containers if state in ("running", "restarting", "paused")])
    except PluginError as exc:
        return "; service still running: %s" % exc
    return ""


def _activate(paths: Paths, docker: Docker, registry: Dict[str, Any], name: str, sha: str,
              info: Dict[str, Any]) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Validate settings, configure, start Compose, verify readiness, write signing keys.

    Returns the subscriptions and the digest of the runtime context configure saw (None without configure).
    Any failure stops the project's containers, so a re-enable never leaves the old ones running unpublished.
    """
    manifest = info["manifest"]
    events = manifest.get("events", [])
    source_dir = paths.package(name, sha)
    project = _project(name)
    values = {}
    try:
        values = _settings(paths, name, manifest)
        docker = Docker(docker.runner, docker.compose(), redactions=values)
        compose_file = _package_path(source_dir, manifest["compose"], "compose")
        digest = None
        if manifest.get("configure"):
            digest = _configure(paths, docker, registry, name, sha, manifest["configure"], values)
        docker.ensure_network()
        if events:
            docker.ensure_probe_image()
        docker.up(project, compose_file, os.path.join(paths.config(name), ".env"), source_dir,
                  _plugin_env(paths, name, sha))
        containers = docker.containers(project)
        subscriptions, ready = [], []
        for event in events:
            hosts = [n for n, _, service in containers if service == event["service"]]
            if len(hosts) != 1:
                raise PluginError("service %s has %d containers; an event needs exactly one" % (event["service"], len(hosts)))
            base = "http://%s:%d" % (hosts[0], event["port"])
            subscriptions.append({"event": event["name"], "url": base + event["path"]})
            ready.append(base + event["readiness_path"])
        if events:
            _wait_ready(docker, ready)
        elif not containers or any(state in ("restarting", "dead", "created") for _, state, _ in containers):
            raise PluginError("services did not come up: %s" % (", ".join("%s %s" % c[:2] for c in containers) or "no containers"))
        for event in events:
            _write_secret(paths, name, event["name"], values[event["secret_key"]])
        return subscriptions, digest
    except (PluginError, OSError) as exc:
        raise PluginError(_redact("%s%s" % (exc, _stop_project(docker, project)), values)) from exc
    except BaseException:  # e.g. Ctrl-C during configure or readiness: stop what may run, then re-raise
        with contextlib.suppress(Exception):
            _stop_project(docker, project)
        raise


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _print_skills(paths: Paths, name: str, info: Dict[str, Any]) -> None:
    try:
        bound = dict((b["skill"], b["phases"]) for b in effective_bindings(paths, name, info))
    except PluginError as exc:
        print("  bindings: %s" % exc)
        bound = {}
    for skill in info["skills"]:
        notes = (["main"] if skill.get("main") else []) + bound.get(skill["name"], [])
        print("  skill:    %s%s" % (skill["name"], " (%s)" % ", ".join(notes) if notes else ""))
    if info["kind"] == "skills" and not bound:
        print("  No skill is bound by default: set a skill's phases in %s before enabling." % _bindings_file(paths, name))


def _write_bindings_template(paths: Paths, name: str, info: Dict[str, Any]) -> None:
    path = _bindings_file(paths, name)
    if info["skills"] and not os.path.exists(path):
        _write_json(path, {"skills": _default_bindings(info)})


def cmd_install(paths: Paths, docker: Docker, url: str, ref: Optional[str], trust: bool) -> None:
    """Clone, validate and record a revision; service packages are trusted and prepared, never started."""
    check_url(url)
    if ref is not None:
        check_ref(ref)
    url = absolute_local(url)
    source = normalize_source(url)
    with _locked(paths):
        registry = load_registry(paths)
        scratch, checkout, sha = _fetch(paths, url, ref)
        if ref is None:
            ref = sha
        try:
            info = inspect_package(checkout, source)
            name = info["name"]
            record = registry["packages"].get(name)
            if record is not None:
                if record["source"] != source:
                    raise PluginError("package name %r is already installed from %s; another source cannot reuse it"
                                      % (name, record["source"]))
                if record["sha"] == sha:
                    print("%s is already installed at %s (ref %s); nothing changed." % (name, sha, record["ref"]))
                    return
                raise PluginError("%s is installed at %s; switch with 'nesti /plugin update %s --ref %s'"
                                  % (name, record["sha"], name, ref))
            for other, other_record in registry["packages"].items():
                if other_record["source"] == source:
                    raise PluginError("%s is already installed as %r" % (source, other))
            if os.path.lexists(paths.package(name)) or os.path.lexists(paths.work(name)):
                raise PluginError("%s or %s exists without a registry record; remove it first"
                                  % (paths.package(name), paths.work(name)))
            os.makedirs(paths.package(name))
            os.replace(checkout, paths.package(name, sha))
        finally:
            _rmtree(scratch)
        try:
            if info["kind"] == "service":
                _trust_and_prepare(paths, docker, info, source, ref, sha, trust)
            os.makedirs(paths.config(name), mode=0o700, exist_ok=True)
            _write_bindings_template(paths, name, info)
            registry["packages"][name] = {
                "kind": info["kind"], "url": url, "source": source, "ref": ref, "sha": sha,
                "installed_at": _now(), "enabled": False,
                "trusted_sha": sha if info["kind"] == "service" else None,
                "skills": info["skills"], "service": {"project": _project(name)} if info["kind"] == "service" else None,
                "bindings": [], "subscriptions": [], "error": None,
            }
            _save(paths, registry)
        except BaseException:
            _rmtree(paths.package(name))
            _rmtree(paths.work(name))
            raise
    print("Installed %s %s (%s) from %s" % (name, ref, sha, source))
    print("  sources:  %s" % paths.package(name, sha))
    _print_skills(paths, name, info)
    if info["skills"]:
        print("  bindings: %s" % _bindings_file(paths, name))
    if info["kind"] == "service":
        config = info["manifest"].get("config", {})
        required = list(config.get("required", [])) + [e["secret_key"] for e in info["manifest"].get("events", [])]
        example = " (copy %s)" % os.path.join(paths.package(name, sha), *config["env_example"].split("/")) \
            if config.get("env_example") else ""
        print("  settings: %s%s" % (os.path.join(paths.config(name), ".env"), example))
        if required:
            print("  required: %s" % ", ".join(sorted(set(required))))
    _print_settings(paths, name, info, paths.package(name, sha))
    print("Enable with: nesti /plugin enable %s" % name)


def cmd_enable(paths: Paths, docker: Docker, name: str) -> None:
    """Publish skill bindings; for a service, start it and publish subscriptions only after readiness."""
    with _locked(paths):
        registry = load_registry(paths)
        record = _record(registry, name)
        source_dir = paths.package(name, record["sha"])
        info = inspect_package(source_dir, record["source"])
        bindings = _compile_bindings(paths, registry, name, info, source_dir)
        subscriptions, digest = [], None
        if record["kind"] == "service":
            if record.get("trusted_sha") != record["sha"]:
                raise PluginError("revision %s is not trusted; reinstall or update with trust" % record["sha"])
            was_enabled = record["enabled"]
            if was_enabled:  # re-enable: unpublish until the recreated services are ready again
                record.update(enabled=False, bindings=[], subscriptions=[], context_digest=None)
                _save(paths, registry)
                _rmtree(paths.secrets(name))
            try:
                subscriptions, digest = _activate(paths, docker, registry, name, record["sha"], info)
            except PluginError as exc:
                if was_enabled:
                    record["error"] = "enable failed: %s" % exc
                    _save(paths, registry)
                raise
            except BaseException:
                record.update(enabled=False, bindings=[], subscriptions=[], context_digest=None,
                              error="enable interrupted; service state unknown")
                _save(paths, registry)
                _rmtree(paths.secrets(name))
                raise
        record.update(enabled=True, bindings=bindings, subscriptions=subscriptions, context_digest=digest, error=None)
        _save(paths, registry, enabling=True)
    print("Enabled %s at %s (ref %s)." % (name, record["sha"], record["ref"]))
    for binding in bindings:
        print("  skill %s: %s" % (binding["skill"], ", ".join(binding["phases"])))
    for sub in subscriptions:
        print("  event %s -> %s" % (sub["event"], sub["url"]))


def _declared_settings(source_dir: str, info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Manifest settings or main skill hint; only a unique description default is inferred."""
    if info["manifest"]:
        return [{"name": s["key"], "choices": s.get("choices"), "secret": s.get("secret", False), "skill": None}
                for s in info["manifest"].get("settings", [])]
    main = next((s for s in info["skills"] if s["main"]), None)
    if main is None:
        return []
    text = _read_text(_package_path(source_dir, main["path"], "skill %s" % main["name"]), "skill")
    meta = parse_frontmatter(text)
    hint = meta.get("argument-hint", "").strip().strip("[]").strip()
    if not hint:
        return []
    choices = [c.strip() for c in hint.split("|") if c.strip()] if "|" in hint else []
    description = meta.get("description", "")
    defaults = re.findall(r"(\S+)\s+\(default\)", description)
    default = defaults[0] if description.count("(default)") == 1 and len(defaults) == 1 \
        and defaults[0] in choices and SETTING_VALUE_RE.fullmatch(defaults[0]) \
        and len(defaults[0]) <= MAX_ARGUMENT_CHARS else None
    return [{"name": "args", "choices": choices or None, "secret": False, "skill": main["name"], "default": default}]


def _setting_text(paths: Paths, name: str, info: Dict[str, Any], setting: Dict[str, Any]) -> str:
    """'<name> = <value> (choices: ...)'; reads only the declared key, never another .env value."""
    label = setting["name"]
    default_note = ""
    if setting["skill"]:
        effective_bindings(paths, name, info)  # validates the entries read below
        entry = _load_bindings(paths, name).get("skills", {}).get(setting["skill"], {})
        arguments = entry.get("arguments", {})
        default = setting.get("default")
        if arguments:
            if set(arguments) == {"args"}:
                value = arguments["args"] or '""'
            else:
                label, value = "arguments", json.dumps(arguments, sort_keys=True)
            if default:
                default_note = " (plugin default: %s)" % default
        else:
            value = "%s (plugin default)" % default if default else "not set (plugin default unknown)"
    else:
        raw = _read_env(os.path.join(paths.config(name), ".env")).get(setting["name"], "")
        value = ("set (secret)" if raw else "not set (secret)") if setting["secret"] else raw or "not set (plugin default)"
    choices = " (choices: %s)" % ", ".join(setting["choices"]) if setting["choices"] else ""
    return "%s = %s%s%s" % (label, value, default_note, choices)


def _change_hint(name: str, settings: List[Dict[str, Any]], setting: Dict[str, Any]) -> str:
    return "nesti /%s %s%s" % (name, "" if len(settings) == 1 else setting["name"] + " ",
                              "-" if setting["secret"] else "<value>")


def _print_settings(paths: Paths, name: str, info: Dict[str, Any], source_dir: str) -> None:
    try:
        settings = _declared_settings(source_dir, info)
        for setting in settings:
            print("  setting:  %s; change with: %s" % (_setting_text(paths, name, info, setting),
                                                      _change_hint(name, settings, setting)))
    except PluginError as exc:
        print("  setting:  %s" % exc)


def _set_env(path: str, key: str, value: str) -> None:
    """Set one .env key: only its line changes (appended when absent); every other byte and the mode stay."""
    try:
        with open(path, "rb") as handle:
            data = handle.read().decode("utf-8")
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        data, mode = "", 0o600
    except (OSError, UnicodeDecodeError) as exc:
        raise PluginError("cannot read settings %s: %s" % (path, exc)) from exc
    lines, found = data.splitlines(True), None
    for index, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, sep, _ = line.partition("=")
        if sep and not line.startswith("#") and name.strip() == key:
            found = index  # the last one wins, as in _read_env
    if found is None:
        lines.append("%s%s=%s\n" % ("\n" if data and not data.endswith(("\n", "\r")) else "", key, value))
    else:
        body = lines[found].rstrip("\r\n")
        lines[found] = body[:body.index("=") + 1] + value + lines[found][len(body):]
    _write_atomic(path, "".join(lines).encode("utf-8"), mode)
    os.chmod(path, mode)  # the umask may have narrowed the new file's mode


def cmd_settings(paths: Paths, name: str) -> None:
    """Show the plugin's declared settings and safe current values; read-only."""
    record = _record(load_registry(paths), name)
    source_dir = paths.package(name, record["sha"])
    info = inspect_package(source_dir, record["source"])
    settings = _declared_settings(source_dir, info)
    if not settings:
        print("%s offers no settings." % name)
        return
    print("%s settings:" % name)
    for setting in settings:
        print("  %s" % _setting_text(paths, name, info, setting))
    hint = _change_hint(name, settings, settings[0]) if len(settings) == 1 else "nesti /%s <KEY> <value>" % name
    if len(settings) > 1 and any(s["secret"] for s in settings):
        hint += "; a secret takes '-' and is typed at the prompt"
    print("Change with: %s" % hint)


def cmd_set(paths: Paths, docker: Docker, name: str, value: str, key: Optional[str] = None,
            prompted: bool = False) -> None:
    """Switch a declared setting; an enabled plugin is re-enabled to apply it."""
    with _locked(paths):
        record = _record(load_registry(paths), name)
        source_dir = paths.package(name, record["sha"])
        info = inspect_package(source_dir, record["source"])
        settings = _declared_settings(source_dir, info)
        if not settings:
            raise PluginError("%s offers no settings" % name)
        keys = ", ".join(s["name"] for s in settings)
        if key is None and len(settings) != 1:
            raise UsageError("%s has %d settings: use nesti /%s <KEY> <value> (keys: %s)"
                             % (name, len(settings), name, keys))
        setting = settings[0] if key is None else next((s for s in settings if s["name"] == key), None)
        if setting is None:
            raise UsageError("%s has no setting %s (keys: %s)" % (name, key, keys))
        if setting["secret"] and not prompted:
            raise UsageError("%s is a secret: pass '-' and type the value at the prompt, so it never reaches "
                             "the command line or shell history" % setting["name"])
        if setting["choices"] and value not in setting["choices"]:
            raise UsageError("%s must be one of: %s" % (setting["name"], ", ".join(setting["choices"])))
        if not setting["choices"] and not SETTING_VALUE_RE.fullmatch(value):
            raise UsageError("%s must be 1 to 128 characters without whitespace, quotes, '#', '$', '\\' "
                             "or control characters" % setting["name"])
        if setting["skill"]:
            try:
                _check_arguments({"args": value}, setting["name"])
            except PluginError as exc:
                raise UsageError(str(exc)) from exc
            effective_bindings(paths, name, info)  # never overwrite a broken bindings.json
            data = _load_bindings(paths, name)
            data.setdefault("skills", {}).setdefault(setting["skill"], {})["arguments"] = {"args": value}
            _write_json(_bindings_file(paths, name), data)
        else:
            _set_env(os.path.join(paths.config(name), ".env"), setting["name"], value)
        enabled = record["enabled"]
    message = "Set %s %s%s" % (name, setting["name"], " (secret)" if setting["secret"] else " = " + value)
    if not enabled:
        print("%s; it applies at the next 'nesti /plugin enable %s'." % (message, name))
        return
    print("%s; re-enabling %s." % (message, name))
    cmd_enable(paths, docker, name)  # takes the lock itself: flock is not re-entrant


def _read_value(prompt: str) -> str:
    try:
        return getpass.getpass(prompt) if sys.stdin.isatty() else sys.stdin.readline().rstrip("\r\n")
    except EOFError:
        return ""


def _deactivate(paths: Paths, docker: Docker, registry: Dict[str, Any], name: str) -> None:
    """Unpublish first, then stop services; a failed stop stays recorded as an error."""
    record = registry["packages"][name]
    record.update(enabled=False, bindings=[], subscriptions=[], context_digest=None, error=None)
    _save(paths, registry)
    _rmtree(paths.secrets(name))
    if record["kind"] == "service":
        note = _stop_project(docker, record["service"]["project"])
        if note:
            record["error"] = "disabled%s" % note
            _save(paths, registry)
            raise PluginError(record["error"])


def cmd_disable(paths: Paths, docker: Docker, name: str) -> None:
    """Remove bindings and subscriptions for new jobs, then stop services."""
    with _locked(paths):
        registry = load_registry(paths)
        _record(registry, name)
        _deactivate(paths, docker, registry, name)
    print("Disabled %s." % name)


def cmd_remove(paths: Paths, docker: Docker, name: str) -> None:
    """Disable, remove containers, sources and the record; settings and volumes stay."""
    with _locked(paths):
        registry = load_registry(paths)
        record = _record(registry, name)
        _deactivate(paths, docker, registry, name)
        if record["kind"] == "service":
            docker.remove([n for n, _, _ in docker.containers(record["service"]["project"])])
        _rmtree(paths.package(name))
        _rmtree(paths.work(name))
        del registry["packages"][name]
        _save(paths, registry)
    print("Removed %s. Kept settings in %s and any Docker volumes." % (name, paths.config(name)))


def cmd_update(paths: Paths, docker: Docker, name: str, ref: Optional[str], trust: bool) -> None:
    """Prepare a tag/commit or default HEAD, then switch; failures keep or restore the running revision."""
    if ref is not None:
        check_ref(ref)
    with _locked(paths):
        registry = load_registry(paths)
        record = _record(registry, name)
        old_sha = record["sha"]
        scratch, checkout, sha = _fetch(paths, record["url"], ref)
        if ref is None:
            ref = sha
        try:
            if sha == old_sha:
                if ref != record["ref"]:
                    record["ref"] = ref
                    _save(paths, registry, enabling=record["enabled"])
                print("%s is already at %s (ref %s); nothing to update." % (name, sha, ref))
                return
            info = inspect_package(checkout, record["source"])
            if info["name"] != name or info["kind"] != record["kind"]:
                raise PluginError("revision %s is the %s package %r, not the %s package %r"
                                  % (sha, info["kind"], info["name"], record["kind"], name))
            if os.path.lexists(paths.package(name, sha)) or os.path.lexists(paths.work(name, sha)):
                raise PluginError("%s exists without a registry record; remove it first" % paths.package(name, sha))
            os.replace(checkout, paths.package(name, sha))
        finally:
            _rmtree(scratch)
        new_dir = paths.package(name, sha)
        try:
            if record["kind"] == "service":
                _trust_and_prepare(paths, docker, info, record["source"], ref, sha, trust)
                if record["enabled"]:
                    _settings(paths, name, info["manifest"])
            bindings = _compile_bindings(paths, registry, name, info, new_dir) if record["enabled"] else []
        except BaseException:
            _rmtree(new_dir)
            _rmtree(paths.work(name, sha))
            raise
        subscriptions, digest = [], None
        if record["enabled"] and record["kind"] == "service":
            record.update(enabled=False, bindings=[], subscriptions=[], context_digest=None)
            _save(paths, registry)
            _rmtree(paths.secrets(name))
            try:
                try:
                    subscriptions, digest = _activate(paths, docker, registry, name, sha, info)
                except PluginError as exc:
                    _restore(paths, docker, registry, name, old_sha, sha, str(exc))
            except PluginError:
                raise
            except BaseException:  # e.g. Ctrl-C during readiness: drop the unrecorded revision, keep subscriptions off
                _rmtree(new_dir)
                _rmtree(paths.work(name, sha))
                record.update(enabled=False, bindings=[], subscriptions=[],
                              error="update to %s was interrupted; disabled at %s, service state unknown" % (sha, old_sha))
                _save(paths, registry)
                raise
            record["enabled"] = True
        record.update(ref=ref, sha=sha, skills=info["skills"], bindings=bindings, subscriptions=subscriptions,
                      context_digest=digest, error=None, updated_at=_now(),
                      trusted_sha=sha if record["kind"] == "service" else None)
        _save(paths, registry, enabling=record["enabled"])
        _rmtree(paths.package(name, old_sha))
        _rmtree(paths.work(name, old_sha))
        _rmdir_empty(paths.work(name))
    print("Updated %s to %s (ref %s)%s." % (name, sha, ref, "" if record["enabled"] else "; it stays disabled"))
    _print_settings(paths, name, info, paths.package(name, sha))


def _restore(paths: Paths, docker: Docker, registry: Dict[str, Any], name: str, old_sha: str, sha: str,
             failure: str) -> None:
    """Bring the previous revision back after a failed activation; always raises."""
    record = registry["packages"][name]
    try:
        old_dir = paths.package(name, old_sha)
        old_info = inspect_package(old_dir, record["source"])
        old_bindings = _compile_bindings(paths, registry, name, old_info, old_dir)
        old_subscriptions, old_digest = _activate(paths, docker, registry, name, old_sha, old_info)
    except PluginError as exc:
        record["error"] = "update to %s failed: %s; restoring %s failed: %s" % (sha, failure, old_sha, exc)
        _save(paths, registry)
        raise PluginError(record["error"]) from exc
    finally:
        _rmtree(paths.package(name, sha))
        _rmtree(paths.work(name, sha))
    record.update(enabled=True, bindings=old_bindings, subscriptions=old_subscriptions, context_digest=old_digest,
                  error=None)
    _save(paths, registry, enabling=True)
    raise PluginError("update to %s failed: %s; restored %s" % (sha, failure, old_sha))


def _service_state(docker: Docker, project: str) -> str:
    try:
        containers = docker.containers(project)
    except PluginError as exc:
        return "unknown (%s)" % exc
    if not containers:
        return "not created"
    running = sum(1 for _, state, _ in containers if state == "running")
    if running == 0:
        return "stopped"
    return "%s %d/%d" % ("running" if running == len(containers) else "partly running", running, len(containers))


def cmd_list(paths: Paths, docker: Docker) -> None:
    """Installed packages with source, ref, SHA, activation and real service state."""
    registry = load_registry(paths)
    if not registry["packages"]:
        print("No plugins installed.")
        return
    for name in sorted(registry["packages"]):
        record = registry["packages"][name]
        print("%s  %s  %s" % (name, record["kind"], "enabled" if record["enabled"] else "disabled"))
        print("  source:   %s" % record["source"])
        print("  revision: %s (ref %s)" % (record["sha"], record["ref"]))
        bound = dict((b["skill"], b["phases"]) for b in record.get("bindings", []))
        for skill in record.get("skills", []):
            notes = (["main"] if skill.get("main") else []) + bound.get(skill["name"], [])
            print("  skill:    %s%s" % (skill["name"], " (%s)" % ", ".join(notes) if notes else ""))
        if record["kind"] == "service":
            print("  service:  %s" % _service_state(docker, record["service"]["project"]))
        print("  config:   %s" % paths.config(name))
        if record.get("error"):
            print("  error:    %s" % record["error"])
        note = stale_note(paths, registry, name)
        if note:
            print("  stale:    %s" % note)


def plugin_overview(paths: Paths) -> List[Dict[str, Any]]:
    """Read only declared settings for display; never return secret values."""
    registry = load_registry(paths)
    entries = []
    for name in sorted(registry["packages"]):
        record = registry["packages"][name]
        entry = {"name": name, "kind": record["kind"], "enabled": record["enabled"],
                 "error": record.get("error"), "settings": []}
        try:
            source_dir = paths.package(name, record["sha"])
            info = inspect_package(source_dir, record["source"])
            entry["settings"] = [{"name": s["name"], "text": _setting_text(paths, name, info, s),
                                  "choices": s["choices"], "secret": s["secret"]}
                                 for s in _declared_settings(source_dir, info)]
        except PluginError as exc:
            entry.update(error=str(exc), settings=[])
        if entry["error"]:
            try:
                entry["error"] = _redact(entry["error"], _read_env(os.path.join(paths.config(name), ".env")))
            except PluginError:
                entry["error"] = "cannot read plugin settings"
        entries.append(entry)
    return entries


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nesti /plugin", description="Manage Nesti plugins on this host.")
    sub = parser.add_subparsers(dest="command", metavar="command")
    for command in ("install", "update"):
        cmd = sub.add_parser(command, help="install a package snapshot" if command == "install"
                             else "update a package snapshot")
        cmd.add_argument("repo_url" if command == "install" else "name")
        cmd.add_argument("--ref", help="tag or commit; defaults to the default branch HEAD, pinned to its full SHA")
        cmd.add_argument("--trust", action="store_true", help="approve running a service revision's code")
    for command, text in (("enable", "activate"), ("disable", "deactivate"), ("remove", "uninstall (keeps settings)")):
        sub.add_parser(command, help=text).add_argument("name")
    sub.add_parser("list", help="show installed packages")
    settings = sub.add_parser("settings", help="show a plugin's settings, or set one "
                             "(also: nesti /<name> [settings | <value> | <KEY> <value>])")
    settings.add_argument("name")
    settings.add_argument("first", nargs="?")
    settings.add_argument("second", nargs="?")
    return parser


def default_root() -> str:
    """The Nesti checkout this script belongs to."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv: Optional[List[str]] = None, root: Optional[str] = None, runner: Optional[Runner] = None,
         compose: Optional[List[str]] = None) -> int:
    """CLI entry: 0 ok, 1 failed operation, 2 usage error."""
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    if not args.command:
        parser.print_help(sys.stderr)
        return 2
    paths, docker = Paths(root or default_root()), Docker(runner, compose)
    try:
        if args.command == "install":
            cmd_install(paths, docker, args.repo_url, args.ref, args.trust)
        elif args.command == "update":
            cmd_update(paths, docker, args.name, args.ref, args.trust)
        elif args.command == "list":
            cmd_list(paths, docker)
        elif args.command == "settings" and args.first is None:
            cmd_settings(paths, args.name)
        elif args.command == "settings":
            key, value = (None, args.first) if args.second is None else (args.first, args.second)
            prompted = value == "-"
            if prompted:
                value = _read_value("%s value: " % (key or args.name))
            cmd_set(paths, docker, args.name, value, key, prompted)
        else:
            {"enable": cmd_enable, "disable": cmd_disable, "remove": cmd_remove}[args.command](paths, docker, args.name)
        if args.command != "list" and not (args.command == "settings" and args.first is None):
            _print_stale(paths)
    except PluginError as exc:
        print("nesti /plugin: error: %s" % exc, file=sys.stderr)
        return 2 if isinstance(exc, UsageError) else 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
