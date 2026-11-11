"""
GitLab Issues client – task intake gateway.

Replaces the former Redmine intake. Responsibilities:
- Fetch the oldest pending issue from the configured GitLab project.
- Lock it so another worker cannot pick it up.
- Close it on success and return it to the pending pool on failure.
- Pause and resume an issue (the domain question holds it with the pause label).
- Create issues: the operator scripts (``scripts/seed_live_issues.py``,
  ``scripts/preflight.py``) reuse it.

Why GitLab Issues have no "in progress" state
─────────────────────────────────────────────
GitLab issues are only ``opened`` or ``closed``, so the intake model lives in
labels:

    <label>                    the opt-in marker a developer adds ("nesti")
    <label>::in-progress       the lock Nesti owns
    <label>::pause             the hold while Nesti waits on a human answer

    pending      = opened, has <label>, has neither control label
    in progress  = opened, has <label>::in-progress
    paused       = opened, has <label>::pause
    done         = closed

A pending issue whose latest trusted failed-run marker matches its current
title, description and target-branch HEAD is skipped: nothing changed since.

``<label>`` comes from GITLAB_ISSUE_LABEL (default "nesti"), so Nesti never
touches an issue a human opened for discussion: intake is opt-in.

Scoped labels (the ``::`` form) are mutually exclusive within their scope in
GitLab, which is what makes the lock single-valued.

Every mutation is verified by an independent read-back. The Redmine intake
this replaces trusted the HTTP status and silently stranded issues when a
workflow rule dropped the change; a lock or unlock that did not apply must be
loud.
"""

import hashlib
import json
import logging
import os
import re
from urllib.parse import quote
from collections.abc import Iterator

import requests

import forge

logger = logging.getLogger(__name__)

_DEFAULT_ISSUE_LABEL = "nesti"
_IN_PROGRESS_SUFFIX = "::in-progress"
_PAUSE_SUFFIX = "::pause"
_REQUEST_TIMEOUT = 15
_POLL_HEARTBEAT_VARIABLE = "NESTI_POLL_HEARTBEAT"
_PER_PAGE = 100
_MAX_PAGES = 1000
_ISSUE_STATES = ("opened", "closed", "all")
_FAILED_RUN_RE = re.compile(r"^<!-- NESTI_FAILED_RUN_V1 [0-9a-f]{64} -->$", re.M)


def _normalise_text(text: str | None) -> str:
    return (text or "").replace("\r\n", "\n").strip()


def failed_run_marker(subject: str, description: str, head_sha: str) -> str:
    """The hidden note line fingerprinting a failed run's title, description and target HEAD."""
    digest = hashlib.sha256(json.dumps([subject, description, head_sha]).encode()).hexdigest()
    return f"<!-- NESTI_FAILED_RUN_V1 {digest} -->"


