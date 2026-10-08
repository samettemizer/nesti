"""
e2e_fixtures.py – the E2E fixture contract shared by the Playwright runner, the
sandbox helper (scripts/e2e_fixtures.php) and the dependency workflow
(issue_dependencies.py).  Pure Python: no network, no Docker, no Laravel.

Declared requirement
────────────────────
A generated change may commit ``e2e/nesti-fixtures.json``:

    {"version": 1, "fixtures": [{"endpoint": "/api/tasks",
                                 "model": "App\\\\Models\\\\Task",
                                 "seeder": "Database\\\\Seeders\\\\TaskSeeder"}]}

Each entry means "this existing unauthenticated GET collection needs at least
one real record before the browser specs run".  Absence, or an empty fixture
list, requests no special data handling.  The sandbox helper re-validates the
same rules before it touches the application, so a direct image invocation is
held to the same contract.

Result transport
────────────────
The helper writes ONE bounded JSON report to ``/nesti-results/fixtures.json``
(a directory mounted from outside the generated repository) and exits:

    0   after a {"version": 1, "status": "ready"} report
    78  after a {"version": 1, "status": "missing_seeder", "requirement": {...}}
        report for a declared seeder whose class and conventional file are absent
    1   for every other preparation or contract error (no dependency)

``read_fixture_report`` accepts a report only when its status agrees with the
container's exit code and its requirement matches a declaration exactly; any
other combination is an ordinary test failure.

Durable dependency record
─────────────────────────
A paused parent issue carries a GitLab note whose first line is
``NESTI_FIXTURE_DEPENDENCIES_V1`` followed by human-readable child references
and one ```json fenced block.  A child issue's description carries one
``<!-- NESTI_FIXTURE_CHILD_V1 {...} -->`` ownership marker.  Both are keyed by
``dependency_key`` — a SHA-256 over canonical JSON of the project, the parent,
the target branch and the requirement, never over a changing clone SHA.
"""

import hashlib
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Declared requirement ──────────────────────────────────────────────────────
MANIFEST_PATH = "e2e/nesti-fixtures.json"
MANIFEST_MAX_BYTES = 32 * 1024
MAX_FIXTURES = 16
MAX_NAME_CHARS = 512
MODEL_PREFIX = "App\\Models\\"
SEEDER_PREFIX = "Database\\Seeders\\"

# ── Result transport ──────────────────────────────────────────────────────────
RESULTS_MOUNT = "/nesti-results"
REPORT_FILENAME = "fixtures.json"
REPORT_MAX_BYTES = 4 * 1024
EXIT_MISSING_SEEDER = 78
STATUS_READY = "ready"
STATUS_MISSING_SEEDER = "missing_seeder"

# ── Durable dependency record ─────────────────────────────────────────────────
DEPENDENCY_NOTE_MARKER = "NESTI_FIXTURE_DEPENDENCIES_V1"
CHILD_MARKER = "NESTI_FIXTURE_CHILD_V1"
ITEM_STATES = ("creating", "waiting", "merged", "blocked")
MAX_DEPENDENCY_ITEMS = 64
MAX_REASON_CHARS = 1000
MAX_BRANCH_CHARS = 255

_ENDPOINT_RE = re.compile(r"^/api(/[A-Za-z0-9._~-]+)+$")
_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\\[A-Za-z_][A-Za-z0-9_]*)+$")
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_NOTE_JSON_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
_CHILD_MARKER_RE = re.compile(r"<!-- " + CHILD_MARKER + r" (.*?) -->", re.DOTALL)

_REQUIREMENT_FIELDS = frozenset({"endpoint", "model", "seeder"})
_REPORT_REQUIREMENT_FIELDS = frozenset({"endpoint", "model", "seeder", "table"})
_STATE_FIELDS = frozenset({"version", "project_id", "release_pending", "items"})
_ITEM_FIELDS = frozenset({
    "key", "state", "requirement", "base_sha", "target_branch", "child_iid",
    "creation_submitted", "mr_iid", "merge_sha", "reason",
})
_CHILD_FIELDS = frozenset({
    "version", "key", "project_id", "parent_iid", "target_branch", "requirement",
})


