"""
project_boost.py – Laravel Boost convention discovery and the ``.omp`` conversion.

``nesti /boost`` (and the startup hook while ``<NESTI_PROJECT_PATH>/.omp`` is
missing) runs Laravel Boost's own ``infer-conventions`` skill against the
Laravel app, driven by the active LLM provider through a bounded, read-only
ls/read/grep loop. Accepted backend patterns are recorded through Boost's
RecordRule tool inside the sandbox; SPA patterns come from Nesti's adapted
``templates/boost/spa-infer-conventions`` skill. The same provider then groups
Boost's rules, guidelines and skills into omp rules under
``<NESTI_PROJECT_PATH>/.omp``. Generated files are tracked in
``.omp/nesti-boost.json``; files a user changed or owns are never overwritten.
"""

import base64
import fcntl
import fnmatch
import hashlib
import json
import logging
import os
import re
import shutil
import sys
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import project_layout
from docker_runner import DockerRunner
from project_layout import LayoutError

logger = logging.getLogger(__name__)

SPA_SKILL_DIR = Path(__file__).resolve().parent / "templates" / "boost" / "spa-infer-conventions"
SKILL_DIRS = (".claude/skills", ".agents/skills", ".cursor/skills", ".github/skills",
              ".junie/skills", ".pi/skills")
INSTALL_SCRIPT = ("[ -f boost.json ] || printf '{\"agents\":[\"claude_code\"]}\\n' > boost.json; "
                  "php artisan boost:install --no-interaction")
COMPOSER_REQUIRE = "composer require --dev laravel/boost --no-interaction --no-progress; "
RECORD_RULE = ("php artisan boost:execute-tool 'Laravel\\Boost\\Mcp\\Tools\\RecordRule' {b64}; "
               "echo '@@NESTI@@'; ")
SEGMENT_MARK = "@@NESTI@@"
CONFIG_FILES = ("pint.json", "rector.php", "phpstan.neon", "phpstan.neon.dist", "phpstan.dist.neon")
SKIP_PATHS = ("bootstrap/cache", "public/build", "storage")
SECRET_NAMES = (".env", ".env.*", "*.pem", "*.key", "auth.json", "id_rsa*")
MANIFEST = "nesti-boost.json"
ARCHITECTURE_RULE = "project-architecture"

_MAX_TURNS = 8
_MAX_ACTIONS = 8
_MAX_OBSERVATIONS = 30_000
_MAX_LS = 300
_MAX_READ_LINES = 300
_MAX_READ_CHARS = 24_000
_MAX_GREP = 80
_MAX_GREP_BYTES = 1_000_000
_MAX_UNIT_CHARS = 3_000

_SECTION = re.compile(r"^## (?P<letter>[A-Z])\. (?P<title>.+)$", re.M)
_NEXT_SECTION = re.compile(r"^## ", re.M)
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
_GUIDELINES = re.compile(r"<laravel-boost-guidelines>(.*?)</laravel-boost-guidelines>", re.S)
_GUIDELINE_SECTION = re.compile(r"^=== (.+?) rules ===$", re.M)
_RULE_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_PROTOCOL = (
    'You run the skill above inside Nesti and cannot execute commands. Reply with ONE JSON '
    'object and nothing else. Either request evidence: `{"actions":[{"tool":"ls","path":"app",'
    '"depth":2},{"tool":"grep","pattern":"->validate(","path":"app/Http","glob":"*.php",'
    '"regex":false},{"tool":"read","path":"app/Http/Controllers/X.php","start":1,"end":120}]}` '
    '(at most 8 actions; results arrive in the next message; paths are relative to the '
    'application root). Or finish: `{"verdicts":[{"dimension":"<number and name>","verdict":'
    '"pattern|conflict|default|no_signal|tooling_owned|already_recorded","evidence":'
    '["<relative file>", "..."],"globs":["app/Http/**"],"title":"<short heading>","note":'
    '"<1-2 imperative lines>","detail":"<conflict split or reason>"}]}`. Nesti runs Steps 3–5 '
    'in yolo mode: every `pattern` citing at least 3 existing files is recorded; conflicts are '
    'reported, never recorded. `globs`, `title` and `note` are required for `pattern` only.'
)
_BUDGET_EXHAUSTED = (
    "Turn budget exhausted. Reply now with the verdicts JSON for every dimension, using the "
    "evidence you have; mark undecided dimensions no_signal."
)
_CONVERT_SYSTEM = (
    "Convert these Laravel Boost outputs into rules for the omp coding agent. omp rules are "
    "files `.omp/rules/<name>.md` with YAML frontmatter: `description` (one line the agent reads "
    "in its rule index to decide whether to open the rule), `globs` (repo-relative globs, "
    "advisory scope), `alwaysApply` (true injects the whole body into every prompt; only for "
    "short, universally relevant rules). Group related units into coherent rules, name them in "
    "kebab-case, write precise descriptions, choose globs for units that have none, and decide "
    "which skills to carry over. You may skip a unit only when it instructs tools omp does not "
    "have (Boost MCP tools: search-docs, tinker, database-query, database-schema, "
    "database-connections, application-info, browser-logs, last-error, read-log-entries, "
    "get-absolute-url). You never rewrite unit text. Reply with ONE JSON object: "
    '{"rules":[{"name","description","alwaysApply","globs":[],"units":["U1"]}],'
    '"skills":[{"name","include","reason"}],"skipped":[{"unit","reason"}]}.'
)


