"""Verified OMP escalation journals; rejected source is reference, never a patch.

CTO reports review outcomes; this service validates their sequence, not whether an
LLM actually reviewed code. Submitted POSTs are never automatically repeated.
SQLite serializes processes and commits each intent before its remote mutation.
"""

import difflib
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
from uuid import UUID

from git import Repo

from gitlab_issues_client import GitLabIssuesClient
from project_context import configured_project_root, inspect_project, project_namespace

logger = logging.getLogger(__name__)

_OWNERSHIP = "NESTI_OMP_ESCALATION_V1"
_HANDOFF = "NESTI_OMP_HANDOFF_V1"
_REFERENCE_LIMIT = 100_000
_TIMEOUT = 15
_SOURCE_SUFFIXES = {".php", ".vue", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".sass", ".less", ".html", ".json", ".yaml", ".yml", ".xml", ".md", ".mdc"}
_UNSAFE_PARTS = {".git", ".idea", "vendor", "node_modules", "storage", "logs", "cache", ".ssh"}


class _Failure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise _Failure(code, message)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: object, *, empty: bool = True) -> bool:
    return isinstance(value, list) and (empty or bool(value)) and all(_text(item) for item in value)


def _path(value: object, *, empty: bool = False) -> bool:
    return isinstance(value, str) and ((empty and value == "") or (
        bool(value) and "\\" not in value and not any(ord(c) < 32 for c in value)
        and not PurePosixPath(value).is_absolute()
        and all(part not in ("", ".", "..") for part in value.split("/"))))


def _review(review: object, number: int, verdict: str) -> None:
    if (not isinstance(review, dict) or type(review.get("round")) is not int
            or review["round"] != number or not _text(review.get("reviewer_id"))
            or review.get("verdict") != verdict or not _strings(review.get("must_fix"))
            or not _strings(review.get("tests_run"))
            or (verdict == "approve" and review["must_fix"])
            or (verdict == "changes_requested" and not review["must_fix"])
            or review.get("reviewer_id") == review.get("developer_id")):
        _fail("invalid_report", f"Expected independent round {number} {verdict} review with findings and tests_run")


def _validate_report(report: dict, *, handoff: bool = False) -> None:
    if not isinstance(report, dict):
        _fail("invalid_report", "report must be an object")
    source = report.get("source")
    if (not _text(report.get("title")) or "\n" in report["title"] or "\r" in report["title"]
            or not _text(report.get("request"))
            or not _strings(report.get("acceptance_criteria"), empty=False)
            or report.get("scope") not in ("backend", "frontend", "fullstack")
            or not isinstance(source, dict)
            or not _path(source.get("application_root"), empty=True)
            or not isinstance(source.get("head"), str)
            or re.fullmatch(r"[0-9a-fA-F]{40,64}", source["head"]) is None
            or not isinstance(source.get("local_branch"), (str, type(None)))
            or not _text(source.get("target_branch"))
            or not isinstance(report.get("changed_files"), list)
            or not all(_path(path) for path in report["changed_files"])
            or len(set(report["changed_files"])) != len(report["changed_files"])
            or not isinstance(report.get("workspace_evidence"), (dict, list))
            or not isinstance(report.get("architecture_fingerprint"), str)
            or re.fullmatch(r"[0-9a-f]{64}", report["architecture_fingerprint"]) is None):
        _fail("invalid_report", "Missing or malformed escalation requirements, source identity, paths or evidence")
    reviews = report.get("reviews")
    developer_failed = handoff and report.get("outcome") == "developer_failed"
    if not isinstance(reviews, list) or len(reviews) != (3 if handoff and not developer_failed else 2):
        _fail("invalid_report", "Creation needs exactly two rejections; handoff needs a real third failure")
    for number, review in enumerate(reviews, 1):
        _review(review, number, "changes_requested")
    if handoff:
        if (report.get("transfer_mode") != "clean_reimplementation"
                or not _text(report.get("advisor_summary"))
                or not _strings(report.get("tests_run"))):
            _fail("invalid_report", "Handoff requires advice, latest tests_run and clean_reimplementation")
        if developer_failed and (not _text(report.get("failure_output"))
                                 or report.get("failure_kind") not in ("implementation", "execution")):
            _fail("invalid_report", "Developer failure requires actual failure_output and failure_kind implementation|execution; infrastructure is not rejection")
        if not developer_failed and report.get("outcome") not in (None, "changes_requested"):
            _fail("invalid_report", "Only an actual third rejection or developer execution failure may hand off")
    try:
        serialized = _json(report)
    except (ValueError, TypeError) as exc:
        _fail("invalid_report", f"Report must contain finite JSON values: {exc}")
    if _OWNERSHIP in serialized or _HANDOFF in serialized:
        _fail("invalid_report", "Reports cannot contain reserved escalation ownership markers")