# ─────────────────────────────────────────────────────────────────────────────
# Shared validation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _reject_duplicate_keys(pairs: list) -> dict:
    """json object_pairs_hook: a repeated key is ambiguous, never last-wins."""
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _loads(text: str):
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def _canonical(value) -> str:
    """Deterministic compact JSON: the same value always serialises identically."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_int(value, label: str) -> int:
    if not _is_int(value) or value <= 0:
        raise ValueError(f"{label} must be a positive integer, got {value!r}")
    return value


def _optional_positive_int(value, label: str) -> int | None:
    return None if value is None else _positive_int(value, label)


def _class_name(value, prefix: str, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_NAME_CHARS:
        raise ValueError(f"{label} must be a class name of at most {MAX_NAME_CHARS} characters")
    if not value.startswith(prefix) or len(value) == len(prefix):
        raise ValueError(f"{label} {value!r} must start with {prefix!r}")
    if not _CLASS_RE.match(value):
        raise ValueError(f"{label} {value!r} is not an ASCII namespaced class name")
    return value


def _endpoint(value) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_NAME_CHARS:
        raise ValueError(f"endpoint must be a path of at most {MAX_NAME_CHARS} characters")
    if not _ENDPOINT_RE.match(value):
        raise ValueError(
            f"endpoint {value!r} must be a local /api path (no URL, query or fragment)"
        )
    if any(segment in (".", "..") for segment in value.split("/")):
        raise ValueError(f"endpoint {value!r} must not contain '.' or '..' segments")
    return value


def _table(value) -> str:
    if not isinstance(value, str) or len(value) > MAX_NAME_CHARS or not _TABLE_RE.match(value):
        raise ValueError(f"table {value!r} is not a supported table identifier")
    return value


def validate_requirement(entry, *, with_table: bool = False) -> dict:
    """
    Validate one fixture requirement and return a clean copy.

    Manifest entries carry exactly ``endpoint``/``model``/``seeder``; a report
    or a dependency record additionally carries the ``table`` the helper
    derived from the model.  Raises ValueError on anything else.
    """
    expected = _REPORT_REQUIREMENT_FIELDS if with_table else _REQUIREMENT_FIELDS
    if not isinstance(entry, dict):
        raise ValueError("a fixture requirement must be a JSON object")
    if set(entry) != expected:
        raise ValueError(f"a fixture requirement has exactly the fields {sorted(expected)}")
    clean = {
        "endpoint": _endpoint(entry["endpoint"]),
        "model": _class_name(entry["model"], MODEL_PREFIX, "model"),
        "seeder": _class_name(entry["seeder"], SEEDER_PREFIX, "seeder"),
    }
    if with_table:
        clean["table"] = _table(entry["table"])
    return clean


def requirement_tuple(requirement: dict) -> tuple[str, str, str]:
    """The identity a report must match: endpoint, model and seeder."""
    return requirement["endpoint"], requirement["model"], requirement["seeder"]


# ─────────────────────────────────────────────────────────────────────────────
# Declared requirement (e2e/nesti-fixtures.json)
# ─────────────────────────────────────────────────────────────────────────────

def parse_manifest(data) -> list[dict]:
    """Validate a decoded manifest document; raises ValueError."""
    if not isinstance(data, dict) or set(data) != {"version", "fixtures"}:
        raise ValueError('the manifest is an object with exactly "version" and "fixtures"')
    if not _is_int(data["version"]) or data["version"] != 1:
        raise ValueError(f"unsupported manifest version {data['version']!r} (expected 1)")
    fixtures = data["fixtures"]
    if not isinstance(fixtures, list):
        raise ValueError('"fixtures" must be a list')
    if len(fixtures) > MAX_FIXTURES:
        raise ValueError(f"at most {MAX_FIXTURES} fixtures may be declared, got {len(fixtures)}")

    requirements: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for index, entry in enumerate(fixtures):
        try:
            requirement = validate_requirement(entry)
        except ValueError as exc:
            raise ValueError(f"fixtures[{index}]: {exc}") from None
        identity = requirement_tuple(requirement)
        if identity in seen:
            raise ValueError(f"fixtures[{index}] repeats an earlier declaration")
        seen.add(identity)
        requirements.append(requirement)
    return requirements


def load_requirements(workspace_path: str) -> list[dict]:
    """
    Read and validate the workspace's fixture manifest.

    Returns ``[]`` when the manifest is absent.  Raises ValueError for an
    oversized, non-UTF-8, non-JSON or schema-violating manifest — the runner
    reports that as an ordinary failure before any container starts.
    """
    path = Path(workspace_path) / MANIFEST_PATH
    if not path.exists() and not path.is_symlink():
        return []
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{MANIFEST_PATH} must be a regular file")
    with open(path, "rb") as handle:
        raw = handle.read(MANIFEST_MAX_BYTES + 1)
    if len(raw) > MANIFEST_MAX_BYTES:
        raise ValueError(f"{MANIFEST_PATH} exceeds {MANIFEST_MAX_BYTES} bytes")
    try:
        data = _loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ValueError(f"{MANIFEST_PATH} is not valid UTF-8 JSON: {exc}") from None
    return parse_manifest(data)


# ─────────────────────────────────────────────────────────────────────────────
# Result transport (/nesti-results/fixtures.json)
# ─────────────────────────────────────────────────────────────────────────────

def read_fixture_report(
    result_path: str, exit_code: int | None, requirements: list[dict]
) -> dict | None:
    """
    Return the helper's validated report, or None.

    A report counts only when it agrees with the container's exit code:
    ``ready`` needs exit 0; ``missing_seeder`` needs exit 78 and a requirement
    that matches a declaration exactly on endpoint/model/seeder, with a valid
    derived table.  A missing, oversized, malformed, unreadable, stale or
    mismatched report yields None — never raises — so the caller treats the
    run as an ordinary failure.
    """
    path = Path(result_path)
    try:
        if path.is_symlink() or not path.is_file():
            return None
        with open(path, "rb") as handle:
            raw = handle.read(REPORT_MAX_BYTES + 1)
        if len(raw) > REPORT_MAX_BYTES:
            logger.warning("Fixture report %s exceeds %d bytes; ignored.", path, REPORT_MAX_BYTES)
            return None
        data = _loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Fixture report %s is unreadable: %s", path, exc)
        return None

    if not isinstance(data, dict) or not _is_int(data.get("version")) or data["version"] != 1:
        logger.warning("Fixture report %s has an unsupported shape; ignored.", path)
        return None
    status = data.get("status")
    if status == STATUS_READY:
        if set(data) != {"version", "status"} or exit_code != 0:
            logger.warning("Ready fixture report does not match exit code %s; ignored.", exit_code)
            return None
        return {"version": 1, "status": STATUS_READY}
    if status == STATUS_MISSING_SEEDER:
        if set(data) != {"version", "status", "requirement"} or exit_code != EXIT_MISSING_SEEDER:
            logger.warning(
                "Missing-seeder fixture report does not match exit code %s; ignored.", exit_code
            )
            return None
        try:
            requirement = validate_requirement(data["requirement"], with_table=True)
        except ValueError as exc:
            logger.warning("Missing-seeder fixture report is invalid: %s", exc)
            return None
        declared = {requirement_tuple(entry) for entry in requirements}
        if requirement_tuple(requirement) not in declared:
            logger.warning(
                "Missing-seeder fixture report names an undeclared requirement %s; ignored.",
                requirement_tuple(requirement),
            )
            return None
        return {"version": 1, "status": STATUS_MISSING_SEEDER, "requirement": requirement}
    logger.warning("Fixture report %s has unknown status %r; ignored.", path, status)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Durable dependency record
# ─────────────────────────────────────────────────────────────────────────────

def dependency_key(project_id: int, parent_iid: int, target_branch: str, requirement: dict) -> str:
    """SHA-256 of the canonical identity of one fixture dependency."""
    payload = {
        "project_id": _positive_int(project_id, "project_id"),
        "parent_iid": _positive_int(parent_iid, "parent_iid"),
        "target_branch": _branch(target_branch),
        "requirement": validate_requirement(requirement, with_table=True),
    }
    return hashlib.sha256(_canonical(payload).encode("ascii")).hexdigest()


def _branch(value) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > MAX_BRANCH_CHARS
            or any(ch in value for ch in "\r\n\0")):
        raise ValueError(f"target_branch {value!r} is not a branch name")
    return value


def _sha(value, label: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.match(value):
        raise ValueError(f"{label} {value!r} is not a commit SHA")
    return value


def _validate_item(item, project_id: int, parent_iid: int | None) -> dict:
    if not isinstance(item, dict) or set(item) != _ITEM_FIELDS:
        raise ValueError(f"a dependency item has exactly the fields {sorted(_ITEM_FIELDS)}")
    key = item["key"]
    if not isinstance(key, str) or not _KEY_RE.match(key):
        raise ValueError(f"dependency key {key!r} is not a SHA-256 hex digest")
    state = item["state"]
    if state not in ITEM_STATES:
        raise ValueError(f"dependency state {state!r} is not one of {ITEM_STATES}")
    requirement = validate_requirement(item["requirement"], with_table=True)
    target_branch = _branch(item["target_branch"])
    child_iid = _optional_positive_int(item["child_iid"], "child_iid")
    mr_iid = _optional_positive_int(item["mr_iid"], "mr_iid")
    merge_sha = None if item["merge_sha"] is None else _sha(item["merge_sha"], "merge_sha")
    if not isinstance(item["creation_submitted"], bool):
        raise ValueError("creation_submitted must be a boolean")
    reason = item["reason"]
    if not isinstance(reason, str) or len(reason) > MAX_REASON_CHARS:
        raise ValueError(f"reason must be a string of at most {MAX_REASON_CHARS} characters")
    if state == "creating" and child_iid is not None:
        raise ValueError("a creating dependency has no child yet")
    if state in ("waiting", "merged") and child_iid is None:
        raise ValueError(f"a {state} dependency names its child issue")
    if state == "merged" and mr_iid is None:
        raise ValueError("a merged dependency names its merge request")
    if parent_iid is not None:
        expected = dependency_key(project_id, parent_iid, target_branch, requirement)
        if key != expected:
            raise ValueError("dependency key does not match its project/parent/branch/requirement")
    return {
        "key": key,
        "state": state,
        "requirement": requirement,
        "base_sha": _sha(item["base_sha"], "base_sha"),
        "target_branch": target_branch,
        "child_iid": child_iid,
        "creation_submitted": item["creation_submitted"],
        "mr_iid": mr_iid,
        "merge_sha": merge_sha,
        "reason": reason,
    }


def validate_dependency_state(state, parent_iid: int | None = None) -> dict:
    """
    Validate a dependency record and return a clean copy; raises ValueError.

    With *parent_iid* every item key is recomputed, so a record copied onto
    another issue or edited by hand fails closed instead of steering it.
    """
    if not isinstance(state, dict) or set(state) != _STATE_FIELDS:
        raise ValueError(f"a dependency record has exactly the fields {sorted(_STATE_FIELDS)}")
    if not _is_int(state["version"]) or state["version"] != 1:
        raise ValueError(f"unsupported dependency record version {state['version']!r}")
    project_id = _positive_int(state["project_id"], "project_id")
    if not isinstance(state["release_pending"], bool):
        raise ValueError("release_pending must be a boolean")
    items = state["items"]
    if not isinstance(items, list) or len(items) > MAX_DEPENDENCY_ITEMS:
        raise ValueError(f"items must be a list of at most {MAX_DEPENDENCY_ITEMS} entries")
    clean_items = [_validate_item(item, project_id, parent_iid) for item in items]
    if len({item["key"] for item in clean_items}) != len(clean_items):
        raise ValueError("a dependency record repeats a key")
    return {
        "version": 1,
        "project_id": project_id,
        "release_pending": state["release_pending"],
        "items": clean_items,
    }


def is_dependency_note(body: str) -> bool:
    """True when *body* claims to be a dependency record (its first line is the marker)."""
    lines = (body or "").lstrip().splitlines()
    return bool(lines) and lines[0].strip() == DEPENDENCY_NOTE_MARKER


def parse_dependency_note(body: str, parent_iid: int | None = None) -> dict | None:
    """
    Parse a parent issue note.

    Returns None for an ordinary note.  A note that starts with the marker but
    cannot be parsed or validated raises ValueError: the caller fails that
    issue closed rather than guessing its dependency state.
    """
    if not is_dependency_note(body):
        return None
    blocks = _NOTE_JSON_RE.findall(body.replace("\r\n", "\n"))
    if len(blocks) != 1:
        raise ValueError("a dependency record carries exactly one ```json block")
    return validate_dependency_state(_loads(blocks[0]), parent_iid=parent_iid)


def _child_reference(item: dict) -> str:
    requirement = item["requirement"]
    child = f"#{item['child_iid']}" if item["child_iid"] else "no child issue yet"
    line = (
        f"- GET `{requirement['endpoint']}` needs `{requirement['seeder']}` "
        f"(table `{requirement['table']}`): {child}, {item['state']}"
    )
    if item["mr_iid"]:
        line += f", merged by !{item['mr_iid']}"
    if item["reason"]:
        line += f" — {item['reason']}"
    return line


def format_dependency_note(state: dict) -> str:
    """Render a dependency record as its canonical note body (deterministic)."""
    clean = validate_dependency_state(state)
    lines = [
        DEPENDENCY_NOTE_MARKER,
        "Nesti keeps this issue paused until the backend dependencies below are merged. "
        "Maintained automatically; do not edit.",
        "",
    ]
    lines += [_child_reference(item) for item in clean["items"]] or ["- none"]
    if clean["release_pending"]:
        lines.append("- release in progress")
    lines += ["", "```json", _canonical(clean), "```"]
    return "\n".join(lines)


def active_dependency(state: dict | None) -> bool:
    """True while a record holds its parent: a nonmerged item or a pending release."""
    if not state:
        return False
    return bool(state["release_pending"]) or any(
        item["state"] != "merged" for item in state["items"]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Child ownership marker
# ─────────────────────────────────────────────────────────────────────────────

def format_child_marker(
    key: str, project_id: int, parent_iid: int, target_branch: str, requirement: dict
) -> str:
    """The HTML-comment ownership marker embedded in a dependency child's description."""
    payload = {
        "version": 1,
        "key": key,
        "project_id": project_id,
        "parent_iid": parent_iid,
        "target_branch": target_branch,
        "requirement": validate_requirement(requirement, with_table=True),
    }
    if dependency_key(project_id, parent_iid, target_branch, payload["requirement"]) != key:
        raise ValueError("child marker key does not match its identity")
    # "<" and ">" are escaped so no value can terminate the HTML comment early.
    body = _canonical(payload).replace("<", "\\u003c").replace(">", "\\u003e")
    return f"<!-- {CHILD_MARKER} {body} -->"