class BoostError(RuntimeError):
    """Boost discovery, recording or the .omp conversion failed."""


class _Unit(NamedTuple):
    id: str
    kind: str
    root: str
    globs: list[str]
    title: str
    text: str


class _RecordingLLM:
    """Forwards ``generate_plan`` and remembers every provider label that answered."""

    def __init__(self, llm) -> None:
        self._llm = llm
        self.models: list[str] = []

    def generate_plan(self, system_prompt: str, user_prompt: str,
                      messages: list[dict] | None = None) -> str:
        """Call the wrapped client and note ``last_planner_label``."""
        reply = self._llm.generate_plan(system_prompt, user_prompt, messages=messages)
        label = str(getattr(self._llm, "last_planner_label", "") or "unknown provider")
        if label not in self.models:
            self.models.append(label)
        return reply


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _text(path: Path, limit: int | None = None) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _count(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return str(json.loads(value))
        except ValueError:
            return value[1:-1]
    return value


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER.sub("", text, count=1).strip()


def _frontmatter_value(path: Path, key: str) -> str:
    match = _FRONTMATTER.match(_text(path))
    for line in match[1].splitlines() if match else []:
        if line.startswith(f"{key}:"):
            return _unquote(line[len(key) + 1:].strip())
    return ""


def _json_object(text: str) -> dict:
    """The first JSON object in *text* (code fences and prose around it are ignored)."""
    start = (text or "").find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    data, _ = json.JSONDecoder().raw_decode(text, start)
    return data


def _relative_glob(glob: object) -> bool:
    return (isinstance(glob, str) and bool(glob.strip()) and not glob.strip().startswith("/")
            and ".." not in glob)


def _groups(checklist: str) -> list[tuple[str, str]]:
    """``(letter. title, text)`` per ``## X. Title`` section of a checklist."""
    groups = []
    for head in _SECTION.finditer(checklist):
        end = _NEXT_SECTION.search(checklist, head.end())
        body = checklist[head.end():end.start() if end else len(checklist)]
        groups.append((f"{head['letter']}. {head['title'].strip()}", body.strip()))
    return groups


# ---------------------------------------------------------------------------
# Read-only discovery tools
# ---------------------------------------------------------------------------

class _ReadOnlyTools:
    """Bounded ls/read/grep inside one application root; refusals are observations."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _skipped(self, rel: str) -> bool:
        return (any(part in project_layout._PRUNE for part in rel.split("/"))
                or any(rel == s or rel.startswith(s + "/") for s in SKIP_PATHS))

    def resolve(self, rel: object) -> Path:
        """Path of *rel* inside the root; ValueError when it is refused."""
        if not isinstance(rel, str) or not rel.strip():
            raise ValueError("refused: a path must be a non-empty relative path")
        rel = rel.strip()
        if rel.startswith("/"):
            raise ValueError(f"refused: {rel} is absolute; paths are relative to the application root")
        current = self.root
        for part in Path(rel).parts:
            if part == "..":
                raise ValueError(f"refused: {rel} leaves the application root")
            current = current / part
            if current.is_symlink():
                raise ValueError(f"refused: {rel} goes through a symlink")
        relative = current.relative_to(self.root).as_posix()
        if self._skipped(relative):
            raise ValueError(f"refused: {rel} is a dependency, cache or tooling folder")
        if any(fnmatch.fnmatch(current.name, name) for name in SECRET_NAMES):
            raise ValueError(f"refused: {rel} may hold secrets")
        return current

    def _walk(self, base: Path, depth: int) -> Iterator[tuple[Path, bool]]:
        try:
            children = sorted(base.iterdir())
        except OSError:
            return
        for child in children:
            if child.is_symlink() or self._skipped(child.relative_to(self.root).as_posix()):
                continue
            is_dir = child.is_dir()
            yield child, is_dir
            if is_dir and depth > 1:
                yield from self._walk(child, depth - 1)

    def files(self, rel: str) -> list[str]:
        """Every non-skipped file below *rel*, relative to the root."""
        base = self.root / rel
        return [p.relative_to(self.root).as_posix()
                for p, is_dir in self._walk(base, 64) if not is_dir] if base.is_dir() else []

    def tree(self, rel: str, depth: int) -> str:
        """Directory tree of *rel* to *depth* levels below it, with recursive file counts."""
        base = self.root / rel
        if not base.is_dir():
            return f"{rel}/ (absent)"
        lines: list[str] = []

        def visit(path: Path, level: int, indent: str) -> int:
            index = len(lines)
            if level >= 0:
                lines.append("")
            files = sum(visit(child, level - 1, indent + "  ") if is_dir else 1
                        for child, is_dir in self._walk(path, 1))
            if level >= 0:
                lines[index] = f"{indent}{rel if path == base else path.name}/ ({_count(files, 'file')})"
            return files

        visit(base, depth, "")
        return "\n".join(lines)

    def ls(self, path: str = ".", depth: int = 1) -> str:
        """List entries below *path* (directories end with ``/``)."""
        base = self.resolve(path)
        if not base.is_dir():
            return f"{path}: not a directory"
        lines = []
        for child, is_dir in self._walk(base, min(max(int(depth), 1), 3)):
            if len(lines) == _MAX_LS:
                lines.append(f"… truncated at {_MAX_LS} entries")
                break
            lines.append(child.relative_to(self.root).as_posix() + ("/" if is_dir else ""))
        return "\n".join(lines) or "(empty)"

    def read(self, path: str, start: int = 1, end: int | None = None) -> str:
        """Line-numbered text of *path* (at most 300 lines and 24 000 characters)."""
        target = self.resolve(path)
        if not target.is_file():
            return f"{path}: not a file"
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        first = max(int(start), 1)
        last = min(int(end) if end is not None else len(lines), first + _MAX_READ_LINES - 1, len(lines))
        body = "\n".join(f"{n}: {lines[n - 1]}" for n in range(first, last + 1))
        return f"{path} lines {first}-{last} of {len(lines)}:\n{body[:_MAX_READ_CHARS]}"

    def grep(self, pattern: str, path: str = ".", glob: str = "*", regex: bool = False) -> str:
        """``file:line: text`` matches of *pattern* (literal unless *regex*), at most 80."""
        base = self.resolve(path)
        if not isinstance(pattern, str) or not pattern:
            return "grep: empty pattern"
        compiled = re.compile(pattern) if regex is True else None
        candidates = [base] if base.is_file() else [p for p, is_dir in self._walk(base, 64) if not is_dir]
        matches: list[str] = []
        for file in candidates:
            rel = file.relative_to(self.root).as_posix()
            if not (fnmatch.fnmatch(file.name, glob) or fnmatch.fnmatch(rel, glob)):
                continue
            if any(fnmatch.fnmatch(file.name, name) for name in SECRET_NAMES):
                continue
            try:
                if file.stat().st_size > _MAX_GREP_BYTES:
                    continue
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                if compiled.search(line) if compiled else pattern in line:
                    matches.append(f"{rel}:{n}: {line.strip()[:200]}")
                    if len(matches) == _MAX_GREP:
                        return "\n".join(matches) + f"\n… stopped at {_MAX_GREP} matches"
        return "\n".join(matches) or "no matches"

    def run(self, actions: list) -> str:
        """Execute up to 8 actions; the observations for the next turn (≤30 000 chars)."""
        tools = {"ls": self.ls, "read": self.read, "grep": self.grep}
        out = []
        for action in actions[:_MAX_ACTIONS]:
            if not isinstance(action, dict) or action.get("tool") not in tools:
                result = "refused: an action is an object whose tool is ls, read or grep"
            else:
                try:
                    result = tools[action["tool"]](**{k: v for k, v in action.items() if k != "tool"})
                except (TypeError, ValueError, OSError, re.error) as exc:
                    result = f"error: {exc}"
            out.append(f"### {json.dumps(action, ensure_ascii=False)}\n{result}")
        if len(actions) > _MAX_ACTIONS:
            out.append(f"Only the first {_MAX_ACTIONS} actions were executed.")
        text = "\n\n".join(out) or "No actions were requested."
        return text if len(text) <= _MAX_OBSERVATIONS else text[:_MAX_OBSERVATIONS] + "\n… observations truncated"


# ---------------------------------------------------------------------------
# Boost installation and discovery
# ---------------------------------------------------------------------------

def _find_skills(backend: Path) -> Path | None:
    for rel in SKILL_DIRS:
        if (backend / rel / "infer-conventions" / "SKILL.md").is_file():
            return backend / rel
    return None


def _boost_version(backend: Path) -> str:
    data = project_layout._read_json(backend / "vendor" / "composer" / "installed.json")
    packages = data.get("packages") if isinstance(data.get("packages"), list) else []
    return next((str(p.get("version", "")) for p in packages
                 if isinstance(p, dict) and p.get("name") == "laravel/boost"), "")


def _ensure_boost(backend: Path) -> tuple[Path, str]:
    """The Boost skills dir holding ``infer-conventions`` and the Boost version; installs Boost."""
    installed = (backend / "vendor" / "laravel" / "boost" / "composer.json").is_file()
    if not installed or _find_skills(backend) is None:
        script = "set -e; " + ("" if installed else COMPOSER_REQUIRE) + INSTALL_SCRIPT
        ok, output = DockerRunner().run_boost_script(str(backend), script, network=True)
        if not ok:
            raise BoostError(f"Boost installation failed: {output[-3000:]}")
    skills = _find_skills(backend)
    if skills is None:
        raise BoostError('infer-conventions skill not installed: add it to boost.json "skills" '
                         "and run php artisan boost:update")
    return skills, _boost_version(backend)


def _backend_orientation(tools: _ReadOnlyTools, layout: dict) -> str:
    backend = tools.root
    facts = "This is the Laravel API."
    if layout["frontend"] not in (None, "."):
        facts += (f" The SPA in `{layout['frontend']}/` is analysed separately; "
                  "do not look for Vue code here.")
    parts = [f"## Layout\n{facts}", f"## composer.json\n{_text(backend / 'composer.json', 8000)}"]
    parts += [f"## {name}\n{_text(backend / name, 4000)}" for name in CONFIG_FILES if (backend / name).is_file()]
    rules_dir = backend / ".ai" / "rules"
    rule_files = sorted(rules_dir.rglob("*.md"), key=lambda p: (p.name != "index.md", p.as_posix())) \
        if rules_dir.is_dir() else []
    rules = "\n\n".join(f"### .ai/rules/{p.relative_to(rules_dir).as_posix()}\n{_text(p)}" for p in rule_files)
    parts.append(f"## Already recorded (.ai/rules)\n{rules[:12000] or 'none'}")
    parts.append(f"## app/ tree\n{tools.tree('app', 3)}")
    parts.append("## routes/ files\n" + ("\n".join(tools.files("routes")) or "none"))
    parts.append(f"## tests/ tree\n{tools.tree('tests', 2)}\n\n## database/ tree\n{tools.tree('database', 2)}")
    return "\n\n".join(parts)


def _spa_orientation(tools: _ReadOnlyTools, layout: dict) -> str:
    spa = tools.root
    parts = [f"## Layout\nThis is the Vue single-page application in `{layout['frontend']}/`. The "
             f"Laravel API in `{layout['backend']}/` is analysed separately; the SPA reaches it over HTTP only."]
    configs = ["package.json", "tsconfig.json", *sorted(p.name for p in spa.glob("vite.config.*"))]
    parts += [f"## {name}\n{_text(spa / name, 8000)}" for name in configs if (spa / name).is_file()]
    parts.append(f"## src/ tree\n{tools.tree('src', 3)}")
    parts += [f"## {name}\n{_text(spa / name, 8000)}" for name in ("src/main.ts", "src/main.js")
              if (spa / name).is_file()]
    tests = tools.files("e2e") + [f for f in tools.files(".")
                                  if not f.startswith("e2e/") and (".spec." in f or ".test." in f)]
    parts.append("## e2e/ and test files\n" + ("\n".join(tests) or "none"))
    return "\n\n".join(parts)


def _discover(llm, system: str, orientation: str, title: str, text: str,
              tools: _ReadOnlyTools, progress: Callable[[str], None]) -> tuple[list[dict], bool]:
    """Run one checklist group as a fresh bounded conversation; ``(verdicts, complete)``."""
    history = [{"role": "user", "content": f"{orientation}\n\n## Your assignment: {title}\n\n{text}\n\n"
                "Return a verdict for every numbered dimension of this assignment."}]
    for turn in range(1, _MAX_TURNS + 2):
        reply = llm.generate_plan(system, "", messages=history)
        history.append({"role": "assistant", "content": reply})
        try:
            data, error = _json_object(reply), 'neither "actions" nor "verdicts"'
        except ValueError as exc:
            data, error = {}, str(exc)
        if isinstance(data.get("verdicts"), list):
            verdicts = [v for v in data["verdicts"] if isinstance(v, dict)]
            kinds = [v.get("verdict") for v in verdicts]
            progress(f"{title} — {_count(turn, 'turn')}, {_count(kinds.count('pattern'), 'pattern')}, "
                     f"{_count(kinds.count('conflict'), 'conflict')}")
            return verdicts, True
        if turn > _MAX_TURNS:
            break
        if turn == _MAX_TURNS:
            message = _BUDGET_EXHAUSTED
        elif isinstance(data.get("actions"), list):
            message = tools.run(data["actions"])
        else:
            message = f"Your reply was not valid JSON ({error}). Reply with one JSON object."
        history.append({"role": "user", "content": message})
    progress(f"{title} — {_count(_MAX_TURNS + 1, 'turn')}, incomplete")
    return [], False


def _pattern_problem(verdict: dict, tools: _ReadOnlyTools) -> str | None:
    title, note, globs, evidence = (verdict.get(k) for k in ("title", "note", "globs", "evidence"))
    if not isinstance(title, str) or not title.strip() or "\n" in title.strip() or len(title.strip()) > 120:
        return "title must be one line of at most 120 characters"
    if not isinstance(note, str) or not note.strip() or len(note.strip()) > 600:
        return "note must hold 1-600 characters"
    if not isinstance(globs, list) or not 1 <= len(globs) <= 4 or not all(_relative_glob(g) for g in globs):
        return "globs must hold 1-4 relative globs without '..' or a leading '/'"
    files = set()
    for item in evidence if isinstance(evidence, list) else []:
        try:  # "file:12" and "file:12-30" cite lines of a file
            path = tools.resolve(re.sub(r":\d+(?:-\d+)?$", "", str(item)))
        except ValueError:
            continue
        if path.is_file():
            files.add(path)
    if len(files) < 3:
        return f"evidence names {_count(len(files), 'existing file')}; at least 3 are required"
    return None


def _classify(verdicts: list[dict], tools: _ReadOnlyTools) -> tuple[list[dict], list[dict], list[dict]]:
    """Split verdicts into accepted patterns, conflicts and rejected patterns."""
    patterns, conflicts, rejected = [], [], []
    for verdict in verdicts:
        if verdict.get("verdict") == "conflict":
            conflicts.append(verdict)
        elif verdict.get("verdict") == "pattern":
            problem = _pattern_problem(verdict, tools)
            if problem:
                rejected.append({**verdict, "reason": problem})
            else:
                patterns.append({**verdict, "title": verdict["title"].strip(), "note": verdict["note"].strip(),
                                 "globs": [g.strip() for g in verdict["globs"]]})
    return patterns, conflicts, rejected


def _sweep(llm, side: str, system: str, orientation: str, groups: list[tuple[str, str]],
           tools: _ReadOnlyTools, progress: Callable[[str], None]) -> dict:
    found: dict = {"patterns": [], "conflicts": [], "rejected": [], "incomplete": []}
    for index, (title, text) in enumerate(groups, 1):
        def prefixed(line: str) -> None:
            progress(f"[{side} {index}/{len(groups)}] {line}")

        verdicts, complete = _discover(llm, system, orientation, title, text, tools, prefixed)
        patterns, conflicts, rejected = _classify(verdicts, tools)
        found["patterns"] += patterns
        found["conflicts"] += conflicts
        found["rejected"] += rejected
        if not complete:
            found["incomplete"].append(title)
    return found


# ---------------------------------------------------------------------------
# Boost rules (.ai/rules) and RecordRule
# ---------------------------------------------------------------------------

def _parse_rule_file(text: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Frontmatter ``paths:`` globs and ``## title`` entries of a Boost rule file."""
    globs: list[str] = []
    match = _FRONTMATTER.match(text)
    if match:
        in_paths = False
        for line in match[1].splitlines():
            if not line.startswith((" ", "-")):
                in_paths = line.startswith("paths:")
            elif in_paths and line.strip().startswith("- "):
                globs.append(_unquote(line.strip()[2:].strip()))
        text = text[match.end():]
    pieces = re.split(r"^## (.+)$", text, flags=re.M)
    return globs, [(pieces[i].strip(), pieces[i + 1].strip()) for i in range(1, len(pieces), 2)]


def _rule_entries(backend: Path) -> list[tuple[list[str], str, str]]:
    """``(globs, title, text)`` for every entry of ``.ai/rules/**/*.md`` except index.md."""
    rules_dir = backend / ".ai" / "rules"
    entries = []
    for path in sorted(rules_dir.rglob("*.md")) if rules_dir.is_dir() else []:
        if path.name != "index.md":
            globs, sections = _parse_rule_file(_text(path))
            entries += [(globs, title, text) for title, text in sections]
    return entries


def _recorded_pairs(backend: Path) -> set[tuple[str, str]]:
    return {(glob, title) for globs, title, _ in _rule_entries(backend) for glob in globs}


def _record_backend(backend: Path, patterns: list[dict]) -> list[dict]:
    """Record accepted backend patterns through Boost's RecordRule; verify by read-back."""
    existing = _recorded_pairs(backend)
    todo: dict[tuple[str, str], str] = {}
    for pattern in patterns:
        for glob in pattern["globs"]:
            if (glob, pattern["title"]) not in existing:
                todo.setdefault((glob, pattern["title"]), pattern["note"])
    if not todo:
        return []
    script = "set -e; " + "".join(
        RECORD_RULE.format(b64=base64.b64encode(json.dumps(
            {"glob": glob, "title": title, "note": note}, ensure_ascii=False).encode()).decode())
        for (glob, title), note in todo.items())
    ok, output = DockerRunner().run_boost_script(str(backend), script, network=False)
    failed = next((s for s in output.split(SEGMENT_MARK) if '"isError":true' in s), None)
    if not ok or failed is not None:
        raise BoostError(f"Boost RecordRule failed: {(failed or output)[-3000:]}")
    after = _recorded_pairs(backend)
    missing = [f"{title} ({glob})" for glob, title in todo if (glob, title) not in after]
    if missing:
        raise BoostError("Boost did not record: " + "; ".join(missing))
    return [{"glob": glob, "title": title} for glob, title in todo]


# ---------------------------------------------------------------------------
# Conversion into .omp
# ---------------------------------------------------------------------------

def _units(backend: Path, layout: dict, spa_patterns: list[dict]) -> list[_Unit]:
    raw = [("backend-rule", layout["backend"], globs, title, text)
           for globs, title, text in _rule_entries(backend)]
    seen: set[str] = set()
    for name in ("CLAUDE.md", "AGENTS.md"):
        if not (backend / name).is_file():
            continue
        content = _text(backend / name)
        found = []
        block = _GUIDELINES.search(content)
        if block:
            heads = list(_GUIDELINE_SECTION.finditer(block[1]))
            for i, head in enumerate(heads):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(block[1])
                found.append(("backend-guideline", head[1], block[1][head.start():end].strip()))
            content = content[:block.start()] + content[block.end():]
        if content.strip():
            found.append(("backend-project-notes", f"{name} project notes", content.strip()))
        for kind, title, text in found:
            digest = _sha(text.encode())
            if digest not in seen:
                seen.add(digest)
                raw.append((kind, layout["backend"], [], title, text))
    raw += [("frontend-rule", layout["frontend"], p["globs"], p["title"], p["note"]) for p in spa_patterns]
    return [_Unit(f"U{i}", *unit) for i, unit in enumerate(raw, 1)]


def _skills(skills_dir: Path) -> list[dict]:
    return [{"name": d.name, "description": _frontmatter_value(d / "SKILL.md", "description")}
            for d in sorted(skills_dir.iterdir())
            if d.is_dir() and not d.is_symlink() and d.name != "infer-conventions"]


def _conversion_prompt(record: dict, units: list[_Unit], skills: list[dict]) -> str:
    lines = ["## Project", *(record.get("architecture") or {}).get("summary", []),
             f"Layout: {json.dumps(record['layout'])}", "", "## Units"]
    for unit in units:
        lines += [f"### {unit.id} · {unit.kind} · root {unit.root} · globs {json.dumps(unit.globs)}",
                  f"Title: {unit.title}", unit.text[:_MAX_UNIT_CHARS], ""]
    lines.append("## Skills")
    lines += [f"- {s['name']}: {s['description']}" for s in skills] or ["none"]
    return "\n".join(lines)


def _conversion_problem(data: dict, layout: dict, units: list[_Unit], skills: list[dict]) -> str | None:
    rules, chosen, skipped = data.get("rules"), data.get("skills", []), data.get("skipped", [])
    if not all(isinstance(x, list) for x in (rules, chosen, skipped)):
        return '"rules", "skills" and "skipped" must be lists'
    prefixes = tuple(f"{d}/" for d in (layout["backend"], layout["frontend"]) if d not in (None, "."))
    ids: list = []
    names: set[str] = set()
    always = 0
    for rule in rules:
        if not isinstance(rule, dict):
            return "every rule must be an object"
        name = rule.get("name")
        if not isinstance(name, str) or not _RULE_NAME.match(name) or len(name) > 60 or name == ARCHITECTURE_RULE:
            return f"invalid rule name {name!r}: kebab-case, at most 60 characters, not {ARCHITECTURE_RULE}"
        if name in names:
            return f"duplicate rule name {name!r}"
        names.add(name)
        description = rule.get("description")
        if not isinstance(description, str) or "\n" in description.strip() \
                or not 10 <= len(description.strip()) <= 250:
            return f"rule {name}: description must be one line of 10-250 characters"
        if not isinstance(rule.get("alwaysApply"), bool):
            return f"rule {name}: alwaysApply must be true or false"
        always += rule["alwaysApply"]
        globs = rule.get("globs", [])
        if not isinstance(globs, list) or len(globs) > 10 or not all(_relative_glob(g) for g in globs):
            return f"rule {name}: globs must hold at most 10 relative globs without '..'"
        if prefixes and not all(g.startswith(prefixes) for g in globs):
            return f"rule {name}: every glob must start with {' or '.join(prefixes)}"
        if not isinstance(rule.get("units"), list):
            return f"rule {name}: units must be a list of unit ids"
        ids += rule["units"]
    if always > 2:
        return "at most 2 rules may set alwaysApply"
    for item in skipped:
        if not isinstance(item, dict):
            return "every skipped entry must be an object"
        ids.append(item.get("unit"))
    known = {unit.id for unit in units}
    unknown = [i for i in ids if not isinstance(i, str) or i not in known]
    if unknown:
        return f"unknown unit ids: {unknown}"
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        return f"units used more than once: {repeated}"
    unused = [unit.id for unit in units if unit.id not in ids]
    if unused:
        return f"units neither converted nor skipped: {unused}"
    skill_names = {s["name"] for s in skills}
    for skill in chosen:
        if not isinstance(skill, dict) or skill.get("name") not in skill_names:
            return f"unknown skill {skill!r}"
    return None


def _convert(llm, record: dict, units: list[_Unit], skills: list[dict]) -> dict:
    """Ask the provider for the rule grouping; one corrective retry, then BoostError."""
    user = _conversion_prompt(record, units, skills)
    messages: list[dict] | None = None
    for _ in range(2):
        reply = llm.generate_plan(_CONVERT_SYSTEM, user, messages=messages)
        try:
            data = _json_object(reply)
            problem = _conversion_problem(data, record["layout"], units, skills)
        except ValueError as exc:
            data, problem = {}, f"no JSON object ({exc})"
        if problem is None:
            return data
        messages = [{"role": "user", "content": user}, {"role": "assistant", "content": reply},
                    {"role": "user", "content": f"Invalid: {problem}. Reply with the corrected JSON object only."}]
    raise BoostError(f"omp conversion rejected: {problem}; reply: {(reply or '')[:500]}")


def _frontmatter(description: str, globs: list[str], always: bool) -> str:
    return (f"---\ndescription: {json.dumps(description.strip(), ensure_ascii=False)}\n"
            f"globs: {json.dumps(globs, ensure_ascii=False)}\nalwaysApply: {json.dumps(always)}\n---\n\n")


def _architecture_rule(record: dict) -> str:
    layout = record["layout"]
    architecture = record.get("architecture") or {}
    backend = architecture.get("backend") or {}
    bullets = [f"Backend (Laravel API): `{layout['backend']}/` (php {backend.get('php') or 'unknown'}, "
               f"laravel/framework {backend.get('laravel') or 'unknown'})."]
    if layout["frontend"] is None:
        bullets.append("Frontend: no frontend SPA.")
    elif layout["frontend"] == ".":
        bullets.append("Frontend: Vue, integrated in the Laravel app (resources/js).")
    else:
        frontend = architecture.get("frontend") or {}
        packages = frontend.get("packages") or {}
        facts = [f"{n} {packages[n]}" for n in ("vue", "primevue", "vue-router", "pinia") if n in packages]
        facts += ["TypeScript"] if frontend.get("typescript") else []
        bullets.append(f"Frontend (Vue SPA): `{layout['frontend']}/` ({', '.join(facts) or 'no versions found'}).")
    if architecture.get("other_dirs"):
        bullets.append("Other folders (not managed by Nesti): "
                       + ", ".join(f"`{d}/`" for d in architecture["other_dirs"]) + ".")
    bullets += architecture.get("summary", [])
    if record.get("mode") == "separated":
        bullets.append("The frontend is a separate SPA: never put Vue/JS/CSS into the backend; "
                       "the SPA reaches the API over HTTP only.")
    return (_frontmatter("Project layout and architecture (generated by Nesti from layout.json)", [], True)
            + "# Project Architecture\n\n" + "\n".join(f"- {b}" for b in bullets) + "\n")


def _skill_files(source: Path, name: str) -> dict[str, bytes]:
    files = {}
    for dirpath, _, filenames in os.walk(source):
        for filename in filenames:
            path = Path(dirpath) / filename
            if not path.is_symlink():
                files[f"skills/{name}/{path.relative_to(source).as_posix()}"] = path.read_bytes()
    return files


def _render(record: dict, units: list[_Unit], conversion: dict, skills_dir: Path,
            boost_version: str, models: list[str]) -> dict[str, bytes]:
    """Every generated ``.omp`` file (relative path → bytes); the manifest carries metadata only."""
    files = {f"rules/{ARCHITECTURE_RULE}.md": _architecture_rule(record).encode()}
    by_id = {unit.id: unit for unit in units}
    for rule in conversion["rules"]:
        members = [by_id[i] for i in rule["units"]]
        globs = list(dict.fromkeys([*rule.get("globs", []), *(
            glob if unit.root == "." else f"{unit.root}/{glob}" for unit in members for glob in unit.globs)]))
        body = [f"# {rule['name'].replace('-', ' ').title()}"]
        body += [f"## {u.title}\n{u.text}" if u.kind.endswith("-rule") else u.text for u in members]
        files[f"rules/{rule['name']}.md"] = (
            _frontmatter(rule["description"], globs, rule["alwaysApply"]) + "\n\n".join(body) + "\n").encode()
    for skill in conversion.get("skills", []):
        if skill.get("include") is True:
            files.update(_skill_files(skills_dir / skill["name"], skill["name"]))
    files[MANIFEST] = json.dumps({
        "schema": 1, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "boost_version": boost_version, "models": models}).encode()
    return files


# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------

def _owned(rel: object) -> bool:
    return (isinstance(rel, str) and not rel.startswith("/") and ".." not in rel.split("/")
            and rel.split("/")[0] in ("rules", "skills"))


def _write(base: Path, rel: str, data: bytes, ref: Path) -> None:
    directory = base
    for part in rel.split("/")[:-1]:
        directory = directory / part
        if not directory.is_dir():
            directory.mkdir()
            project_layout._adopt(directory, ref)
    path = base / rel
    tmp = path.with_name(path.name + ".nesti-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    project_layout._adopt(path, ref)


def _manifest(meta: dict, files: dict[str, bytes]) -> bytes:
    data = {"schema": 1, **meta, "files": {rel: _sha(body) for rel, body in files.items()}}
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()


def _publish(root: Path, files: dict[str, bytes]) -> dict:
    """Write *files* into ``root/.omp``; never touch user-modified or user-owned files."""
    omp = root / ".omp"
    if omp.is_symlink() or (omp.exists() and not omp.is_dir()):
        raise BoostError(f"{omp} is a symlink or a file; refusing to publish")
    files = dict(files)
    meta = json.loads(files.pop(MANIFEST, b"{}"))
    report: dict[str, list[str]] = {"written": [], "removed": [], "kept_user_modified": [], "conflicts": []}
    if not omp.exists():
        staging = root / ".omp.nesti-staging"
        if staging.is_symlink() or staging.is_file():
            staging.unlink()
        elif staging.exists():
            shutil.rmtree(staging)
        staging.mkdir()
        project_layout._adopt(staging, root)
        for rel, data in files.items():
            _write(staging, rel, data, root)
        _write(staging, MANIFEST, _manifest(meta, files), root)
        os.rename(staging, omp)
        report["written"] = list(files)
        return report
    previous = project_layout._read_json(omp / MANIFEST).get("files")
    previous = previous if isinstance(previous, dict) else {}
    for rel, digest in previous.items():
        path = omp / str(rel)
        if not _owned(rel) or path.is_symlink() or not path.is_file():
            continue
        if _sha(path.read_bytes()) != digest:
            report["kept_user_modified"].append(rel)
        elif rel not in files:
            path.unlink()
            directory = path.parent
            while directory not in (omp, omp / "rules", omp / "skills") and not any(directory.iterdir()):
                directory.rmdir()
                directory = directory.parent
            report["removed"].append(rel)
    for rel, data in files.items():
        path = omp / rel
        if rel in report["kept_user_modified"]:
            continue
        if rel not in previous and (path.exists() or path.is_symlink()):
            report["conflicts"].append(rel)
            continue
        _write(omp, rel, data, root)
        report["written"].append(rel)
    _write(omp, MANIFEST, _manifest(meta, {rel: files[rel] for rel in report["written"]}), root)
    return report


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_boost(root: Path, record: dict, llm, progress: Callable[[str], None] = logger.info) -> dict:
    """Run Boost discovery for *record*'s layout and rebuild ``root/.omp``; return the report."""
    state = project_layout.STATE_DIR
    state.mkdir(parents=True, exist_ok=True)
    lock_path = state / "boost.lock"
    with open(lock_path, "w", encoding="utf-8") as lock:
        project_layout._adopt(lock_path, state)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BoostError("another nesti /boost is running") from exc
        return _boost(root, record, _RecordingLLM(llm), progress)


def _boost(root: Path, record: dict, llm: _RecordingLLM, progress: Callable[[str], None]) -> dict:
    layout = record["layout"]
    if layout["backend"] is None:
        raise BoostError("greenfield project: nothing to boost until the first scaffold is merged and pulled")
    backend = root / layout["backend"]
    skills_dir, version = _ensure_boost(backend)
    progress(f"Laravel Boost {version or '(version unknown)'}: infer-conventions from {skills_dir}")

    skill_md = skills_dir / "infer-conventions" / "SKILL.md"
    skill = _strip_frontmatter(_text(skill_md))
    groups = _groups(_text(skill_md.parent / "references" / "checklist.md"))
    start = skill.find("### Step 2")
    if start >= 0:
        end = skill.find("\n### ", start + 1)
        groups.append(("Architecture & house patterns", skill[start:end if end >= 0 else len(skill)].strip()))
    tools = _ReadOnlyTools(backend)
    back = _sweep(llm, "backend", f"{skill}\n\n{_PROTOCOL}", _backend_orientation(tools, layout),
                  groups, tools, progress)
    recorded = _record_backend(backend, back["patterns"])

    front: dict = {"patterns": [], "conflicts": [], "rejected": [], "incomplete": []}
    if layout["frontend"] not in (None, "."):
        spa_tools = _ReadOnlyTools(root / layout["frontend"])
        spa_skill = _strip_frontmatter(_text(SPA_SKILL_DIR / "SKILL.md"))
        front = _sweep(llm, "frontend", f"{spa_skill}\n\n{_PROTOCOL}", _spa_orientation(spa_tools, layout),
                       _groups(_text(SPA_SKILL_DIR / "references" / "checklist.md")), spa_tools, progress)

    units = _units(backend, layout, front["patterns"])
    skills = _skills(skills_dir)
    conversion = _convert(llm, record, units, skills)
    published = _publish(root, _render(record, units, conversion, skills_dir, version, llm.models))
    progress(f".omp: {_count(len(published['written']), 'file')} written, {len(published['removed'])} removed, "
             f"{len(published['kept_user_modified'])} kept, {len(published['conflicts'])} conflicts")
    project_layout.refresh_architecture(record)
    return {
        "layout": layout, "boost_version": version,
        "backend": {"recorded": recorded, "conflicts": back["conflicts"], "rejected": back["rejected"],
                    "incomplete": back["incomplete"]},
        "frontend": front, "omp": published, "skipped_units": conversion.get("skipped", []),
        "skills": [s["name"] for s in conversion.get("skills", []) if s.get("include") is True],
        "models": llm.models,
    }


def cli_boost(args: list[str]) -> int:
    """``nesti /boost``: run discovery and rebuild ``<NESTI_PROJECT_PATH>/.omp``; the exit code."""
    if args:
        print("Usage: nesti /boost")
        return 2
    try:
        from llm_client import LLMClient

        root = project_layout.project_root()
        record = project_layout.ensure_layout(root)
        report = run_boost(root, record, LLMClient(), progress=print)
    except (LayoutError, BoostError, RuntimeError) as exc:
        print(f"Boost failed: {exc}", file=sys.stderr)
        return 1
    omp = report["omp"]
    sides = ("backend", "frontend")
    sections = [
        ("Recorded backend rules", [f"{r['title']} ({r['glob']})" for r in report["backend"]["recorded"]]),
        ("Conflicts (reported, never recorded)",
         [f"[{side}] {c.get('dimension', '?')}: {c.get('detail', '')}" for side in sides
          for c in report[side]["conflicts"]]),
        ("Incomplete groups", [f"[{side}] {title}" for side in sides for title in report[side]["incomplete"]]),
        (".omp written", omp["written"]),
        (".omp removed", omp["removed"]),
        (".omp kept (modified by you)", omp["kept_user_modified"]),
        (".omp conflicts (not generated by Nesti, left untouched)", omp["conflicts"]),
        ("Models used", report["models"]),
    ]
    for title, items in sections:
        print(f"{title}:" + ("" if items else " none"))
        for item in items:
            print(f"  - {item}")
    print("Restart your omp session (/new) to load the refreshed .omp rules and skills.")
    return 0