def _block(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    fence = "`" * max(3, 1 + max((len(m.group()) for m in re.finditer(r"`+", text)), default=0))
    return f"{fence}json\n{text}\n{fence}"


def _capture(project: dict, report: dict) -> dict:
    from project_architecture import collect_inventory

    root = Path(project.get("project_root") or project["root"])
    inventory = collect_inventory(str(root))
    repo = Repo(project["git_root"])
    captured: list[dict] = []
    omitted: list[dict] = []
    remaining = _REFERENCE_LIMIT
    for path in report["changed_files"]:
        parts = PurePosixPath(path).parts
        destination = root / path
        if (any(part in _UNSAFE_PARTS or part.startswith(".env") for part in parts)
                or destination.suffix.lower() not in _SOURCE_SUFFIXES
                or any((root.joinpath(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1))):
            omitted.append({"path": path, "reason": "secret, excluded, non-source or symlink path"})
            continue
        git_path = (root.relative_to(Path(project["git_root"])) / path).as_posix()
        if repo.ignored(git_path):
            omitted.append({"path": path, "reason": "Git-ignored path"})
            continue
        if not destination.is_file():
            captured.append({"path": path, "status": "deleted/unavailable"})
            continue
        entry = inventory["files"].get(path)
        if entry is None:
            omitted.append({"path": path, "reason": "not approved textual source evidence"})
            continue
        current = entry["content"]
        try:
            blob = repo.head.commit.tree / git_path
        except KeyError:
            blob = None
        if blob is None:
            content, kind = current, "complete_new_file"
            old_hash = None
        else:
            if blob.size > _REFERENCE_LIMIT * 4:
                omitted.append({"path": path, "reason": "HEAD text exceeds evidence limit"})
                continue
            try:
                previous = blob.data_stream.read().decode("utf-8")
            except UnicodeDecodeError:
                omitted.append({"path": path, "reason": "binary HEAD content"})
                continue
            if "\x00" in previous:
                omitted.append({"path": path, "reason": "binary HEAD content"})
                continue
            old_hash = hashlib.sha256(previous.encode()).hexdigest()
            content = "".join(difflib.unified_diff(previous.splitlines(keepends=True), current.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"))
            kind = "HEAD_diff"
        if len(content) > remaining:
            omitted.append({"path": path, "reason": "100000-character inline reference limit; file not truncated"})
            continue
        remaining -= len(content)
        captured.append({"path": path, "kind": kind, "head_hash": old_hash,
                         "hash": hashlib.sha256(current.encode()).hexdigest(), "content": content})
    return {"head": project["source"]["head"], "fingerprint": inventory["fingerprint"],
            "notice": "Reference only. HEAD diffs may include pre-existing local edits and do not prove task ownership. Never apply this patch; reimplement from the clean target branch.",
            "files": captured, "omitted": omitted}


def _description(report: dict, evidence: dict) -> str:
    sections = [("Requested behavior", {key: report[key] for key in ("title", "request", "acceptance_criteria", "scope")}),
                ("Source identity", report["source"]), ("Reviewer findings (CTO-reported, not independently attested)", report["reviews"]),
                ("Test evidence and unresolved prerequisites (CTO-reported)", report["workspace_evidence"])]
    if "advisor_summary" in report:
        sections.extend([("Advisor advice", report["advisor_summary"]),
                         ("Latest test results", report["tests_run"]),
                         ("Clean reimplementation handoff", {key: report[key] for key in ("transfer_mode", "outcome", "failure_kind", "failure_output") if key in report})])
    sections.append(("Rejected implementation — reference only", evidence))
    return "\n\n".join(f"## {heading}\n\n{_block(value)}" for heading, value in sections)


def _database_path() -> Path:
    return Path(os.environ.get("NESTI_STATE_DIR", "/var/lib/nesti")) / "escalations.sqlite3"


def _journal() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise RuntimeError("Escalation journal must not be a symlink")
    connection = sqlite3.connect(path, timeout=60, isolation_level=None)
    os.chmod(path, 0o600)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS escalations (namespace TEXT NOT NULL, operation_id TEXT NOT NULL, request_hash TEXT NOT NULL, issue_iid INTEGER, phase TEXT NOT NULL, report_json TEXT NOT NULL, pending_json TEXT, PRIMARY KEY(namespace, operation_id))")
    connection.execute("BEGIN IMMEDIATE")
    return connection


class _Escalation:
    def __init__(self, project_id: int, operation_id: str) -> None:
        try:
            if str(UUID(operation_id)) != operation_id:
                raise ValueError("noncanonical UUID")
        except (ValueError, TypeError, AttributeError):
            _fail("invalid_report", "operation_id must be a persisted canonical UUID")
        self.project = inspect_project(str(configured_project_root()))
        if type(project_id) is not int or project_id != self.project["id"]:
            _fail("project_mismatch", "Requested project differs from the configured shared project")
        self.client = GitLabIssuesClient()
        if self.client.get_project()["id"] != project_id:
            _fail("project_mismatch", "GitLab project identity changed")
        self.user_id = self.client.current_user_id()
        self.operation_id = operation_id
        self.key = (self.project["namespace"], operation_id)
        if not self.key[0]:
            _fail("project_mismatch", "Configured project namespace is unavailable")
        # Keep submissions serialized across the commits that make intents durable.
        lock_path = _database_path().with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX)
            self.db = _journal()
        except Exception:
            os.close(self.lock)
            raise

    def close(self) -> None:
        self.db.close()
        os.close(self.lock)

    def row(self) -> dict | None:
        row = self.db.execute("SELECT * FROM escalations WHERE namespace=? AND operation_id=?", self.key).fetchone()
        return dict(row) if row is not None else None

    def save(self, *, phase: str, pending: dict | None, iid: int | None = None) -> dict:
        self.db.execute("UPDATE escalations SET phase=?, pending_json=?, issue_iid=COALESCE(?, issue_iid) WHERE namespace=? AND operation_id=?",
                        (phase, _json(pending) if pending is not None else None, iid, *self.key))
        self.db.commit()
        self.db.execute("BEGIN IMMEDIATE")
        return self.row()

    def marker(self, row: dict) -> str:
        identity = {"namespace": self.key[0], "operation_id": self.operation_id,
                    "project_id": self.project["id"], "target_branch": self.project["target_branch"],
                    "request_hash": row["request_hash"]}
        return f"<!-- {_OWNERSHIP} {_json(identity)} -->"

    def owned(self, issue: dict, row: dict) -> None:
        markers = re.findall(r"<!-- NESTI_OMP_ESCALATION_V1 .*? -->", issue.get("description", ""))
        if (issue.get("project_id") != self.project["id"] or issue.get("author_id") != self.user_id
                or markers != [self.marker(row)]
                or issue.get("description", "").count(_OWNERSHIP) != 1):
            _fail("ownership_mismatch", "Issue project, authenticated author or exact ownership marker differs")

    def result(self, row: dict, issue: dict) -> dict:
        return {"success": True, "result": {"project_id": self.project["id"],
                "issue_id": issue["iid"], "operation_id": self.operation_id,
                "namespace": self.key[0], "target_branch": self.project["target_branch"],
                "application_root": self.project["application_root"],
                "url": issue["web_url"], "phase": row["phase"]}}

    def find(self, row: dict) -> dict | None:
        candidates = []
        for issue in self.client.list_issues(state="all"):
            description = issue.get("description", "")
            if (issue.get("author_id") != self.user_id
                    or _OWNERSHIP not in description or self.operation_id not in description):
                continue
            self.owned(issue, row)
            candidates.append(issue)
        if len(candidates) > 1:
            _fail("ownership_mismatch", "Multiple issues claim the same escalation operation")
        return self.client.get_issue(candidates[0]["iid"]) if candidates else None

    def available(self, issue: dict, *, transferred: bool = False) -> None:
        labels = issue.get("labels") or []
        if (issue.get("state") != "opened" or self.client.pause_label in labels
                or (not transferred and (self.client.issue_label in labels or self.client.in_progress_label in labels))):
            _fail("operation_conflict", "Issue is closed, paused, or already opted into Nesti; manual controls are preserved")
        hold = self.client._record_hold_reason(issue["iid"])
        if hold:
            _fail("operation_conflict", f"Issue is dependency-held: {hold}")

    def source(self, report: dict) -> None:
        if (report["source"]["application_root"] != self.project["application_root"]
                or report["source"]["target_branch"] != self.project["target_branch"]):
            _fail("project_mismatch", "Report application root or target branch differs from the configured project")

    def current_source(self, report: dict, evidence: dict) -> None:
        repo = Repo(self.project["git_root"])
        branch = None if repo.head.is_detached else repo.active_branch.name
        if (report["source"]["head"] != repo.head.commit.hexsha
                or report["source"]["local_branch"] != branch
                or report["architecture_fingerprint"] != evidence["fingerprint"]):
            _fail("invalid_report", "Report source HEAD, branch or architecture fingerprint is stale")

    def create(self, report: dict) -> dict:
        self.source(report)
        request_hash = _hash(report)
        row = self.row()
        fresh = row is None
        if row is not None and row["request_hash"] != request_hash:
            _fail("operation_conflict", "operation_id already belongs to a different creation report")
        if fresh:
            row = {"request_hash": request_hash}
        issue = self.find(row)
        if fresh:
            if issue is None:
                evidence = _capture(self.project, report)
                self.current_source(report, evidence)
                description = _description(report, evidence) + "\n\n" + self.marker(row)
            else:
                description = issue["description"]
            self.db.execute("INSERT INTO escalations VALUES (?,?,?,?,?,?,?)", (*self.key, request_hash, None, "creating", _json(report), _json({"description": description})))
            self.db.commit()
            self.db.execute("BEGIN IMMEDIATE")
            row = self.row()
            if issue is None and row["phase"] == "creating":
                try:
                    self.client.create_issue(report["title"], description, labels=[])
                except Exception as exc:
                    logger.warning("Escalation create outcome requires read-back: %s", exc)
                issue = self.find(row)
        if issue is None:
            _fail("creation_unconfirmed", "Submitted creation is unconfirmed; preserve this operation_id and resolve remotely, never submit a replacement")
        self.owned(issue, row)
        if row["phase"] == "creating":
            if issue["description"] != json.loads(row["pending_json"])["description"]:
                _fail("creation_unconfirmed", "Created issue requirements did not independently read back exactly")
            if issue.get("state") != "opened" or issue.get("labels") != []:
                _fail("creation_unconfirmed", "Created issue is not independently verified open and completely unlabeled")
            row = self.save(phase="assisted", pending=None, iid=issue["iid"])
        elif row["issue_iid"] != issue["iid"]:
            _fail("ownership_mismatch", "Journal and remote issue iid differ")
        elif row["phase"] == "assisted":
            self.available(issue)
        return self.result(row, issue)

    def transition(self, issue_id: int, payload: dict, *, handoff: bool) -> dict:
        row = self.row()
        if row is None or type(issue_id) is not int or row["issue_iid"] != issue_id:
            _fail("ownership_mismatch", "Operation does not own this issue in the durable journal")
        phase, terminal = ("handing_off", "handed_off") if handoff else ("completing", "completed")
        if row["phase"] not in ("assisted", phase, terminal):
            _fail("operation_conflict", f"Cannot transition an escalation in phase {row['phase']}")
        issue = self.client.get_issue(issue_id)
        self.owned(issue, row)
        pending = json.loads(row["pending_json"]) if row["pending_json"] else None
        if row["phase"] == "assisted":
            self.available(issue)
            original = json.loads(row["report_json"])
            if handoff:
                self.source(payload)
                for field in ("title", "request", "acceptance_criteria", "scope"):
                    if payload[field] != original[field]:
                        _fail("operation_conflict", f"Handoff cannot rewrite original {field}")
                if payload["reviews"][:2] != original["reviews"]:
                    _fail("operation_conflict", "Handoff cannot rewrite prior rejections")
                evidence = _capture(self.project, payload)
                self.current_source(payload, evidence)
                marker = f"<!-- {_HANDOFF} {_json({'operation_id': self.operation_id, 'request_hash': _hash(payload)})} -->"
                section = marker + "\n\n" + _description(payload, evidence) + f"\n\n<!-- /{_HANDOFF} -->"
                pending = {"payload": payload, "section": section}
            else:
                pending = {"payload": payload}
            row = self.save(phase=phase, pending=pending)
            pending = json.loads(row["pending_json"])
        if pending is None or pending["payload"] != payload:
            _fail("operation_conflict", "A different terminal request is already journaled")
        if handoff:
            return self.handoff(row, pending, issue)
        return self.complete(row, pending, issue)

    def submitted(self, row: dict, pending: dict, flag: str) -> tuple[dict, dict]:
        pending[flag] = True
        row = self.save(phase=row["phase"], pending=pending)
        return row, json.loads(row["pending_json"])

    def note(self, iid: int, body: str) -> dict | None:
        matches = [note for note in self.client.list_notes(iid) if not note.get("system")
                   and (note.get("author") or {}).get("id") == self.user_id and note.get("body") == body]
        if len(matches) > 1:
            _fail("ownership_mismatch", "Multiple authenticated attribution notes exist")
        if not matches:
            return None
        response = self.client.session.get(f"{self.client._project_api}/issues/{iid}/notes/{matches[0]['id']}", timeout=_TIMEOUT)
        response.raise_for_status()
        note = response.json()
        if (note.get("body") != body or note.get("system")
                or (note.get("author") or {}).get("id") != self.user_id):
            _fail("transition_unconfirmed", "Attribution note did not independently read back exactly")
        return note

    def complete(self, row: dict, pending: dict, issue: dict) -> dict:
        iid = issue["iid"]
        body = f"omp-developer / model: {pending['payload']['model']}"
        note = self.note(iid, body)
        if note is None:
            if row["phase"] == "completed" or pending.get("note_submitted"):
                _fail("transition_unconfirmed", "Attribution POST is unconfirmed; closing is forbidden")
            self.available(self.client.get_issue(iid))
            row, pending = self.submitted(row, pending, "note_submitted")
            self.client._comment(iid, body)
            note = self.note(iid, body)
            if note is None:
                _fail("transition_unconfirmed", "Attribution note was not verified; issue remains open")
        issue = self.client.get_issue(iid)
        self.owned(issue, row)
        if issue.get("state") == "closed":
            if not pending.get("close_submitted"):
                _fail("operation_conflict", "Issue was closed outside the completion submission")
        else:
            self.available(issue)
            if row["phase"] == "completed" or pending.get("close_submitted"):
                _fail("transition_unconfirmed", "Submitted closure is not currently confirmed; manual reopening is preserved")
            row, pending = self.submitted(row, pending, "close_submitted")
            self.client.close_issue(iid)
            issue = self.client.get_issue(iid)
            self.owned(issue, row)
            if issue.get("state") != "closed":
                _fail("transition_unconfirmed", "Issue closure did not read back")
        if row["phase"] != "completed":
            row = self.save(phase="completed", pending=pending)
        return self.result(row, issue)

    def handoff(self, row: dict, pending: dict, issue: dict) -> dict:
        iid = issue["iid"]
        section = pending["section"]
        self.available(issue, transferred=bool(pending.get("label_submitted")))
        if section not in issue["description"]:
            if pending.get("description_submitted") or row["phase"] == "handed_off":
                _fail("transition_unconfirmed", "Handoff description submission is not independently confirmed")
            if _HANDOFF in issue["description"]:
                _fail("ownership_mismatch", "A conflicting handoff section already exists")
            row, pending = self.submitted(row, pending, "description_submitted")
            issue = self.client.get_issue(iid)
            self.owned(issue, row)
            self.available(issue)
            try:
                self.client._update(iid, {"description": issue["description"] + "\n\n" + section})
            except Exception as exc:
                logger.warning("Handoff description outcome requires read-back: %s", exc)
            issue = self.client.get_issue(iid)
            self.owned(issue, row)
            if section not in issue["description"]:
                _fail("transition_unconfirmed", "Handoff description was not verified; opt-in is forbidden")
        self.available(issue, transferred=bool(pending.get("label_submitted")))
        labels = issue.get("labels") or []
        if self.client.issue_label not in labels:
            if pending.get("label_submitted") or row["phase"] == "handed_off":
                _fail("transition_unconfirmed", "Opt-in is absent after submission; a human opt-out is never reversed")
            row, pending = self.submitted(row, pending, "label_submitted")
            issue = self.client.get_issue(iid)
            self.owned(issue, row)
            self.available(issue)
            if section not in issue["description"]:
                _fail("transition_unconfirmed", "Handoff description changed before label submission")
            try:
                self.client._update(iid, {"add_labels": self.client.issue_label})
            except Exception as exc:
                logger.warning("Handoff opt-in outcome requires read-back: %s", exc)
            issue = self.client.get_issue(iid)
        self.owned(issue, row)
        self.available(issue, transferred=True)
        if self.client.issue_label not in (issue.get("labels") or []) or section not in issue["description"]:
            _fail("transition_unconfirmed", "Open opt-in and exact handoff description were not verified")
        if row["phase"] != "handed_off":
            row = self.save(phase="handed_off", pending=pending)
        return self.result(row, issue)


def _call(project_id: int, operation_id: str, action: str, **kwargs: object) -> dict:
    service = None
    try:
        if action == "create":
            _validate_report(kwargs["report"])
        else:
            handoff = kwargs["handoff"]
            payload = kwargs["payload"]
            if handoff:
                _validate_report(payload, handoff=True)
            else:
                _review(payload["review"], 3, "approve")
                model = payload["model"]
                if not _text(model) or model != model.strip() or any(ord(c) < 32 or ord(c) == 127 for c in model):
                    _fail("invalid_report", "Runtime developer model must be nonempty and single-line")
        service = _Escalation(project_id, operation_id)
        return getattr(service, action)(**kwargs)
    except _Failure as exc:
        return {"success": False, "error": str(exc), "code": exc.code}
    except Exception as exc:
        logger.warning("Escalation operation failed: %s", exc)
        result = {"success": False, "error": str(exc)}
        if service is not None:
            row = service.row()
            if row and row["phase"] == "creating":
                result["code"] = "creation_unconfirmed"
            elif row and row["phase"] in ("completing", "handing_off"):
                result["code"] = "transition_unconfirmed"
        return result
    finally:
        if service is not None:
            service.close()


def issue_escalation_create(project_id: int, operation_id: str, report: dict) -> dict:
    """Create/recover one unlabeled escalation after exactly two CTO-reported rejections."""
    return _call(project_id, operation_id, "create", report=report)


def issue_escalation_complete(project_id: int, issue_id: int, operation_id: str, model: str, review: dict) -> dict:
    """Verify a runtime-model attribution note before closing an approved third attempt."""
    return _call(project_id, operation_id, "transition", issue_id=issue_id, payload={"model": model, "review": review}, handoff=False)


def issue_escalation_handoff(project_id: int, issue_id: int, operation_id: str, report: dict) -> dict:
    """Verify failure evidence in the description before opting into clean Nesti reimplementation."""
    return _call(project_id, operation_id, "transition", issue_id=issue_id, payload=report, handoff=True)


def issue_history(project_id: int, issue_id: int) -> dict:
    """Read all issue notes with authenticated authorship and an optional local journal phase."""
    try:
        client = GitLabIssuesClient()
        namespace = project_namespace()
        if type(project_id) is not int or client.get_project()["id"] != project_id or not namespace:
            _fail("project_mismatch", "History is restricted to the configured project")
        if type(issue_id) is not int or issue_id <= 0:
            _fail("invalid_report", "issue_id must be a positive project-scoped iid")
        user_id = client.current_user_id()
        issue = client.get_issue(issue_id)
        if issue.get("project_id") != project_id:
            _fail("project_mismatch", "Issue belongs to another project")
        notes = []
        for note in client.list_notes(issue_id):
            author = note.get("author") or {}
            notes.append({"id": note["id"], "body": note.get("body", ""),
                          "system": bool(note.get("system")), "author_id": author.get("id"),
                          "author": author.get("username", ""), "created_at": note.get("created_at"),
                          "updated_at": note.get("updated_at"),
                          "trusted_automation": not note.get("system") and author.get("id") == user_id})
        escalation = None
        path = _database_path()
        if path.exists():
            with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=60) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute("SELECT * FROM escalations WHERE namespace=? AND issue_iid=?", (namespace, issue_id)).fetchall()
                if len(rows) > 1:
                    _fail("ownership_mismatch", "Multiple journal operations claim the issue")
                if rows:
                    row = rows[0]
                    source = json.loads(row["report_json"])["source"]
                    marker = f"<!-- {_OWNERSHIP} {_json({'namespace': namespace, 'operation_id': row['operation_id'], 'project_id': project_id, 'target_branch': source['target_branch'], 'request_hash': row['request_hash']})} -->"
                    if (issue.get("author_id") != user_id
                            or issue["description"].count(_OWNERSHIP) != 1
                            or marker not in issue["description"]):
                        _fail("ownership_mismatch", "Journal history lacks authenticated remote ownership")
                    escalation = {"project_id": project_id, "issue_id": issue_id,
                                  "operation_id": row["operation_id"], "namespace": namespace,
                                  "target_branch": source["target_branch"], "application_root": source["application_root"],
                                  "url": issue["web_url"], "phase": row["phase"]}
        return {"success": True, "result": {"issue": issue, "notes": notes, "escalation": escalation}}
    except _Failure as exc:
        return {"success": False, "error": str(exc), "code": exc.code}
    except Exception as exc:
        logger.warning("Issue history unavailable: %s", exc)
        return {"success": False, "error": str(exc)}