def parse_child_marker(description: str) -> dict | None:
    """
    Return the validated ownership marker of a child description.

    None when the description carries no marker; ValueError when it carries
    more than one or a marker that does not validate (key recomputed).
    """
    description = description or ""
    if CHILD_MARKER not in description:
        return None
    found = _CHILD_MARKER_RE.findall(description)
    if description.count(CHILD_MARKER) != 1 or len(found) != 1:
        raise ValueError("a description must carry one complete child ownership marker")
    data = _loads(found[0])
    if not isinstance(data, dict) or set(data) != _CHILD_FIELDS:
        raise ValueError(f"a child marker has exactly the fields {sorted(_CHILD_FIELDS)}")
    if not _is_int(data["version"]) or data["version"] != 1:
        raise ValueError(f"unsupported child marker version {data['version']!r}")
    requirement = validate_requirement(data["requirement"], with_table=True)
    project_id = _positive_int(data["project_id"], "project_id")
    parent_iid = _positive_int(data["parent_iid"], "parent_iid")
    target_branch = _branch(data["target_branch"])
    key = data["key"]
    if key != dependency_key(project_id, parent_iid, target_branch, requirement):
        raise ValueError("child marker key does not match its identity")
    return {
        "version": 1,
        "key": key,
        "project_id": project_id,
        "parent_iid": parent_iid,
        "target_branch": target_branch,
        "requirement": requirement,
    }