class GitLabIssuesClient:
    """Issue intake and lifecycle against the GitLab API."""

    def __init__(self) -> None:
        self.base_url = os.environ["GITLAB_URL"].rstrip("/")
        self.token = os.environ["GITLAB_TOKEN"]
        self.project_path = forge.path()
        self.issue_label = (
            os.environ.get("GITLAB_ISSUE_LABEL", _DEFAULT_ISSUE_LABEL).strip()
            or _DEFAULT_ISSUE_LABEL
        )
        self.in_progress_label = f"{self.issue_label}{_IN_PROGRESS_SUFFIX}"
        self.pause_label = f"{self.issue_label}{_PAUSE_SUFFIX}"
        self._user_id: int | None = None

        self.session = requests.Session()
        self.session.headers.update(
            {"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"}
        )
        self.session.verify = (
            os.environ.get("GITLAB_SSL_VERIFY", "true").lower() != "false"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _project_api(self) -> str:
        return f"{self.base_url}/api/v4/projects/{quote(self.project_path, safe='')}"

    @staticmethod
    def _normalise(issue: dict) -> dict:
        """
        Map a GitLab issue onto the intake contract the pipeline consumes.

        ``id``/``subject``/``description`` are what skill_loader, prompt_builder
        and every graph node read, so the GitLab field names are translated
        here rather than leaking ``iid``/``title`` across the whole codebase.
        ``id`` is the project-scoped ``iid``: it is what "#7" means to a human
        looking at the project and what GitLab closing keywords resolve.
        """
        author = issue.get("author") or {}
        project_id = issue.get("project_id")
        author_id = author.get("id")
        return {
            "id": issue["iid"],
            "subject": issue.get("title", "") or "",
            "description": issue.get("description", "") or "",
            "iid": issue["iid"],
            "global_id": issue.get("id"),
            "state": issue.get("state"),
            "labels": issue.get("labels", []),
            "web_url": issue.get("web_url", ""),
            "author": author.get("username", ""),
            "project_id": project_id if type(project_id) is int else None,
            "author_id": author_id if type(author_id) is int else None,
        }

    def _get_raw(self, iid: int) -> dict:
        response = self.session.get(
            f"{self._project_api}/issues/{iid}", timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    def _pages(self, url: str, params: dict | None = None) -> Iterator[list[dict]]:
        """Yield collection pages, following GitLab's ``X-Next-Page``."""
        query = dict(params or {})
        query["per_page"] = _PER_PAGE
        page = "1"
        for _ in range(_MAX_PAGES):
            query["page"] = page
            response = self.session.get(url, params=query, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, list):
                raise RuntimeError(f"GitLab returned a non-list page for {url}")
            yield body
            page = (response.headers.get("X-Next-Page") or "").strip()
            if not page:
                return
        raise RuntimeError(f"Pagination of {url} exceeded {_MAX_PAGES} pages")

    def _paginate(self, url: str, params: dict | None = None) -> list[dict]:
        """Return all items using the shared collection pagination."""
        return [item for page in self._pages(url, params) for item in page]

    def _update(self, iid: int, payload: dict) -> dict:
        """PUT *payload*, then return an independent read-back of the issue."""
        response = self.session.put(
            f"{self._project_api}/issues/{iid}", json=payload, timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return self._get_raw(iid)

    def _comment(self, iid: int, body: str) -> bool:
        """Post a note. A failed note must never fail the transition itself."""
        try:
            response = self.session.post(
                f"{self._project_api}/issues/{iid}/notes",
                json={"body": body},
                timeout=_REQUEST_TIMEOUT,
            )
            if response.status_code not in (200, 201):
                logger.warning(
                    "Could not comment on issue #%s – HTTP %s",
                    iid, response.status_code,
                )
                return False
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Could not comment on issue #%s: %s", iid, exc)
            return False

    def _opted_in_open(self, issue: dict) -> bool:
        return (
            issue.get("state") == "opened"
            and self.issue_label in (issue.get("labels") or [])
        )

    def _not_pending_reason(self, issue: dict) -> str | None:
        """Why *issue* (raw or normalised) is not pending, or None when it is."""
        labels = issue.get("labels") or []
        if issue.get("state") != "opened":
            return f"state is {issue.get('state')!r}"
        if self.issue_label not in labels:
            return f"the opt-in label {self.issue_label!r} is absent"
        if self.in_progress_label in labels:
            return f"it carries {self.in_progress_label!r}"
        if self.pause_label in labels:
            return f"it carries {self.pause_label!r}"
        return None

    def _target_head(self) -> str | None:
        """The target branch's HEAD sha, or None when the branch does not exist (404)."""
        branch = quote(forge.default_branch(), safe="")
        response = self.session.get(
            f"{self._project_api}/repository/branches/{branch}", timeout=_REQUEST_TIMEOUT
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()["commit"]["id"]

    def _failed_run(self, iid: int) -> str | None:
        """The latest trusted failed-run marker on *iid* (highest note id), or None."""
        user_id = self.current_user_id()
        latest: tuple[int, str] | None = None
        for note in self._paginate(f"{self._project_api}/issues/{iid}/notes"):
            if (not note.get("system") and (note.get("author") or {}).get("id") == user_id
                    and (match := _FAILED_RUN_RE.search(note.get("body") or ""))
                    and (latest is None or note.get("id", 0) > latest[0])):
                latest = (note.get("id", 0), match.group(0))
        return latest[1] if latest else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, iid: int) -> dict:
        """Fetch one issue by its project-scoped iid, in intake shape."""
        return self._normalise(self._get_raw(iid))

    def project_info(self) -> dict:
        """The GitLab project record (``GET /projects/:id``); raises on a non-2xx answer."""
        response = self.session.get(self._project_api, timeout=_REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def list_issues(
        self, *, state: str = "opened", labels: list[str] | None = None
    ) -> list[dict]:
        """Return every issue in *state* carrying all *labels*, oldest first."""
        if state not in _ISSUE_STATES:
            raise ValueError(f"state must be one of {_ISSUE_STATES}, got {state!r}")
        params = {"state": state, "order_by": "created_at", "sort": "asc"}
        if labels:
            params["labels"] = ",".join(labels)
        return [
            self._normalise(issue)
            for issue in self._paginate(f"{self._project_api}/issues", params)
        ]

    def list_pending(self, limit: int = 25) -> list[dict]:
        """
        Return up to *limit* pending issues, oldest first.

        GitLab cannot express "has label A but none of B, C" in one query, so
        the opt-in label is filtered server-side and control labels client-side.
        Pages are followed until enough issues are found, so a page of locked
        or paused issues never starves eligible work. A metadata error excludes
        only that issue; a failed issue-list or target-HEAD call raises. An
        issue whose last failed run saw the same title, description and target
        HEAD is skipped (see ``failed_run_marker``) and does not count toward
        *limit*.
        """
        url = f"{self._project_api}/issues"
        query = {
            "state": "opened",
            "labels": self.issue_label,
            "order_by": "created_at",
            "sort": "asc",
        }
        pending: list[dict] = []
        head: str | None = None
        head_read = False
        if limit <= 0:
            return pending
        for page in self._pages(url, query):
            for issue in page:
                labels = issue.get("labels") or []
                if (self.in_progress_label in labels or self.pause_label in labels
                        or self.issue_label not in labels
                        or issue.get("state") != "opened"):
                    continue
                try:
                    marker = self._failed_run(issue["iid"])
                except Exception as exc:  # pylint: disable=broad-except
                    logger.info("Issue #%s is not pending: its notes could not be read: %s.",
                                issue["iid"], exc)
                    continue
                normalised = self._normalise(issue)
                if marker:
                    if not head_read:
                        head, head_read = self._target_head(), True
                    if head is not None and marker == failed_run_marker(
                            normalised["subject"], normalised["description"], head):
                        logger.info(
                            "Issue #%s is not pending: its last failed run saw the same "
                            "title, description and target-branch HEAD.", issue["iid"],
                        )
                        continue
                pending.append(normalised)
                if len(pending) >= limit:
                    return pending
        return pending

    def get_next_issue(self) -> dict | None:
        """Return the oldest pending issue, or None when there is no work."""
        pending = self.list_pending(limit=1)
        if not pending:
            logger.info(
                "No pending issues labelled %r in %s.",
                self.issue_label, self.project_path,
            )
            return None
        issue = pending[0]
        logger.info("Fetched issue #%s: %s", issue["id"], issue["subject"])
        return issue

    def lock_issue(self, iid: int) -> bool:
        """
        Claim a still-pending issue by adding the in-progress label.

        ``add_labels`` is used instead of replacing ``labels`` so a
        concurrently added human label is never dropped.
        """
        try:
            reason = self._not_pending_reason(self._get_raw(iid))
            if reason:
                logger.warning("Refusing to lock issue #%s: %s.", iid, reason)
                return False
            updated = self._update(iid, {"add_labels": self.in_progress_label})
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to lock issue #%s: %s", iid, exc)
            return False

        labels = updated.get("labels") or []
        if (not self._opted_in_open(updated) or self.in_progress_label not in labels
                or self.pause_label in labels):
            logger.error(
                "Issue #%s was NOT locked: state=%r, labels=%s. Another worker may "
                "have taken it, or the token lacks Reporter rights on %s.",
                iid, updated.get("state"), labels, self.project_path,
            )
            return False
        logger.info("Issue #%s locked (label %r added).", iid, self.in_progress_label)
        return True

    def close_issue(self, iid: int, note: str = "", require_note: bool = False) -> bool:
        """Comment, drop the lock label and close the issue.

        With *require_note* a failed comment aborts before the issue closes.
        """
        if note and not self._comment(iid, note) and require_note:
            logger.error("Issue #%s left open: the required note was not posted.", iid)
            return False
        try:
            updated = self._update(
                iid,
                {
                    "remove_labels": self.in_progress_label,
                    "state_event": "close",
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to close issue #%s: %s", iid, exc)
            return False

        if (updated.get("state") != "closed"
                or self.in_progress_label in (updated.get("labels") or [])):
            logger.error(
                "Issue #%s was NOT closed: state=%r, labels=%s.",
                iid, updated.get("state"), updated.get("labels"),
            )
            return False
        logger.info("Issue #%s closed.", iid)
        return True

    def handoff_issue(self, iid: int, appendix: str) -> bool:
        """Append *appendix* to an open, unlabelled issue and add the opt-in label."""
        raw = self._get_raw(iid)
        if raw.get("state") != "opened" or self.issue_label in (raw.get("labels") or []):
            logger.error("Issue #%s not handed off: closed or already opted in.", iid)
            return False
        try:
            updated = self._update(iid, {
                "description": (raw.get("description") or "").rstrip()
                + "\n\n" + appendix.strip() + "\n",
                "add_labels": self.issue_label,
            })
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to hand off issue #%s: %s", iid, exc)
            return False
        if (updated.get("state") != "opened"
                or self.issue_label not in (updated.get("labels") or [])
                or not _normalise_text(updated.get("description")).endswith(
                    _normalise_text(appendix.strip()))):
            logger.error("Issue #%s hand-off did not read back.", iid)
            return False
        logger.info("Issue #%s handed off (label %r added).", iid, self.issue_label)
        return True

    def list_notes(self, iid: int) -> list[dict]:
        """Non-system notes of issue *iid*, oldest first."""
        return [
            {"id": n.get("id"), "author": (n.get("author") or {}).get("username"),
             "author_id": (n.get("author") or {}).get("id"),
             "created_at": n.get("created_at"), "body": n.get("body"), "trusted": True}
            for n in self._paginate(f"{self._project_api}/issues/{iid}/notes",
                                    {"sort": "asc", "order_by": "created_at"})
            if not n.get("system")
        ]

    def post_note(self, iid: int, body: str) -> int:
        """Post one note and verify it by an independent GET; return its id. Raises RuntimeError."""
        notes_url = f"{self._project_api}/issues/{iid}/notes"
        response = self.session.post(notes_url, json={"body": body}, timeout=_REQUEST_TIMEOUT)
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"Note on issue #{iid} failed: HTTP {response.status_code}")
        note_id = response.json().get("id")
        if not isinstance(note_id, int) or isinstance(note_id, bool) or note_id <= 0:
            raise RuntimeError(f"Note on issue #{iid} returned no id")
        check = self.session.get(f"{notes_url}/{note_id}", timeout=_REQUEST_TIMEOUT)
        check.raise_for_status()
        if check.json().get("body") != body:
            raise RuntimeError(f"Note {note_id} on issue #{iid} did not read back")
        return note_id

    def reopen_issue(self, iid: int, note: str = "") -> bool:
        """
        Return the issue to the pending pool after a failed run.

        Only a still-open opted-in issue is unlocked; a human closure or
        opt-out is never reversed. A pause is refused.
        """
        try:
            current = self._get_raw(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to reopen issue #%s: %s", iid, exc)
            return False
        if not self._opted_in_open(current):
            logger.warning("Refusing to reopen issue #%s: it is not open and opted in.", iid)
            return False
        if self.pause_label in (current.get("labels") or []):
            logger.warning(
                "Refusing to reopen issue #%s: it carries %r.", iid, self.pause_label
            )
            return False

        if note:
            self._comment(iid, note)
        try:
            updated = self._update(
                iid,
                {
                    "remove_labels": self.in_progress_label,
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to reopen issue #%s: %s", iid, exc)
            return False

        reason = self._not_pending_reason(updated)
        if reason:
            logger.error("Issue #%s was NOT returned to the pending pool: %s.", iid, reason)
            return False
        logger.info("Issue #%s returned to pending (lock label removed).", iid)
        return True

    def pause_issue(self, iid: int, note: str = "") -> bool:
        """
        Hold an open, opted-in issue: add the pause label, drop the lock.

        A closed or opted-out issue is left untouched (never reopened).
        """
        try:
            current = self._get_raw(iid)
            if not self._opted_in_open(current):
                logger.warning(
                    "Refusing to pause issue #%s: state=%r, labels=%s.",
                    iid, current.get("state"), current.get("labels"),
                )
                return False
            if note:
                self._comment(iid, note)
            updated = self._update(
                iid,
                {"add_labels": self.pause_label, "remove_labels": self.in_progress_label},
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to pause issue #%s: %s", iid, exc)
            return False

        labels = updated.get("labels") or []
        if (not self._opted_in_open(updated) or self.pause_label not in labels
                or self.in_progress_label in labels):
            logger.error(
                "Issue #%s was NOT paused: state=%r, labels=%s.",
                iid, updated.get("state"), labels,
            )
            return False
        logger.info("Issue #%s paused (label %r added).", iid, self.pause_label)
        return True

    def resume_issue(self, iid: int) -> bool:
        """
        Release an open, opted-in issue: drop both control labels.

        A closed or opted-out issue is left untouched (never reopened).
        """
        try:
            current = self._get_raw(iid)
            if not self._opted_in_open(current):
                logger.warning(
                    "Refusing to resume issue #%s: state=%r, labels=%s.",
                    iid, current.get("state"), current.get("labels"),
                )
                return False
            updated = self._update(
                iid,
                {"remove_labels": f"{self.pause_label},{self.in_progress_label}"},
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to resume issue #%s: %s", iid, exc)
            return False

        labels = updated.get("labels") or []
        if (not self._opted_in_open(updated) or self.pause_label in labels
                or self.in_progress_label in labels):
            logger.error(
                "Issue #%s was NOT resumed: state=%r, labels=%s.",
                iid, updated.get("state"), labels,
            )
            return False
        logger.info("Issue #%s resumed (control labels removed).", iid)
        return True

    def current_user_id(self) -> int:
        """The numeric id of the token's user (``GET /user``), cached per client."""
        if self._user_id is None:
            response = self.session.get(
                f"{self.base_url}/api/v4/user", timeout=_REQUEST_TIMEOUT
            )
            response.raise_for_status()
            user_id = response.json().get("id")
            if not isinstance(user_id, int) or isinstance(user_id, bool):
                raise RuntimeError("GitLab /user returned no numeric id")
            self._user_id = user_id
        return self._user_id

    def create_issue(
        self, title: str, description: str, labels: list[str] | None = None
    ) -> dict:
        """
        Create one issue (exactly one POST, never retried) and verify it.

        Returns the normalised read-back; raises RuntimeError on a non-2xx
        answer or a read-back that lacks the title, description or labels.
        """
        payload: dict = {"title": title, "description": description}
        if labels:
            payload["labels"] = ",".join(labels)
        response = self.session.post(
            f"{self._project_api}/issues", json=payload, timeout=_REQUEST_TIMEOUT
        )
        if not 200 <= response.status_code < 300:
            raise RuntimeError(
                f"Issue creation failed: HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )
        iid = response.json().get("iid")
        if type(iid) is not int or iid <= 0:
            raise RuntimeError("Issue creation returned no iid")
        issue = self.get_issue(iid)
        missing = [label for label in labels or [] if label not in issue["labels"]]
        if (issue["subject"] != title
                or _normalise_text(issue["description"]) != _normalise_text(description)
                or missing):
            raise RuntimeError(
                f"Issue #{iid} did not read back as created (missing labels: {missing})"
            )
        logger.info("Created issue #%s: %s", iid, title)
        return issue

    def swap_poll_heartbeat(self, value: str) -> str | None:
        """
        Write *value* to the project's poll-heartbeat CI/CD variable; return the previous value.

        Needs Maintainer. Every orchestrator polling the project writes here, so a
        foreign value reveals a second poller even on another machine.
        """
        url = f"{self._project_api}/variables/{_POLL_HEARTBEAT_VARIABLE}"
        current = self.session.get(url, timeout=_REQUEST_TIMEOUT)
        if current.status_code == 404:
            self.session.post(
                f"{self._project_api}/variables",
                json={"key": _POLL_HEARTBEAT_VARIABLE, "value": value,
                      "protected": False, "masked": False},
                timeout=_REQUEST_TIMEOUT,
            ).raise_for_status()
            return None
        current.raise_for_status()
        previous = current.json().get("value")
        self.session.put(url, json={"value": value}, timeout=_REQUEST_TIMEOUT).raise_for_status()
        return previous
