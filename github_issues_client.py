"""
GitHub Issues client – the GitHub counterpart of ``gitlab_issues_client.py``.

Same intake model, same return shapes (``forge.IssueClient``):

    pending      = open issue, has <label>, has neither control label,
                   author is OWNER / MEMBER / COLLABORATOR, no matching failed-run marker
    in progress  = open, has <label>::in-progress
    paused       = open, has <label>::pause (with both control labels: paused)
    done         = closed

What differs from GitLab:

- Labels are written only with ``POST …/issues/{n}/labels`` and
  ``DELETE …/issues/{n}/labels/{name}``. ``PATCH /issues`` with ``labels`` and
  ``PUT …/labels`` replace the whole set and would drop a label a human added
  at the same moment, so they are never used. Multi-step transitions therefore
  run in a fixed order chosen so a half-done one lands on the safe side, and
  every transition ends with an independent read-back.
- GitHub has no scoped labels; the control labels are plain labels.
- A public repository lets anyone open issues and comment. Only an issue whose
  author is OWNER, MEMBER or COLLABORATOR is pending, and only comments by them
  are ``trusted`` (the domain question counts trusted replies only).
- Issue and comment bodies are limited to 65,536 characters; a longer note is
  cut in the middle and a trailing failed-run marker line is always kept.
- ``/issues`` lists pull requests too; records with ``pull_request`` are dropped.
"""

import logging
import os
from collections.abc import Iterator
from urllib.parse import quote

import requests

import forge

logger = logging.getLogger(__name__)

_DEFAULT_ISSUE_LABEL = "nesti"
_DEFAULT_API_URL = "https://api.github.com"
_API_VERSION = "2022-11-28"
_IN_PROGRESS_SUFFIX = "::in-progress"
_PAUSE_SUFFIX = "::pause"
_REQUEST_TIMEOUT = 15
_POLL_HEARTBEAT_VARIABLE = "NESTI_POLL_HEARTBEAT"
_PER_PAGE = 100
_MAX_PAGES = 1000
_ISSUE_STATES = {"opened": "open", "closed": "closed", "all": "all"}
_TRUSTED_ASSOCIATIONS = ("OWNER", "MEMBER", "COLLABORATOR")
BODY_LIMIT = 65536
_TRUNCATED = "\n\n…(truncated)…\n\n"


def _normalise_text(text: str | None) -> str:
    return (text or "").replace("\r\n", "\n").strip()


def _raise_for_status(response: requests.Response) -> None:
    """``raise_for_status``, with GitHub's retry hints in the error on 403/429."""
    if response.status_code in (403, 429):
        hints = ", ".join(
            f"{name}={response.headers[name]}"
            for name in ("Retry-After", "X-RateLimit-Reset")
            if response.headers.get(name)
        )
        message = f"GitHub answered HTTP {response.status_code} for {response.url}" + (
            f" ({hints})" if hints else ""
        )
        logger.warning(message)
        raise requests.HTTPError(message, response=response)
    response.raise_for_status()


def fit_body(body: str) -> str:
    """*body* within GitHub's 65,536-character limit: cut in the middle, a trailing marker line kept."""
    if len(body) <= BODY_LIMIT:
        return body
    text = body.rstrip()
    rest, _, last = text.rpartition("\n")
    keep = ""
    if forge.FAILED_RUN_RE.fullmatch(last):
        text, keep = rest, "\n" + last
    room = BODY_LIMIT - len(_TRUNCATED) - len(keep)
    return text[: room - room // 2] + _TRUNCATED + text[len(text) - room // 2:] + keep


class GitHubIssuesClient:
    """Issue intake and lifecycle against the GitHub REST API."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("NESTI_GITHUB_API_URL", _DEFAULT_API_URL).rstrip("/")
        self.project_path = forge.path()
        self.issue_label = (
            os.environ.get("NESTI_GITHUB_ISSUE_LABEL", _DEFAULT_ISSUE_LABEL).strip()
            or _DEFAULT_ISSUE_LABEL
        )
        self.in_progress_label = f"{self.issue_label}{_IN_PROGRESS_SUFFIX}"
        self.pause_label = f"{self.issue_label}{_PAUSE_SUFFIX}"
        self._user_id: int | None = None

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {os.environ['NESTI_GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
        })

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _repo_api(self) -> str:
        return f"{self.base_url}/repos/{self.project_path}"

    @staticmethod
    def _labels(issue: dict) -> list[str]:
        return [label["name"] for label in issue.get("labels") or []]

    @staticmethod
    def _normalise(issue: dict) -> dict:
        """Map a GitHub issue onto the intake contract (``state`` ``open`` → ``opened``)."""
        user = issue.get("user") or {}
        author_id = user.get("id")
        return {
            "id": issue["number"],
            "subject": issue.get("title", "") or "",
            "description": issue.get("body", "") or "",
            "iid": issue["number"],
            "global_id": issue.get("id"),
            "state": "opened" if issue.get("state") == "open" else issue.get("state"),
            "labels": GitHubIssuesClient._labels(issue),
            "web_url": issue.get("html_url", ""),
            "author": user.get("login", ""),
            "project_id": None,
            "author_id": author_id if type(author_id) is int else None,
        }

    def _get_raw(self, number: int) -> dict:
        response = self.session.get(f"{self._repo_api}/issues/{number}", timeout=_REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.json()

    def _pages(self, url: str, params: dict | None = None) -> Iterator[list[dict]]:
        """Yield collection pages, following GitHub's ``Link: rel="next"``."""
        query: dict | None = {**(params or {}), "per_page": _PER_PAGE}
        next_url: str | None = url
        for _ in range(_MAX_PAGES):
            response = self.session.get(next_url, params=query, timeout=_REQUEST_TIMEOUT)
            _raise_for_status(response)
            body = response.json()
            if not isinstance(body, list):
                raise RuntimeError(f"GitHub returned a non-list page for {url}")
            yield body
            next_url = (response.links.get("next") or {}).get("url")
            if not next_url:
                return
            query = None  # the next link carries the query
        raise RuntimeError(f"Pagination of {url} exceeded {_MAX_PAGES} pages")

    def _add_label(self, number: int, label: str) -> None:
        response = self.session.post(
            f"{self._repo_api}/issues/{number}/labels", json={"labels": [label]},
            timeout=_REQUEST_TIMEOUT,
        )
        _raise_for_status(response)

    def _remove_label(self, number: int, label: str) -> None:
        """Drop *label*; 404 means it is already absent and the read-back decides."""
        response = self.session.delete(
            f"{self._repo_api}/issues/{number}/labels/{quote(label, safe='')}",
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code != 404:
            _raise_for_status(response)

    def _patch(self, number: int, payload: dict) -> None:
        """PATCH issue fields; never ``labels`` (that would replace the label set)."""
        response = self.session.patch(
            f"{self._repo_api}/issues/{number}", json=payload, timeout=_REQUEST_TIMEOUT
        )
        _raise_for_status(response)

    def _comment(self, number: int, body: str) -> bool:
        """Post a comment. A failed comment must never fail the transition itself."""
        try:
            response = self.session.post(
                f"{self._repo_api}/issues/{number}/comments",
                json={"body": fit_body(body)}, timeout=_REQUEST_TIMEOUT,
            )
            if response.status_code not in (200, 201):
                logger.warning("Could not comment on issue #%s – HTTP %s",
                               number, response.status_code)
                return False
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Could not comment on issue #%s: %s", number, exc)
            return False

    def _opted_in_open(self, issue: dict) -> bool:
        return issue.get("state") == "open" and self.issue_label in self._labels(issue)

    def _not_pending_reason(self, issue: dict) -> str | None:
        """Why the raw *issue* is not pending by state and labels (author trust aside), or None."""
        labels = self._labels(issue)
        if "pull_request" in issue:
            return "it is a pull request"
        if issue.get("state") != "open":
            return f"state is {issue.get('state')!r}"
        if self.issue_label not in labels:
            return f"the opt-in label {self.issue_label!r} is absent"
        if self.in_progress_label in labels:
            return f"it carries {self.in_progress_label!r}"
        if self.pause_label in labels:
            return f"it carries {self.pause_label!r}"
        return None

    @staticmethod
    def _untrusted_author(issue: dict) -> str | None:
        association = issue.get("author_association")
        if association in _TRUSTED_ASSOCIATIONS:
            return None
        return (f"its author {(issue.get('user') or {}).get('login')!r} is {association}, "
                f"not {'/'.join(_TRUSTED_ASSOCIATIONS)}")

    def _target_head(self) -> str | None:
        """The target branch's HEAD sha, or None when the branch does not exist (404)."""
        response = self.session.get(
            f"{self._repo_api}/branches/{quote(forge.default_branch())}", timeout=_REQUEST_TIMEOUT
        )
        if response.status_code == 404:
            return None
        _raise_for_status(response)
        return response.json()["commit"]["sha"]

    def _failed_run(self, number: int) -> str | None:
        """The latest trusted failed-run marker on *number* (highest comment id), or None."""
        user_id = self.current_user_id()
        latest: tuple[int, str] | None = None
        for note in self.list_notes(number):
            if (note["author_id"] == user_id
                    and (match := forge.FAILED_RUN_RE.search(note["body"] or ""))
                    and (latest is None or note["id"] > latest[0])):
                latest = (note["id"], match.group(0))
        return latest[1] if latest else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, iid: int) -> dict:
        """Fetch one issue by number, in intake shape."""
        return self._normalise(self._get_raw(iid))

    def project_info(self) -> dict:
        """The repository record plus ``path_with_namespace`` and ``issues_enabled``; raises on non-2xx."""
        response = self.session.get(self._repo_api, timeout=_REQUEST_TIMEOUT)
        _raise_for_status(response)
        repo = response.json()
        return {**repo, "path_with_namespace": repo.get("full_name"),
                "issues_enabled": bool(repo.get("has_issues"))}

    def list_issues(
        self, *, state: str = "opened", labels: list[str] | None = None
    ) -> list[dict]:
        """Return every issue (never a pull request) in *state* carrying all *labels*, oldest first."""
        if state not in _ISSUE_STATES:
            raise ValueError(f"state must be one of {tuple(_ISSUE_STATES)}, got {state!r}")
        params = {"state": _ISSUE_STATES[state], "sort": "created", "direction": "asc"}
        if labels:
            params["labels"] = ",".join(labels)
        return [
            self._normalise(issue)
            for page in self._pages(f"{self._repo_api}/issues", params)
            for issue in page if "pull_request" not in issue
        ]

    def list_pending(self, limit: int = 25) -> list[dict]:
        """
        Return up to *limit* pending issues, oldest first.

        The opt-in label is filtered server-side; pull requests, control
        labels and untrusted authors client-side. Pages are followed until
        enough issues are found. A comment-read error excludes only that issue;
        a failed issue-list or target-HEAD call raises (the poll is skipped).
        An issue whose last failed run saw the same title, description and
        target HEAD is skipped and does not count toward *limit*.
        """
        query = {"state": "open", "labels": self.issue_label, "sort": "created", "direction": "asc"}
        pending: list[dict] = []
        head: str | None = None
        head_read = False
        if limit <= 0:
            return pending
        for page in self._pages(f"{self._repo_api}/issues", query):
            for issue in page:
                if self._not_pending_reason(issue):
                    continue
                if reason := self._untrusted_author(issue):
                    logger.info("Issue #%s is not pending: %s.", issue["number"], reason)
                    continue
                try:
                    marker = self._failed_run(issue["number"])
                except Exception as exc:  # pylint: disable=broad-except
                    logger.info("Issue #%s is not pending: its comments could not be read: %s.",
                                issue["number"], exc)
                    continue
                normalised = self._normalise(issue)
                if marker:
                    if not head_read:
                        head, head_read = self._target_head(), True
                    if head is not None and marker == forge.failed_run_marker(
                            normalised["subject"], normalised["description"], head):
                        logger.info(
                            "Issue #%s is not pending: its last failed run saw the same "
                            "title, description and target-branch HEAD.", issue["number"],
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
            logger.info("No pending issues labelled %r in %s.", self.issue_label, self.project_path)
            return None
        issue = pending[0]
        logger.info("Fetched issue #%s: %s", issue["id"], issue["subject"])
        return issue

    def lock_issue(self, iid: int) -> bool:
        """Claim a still-pending issue: POST the in-progress label, then read back."""
        try:
            raw = self._get_raw(iid)
            reason = self._not_pending_reason(raw) or self._untrusted_author(raw)
            if reason:
                logger.warning("Refusing to lock issue #%s: %s.", iid, reason)
                return False
            self._add_label(iid, self.in_progress_label)
            updated = self._get_raw(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to lock issue #%s: %s", iid, exc)
            return False

        labels = self._labels(updated)
        if (not self._opted_in_open(updated) or self.in_progress_label not in labels
                or self.pause_label in labels):
            logger.error(
                "Issue #%s was NOT locked: state=%r, labels=%s. Another worker may "
                "have taken it, or the token lacks Issues write on %s.",
                iid, updated.get("state"), labels, self.project_path,
            )
            return False
        logger.info("Issue #%s locked (label %r added).", iid, self.in_progress_label)
        return True

    def close_issue(self, iid: int, note: str = "", require_note: bool = False) -> bool:
        """
        Comment, close the issue, then drop the lock label.

        Not atomic; the order is fixed so a half-done close leaves the issue
        closed and still locked (never back in the pending pool). With
        *require_note* a failed comment aborts before the issue closes.
        """
        if note and not self._comment(iid, note) and require_note:
            logger.error("Issue #%s left open: the required note was not posted.", iid)
            return False
        try:
            self._patch(iid, {"state": "closed", "state_reason": "completed"})
            self._remove_label(iid, self.in_progress_label)
            updated = self._get_raw(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to close issue #%s: %s", iid, exc)
            return False

        if updated.get("state") != "closed" or self.in_progress_label in self._labels(updated):
            logger.error("Issue #%s was NOT closed: state=%r, labels=%s.",
                         iid, updated.get("state"), self._labels(updated))
            return False
        logger.info("Issue #%s closed.", iid)
        return True

    def handoff_issue(self, iid: int, appendix: str) -> bool:
        """Append *appendix* to an open, unlabelled issue by a trusted author, then add the opt-in label."""
        raw = self._get_raw(iid)
        if raw.get("state") != "open" or self.issue_label in self._labels(raw) or "pull_request" in raw:
            logger.error("Issue #%s not handed off: closed, a pull request or already opted in.", iid)
            return False
        if reason := self._untrusted_author(raw):
            logger.error("Issue #%s not handed off: %s, so it would never be pending.", iid, reason)
            return False
        try:
            self._patch(iid, {"body": (raw.get("body") or "").rstrip() + "\n\n" + appendix.strip() + "\n"})
            self._add_label(iid, self.issue_label)
            updated = self._get_raw(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to hand off issue #%s: %s", iid, exc)
            return False
        if (updated.get("state") != "open"
                or self.issue_label not in self._labels(updated)
                or not _normalise_text(updated.get("body")).endswith(_normalise_text(appendix.strip()))):
            logger.error("Issue #%s hand-off did not read back.", iid)
            return False
        logger.info("Issue #%s handed off (label %r added).", iid, self.issue_label)
        return True

    def list_notes(self, iid: int) -> list[dict]:
        """Comments of issue *iid* by id; ``trusted`` for OWNER, MEMBER and COLLABORATOR authors."""
        comments = [c for page in self._pages(f"{self._repo_api}/issues/{iid}/comments") for c in page]
        return [
            {"id": c.get("id"), "author": (c.get("user") or {}).get("login"),
             "author_id": (c.get("user") or {}).get("id"),
             "created_at": c.get("created_at"), "body": c.get("body"),
             "trusted": c.get("author_association") in _TRUSTED_ASSOCIATIONS}
            for c in sorted(comments, key=lambda c: c.get("id") or 0)
        ]

    def post_note(self, iid: int, body: str) -> int:
        """Post one comment (fitted to the body limit), verify it by GET; return its id. Raises RuntimeError."""
        body = fit_body(body)
        response = self.session.post(
            f"{self._repo_api}/issues/{iid}/comments", json={"body": body}, timeout=_REQUEST_TIMEOUT
        )
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"Note on issue #{iid} failed: HTTP {response.status_code}")
        note_id = response.json().get("id")
        if not isinstance(note_id, int) or isinstance(note_id, bool) or note_id <= 0:
            raise RuntimeError(f"Note on issue #{iid} returned no id")
        check = self.session.get(f"{self._repo_api}/issues/comments/{note_id}", timeout=_REQUEST_TIMEOUT)
        _raise_for_status(check)
        if check.json().get("body") != body:
            raise RuntimeError(f"Note {note_id} on issue #{iid} did not read back")
        return note_id

    def reopen_issue(self, iid: int, note: str = "") -> bool:
        """
        Return the issue to the pending pool after a failed run (drop the lock label).

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
        if self.pause_label in self._labels(current):
            logger.warning("Refusing to reopen issue #%s: it carries %r.", iid, self.pause_label)
            return False

        if note:
            self._comment(iid, note)
        try:
            self._remove_label(iid, self.in_progress_label)
            updated = self._get_raw(iid)
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
        Hold an open, opted-in issue: add the pause label, then drop the lock.

        A closed or opted-out issue is left untouched (never reopened).
        """
        try:
            current = self._get_raw(iid)
            if not self._opted_in_open(current):
                logger.warning("Refusing to pause issue #%s: state=%r, labels=%s.",
                               iid, current.get("state"), self._labels(current))
                return False
            if note:
                self._comment(iid, note)
            self._add_label(iid, self.pause_label)
            self._remove_label(iid, self.in_progress_label)
            updated = self._get_raw(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to pause issue #%s: %s", iid, exc)
            return False

        labels = self._labels(updated)
        if (not self._opted_in_open(updated) or self.pause_label not in labels
                or self.in_progress_label in labels):
            logger.error("Issue #%s was NOT paused: state=%r, labels=%s.",
                         iid, updated.get("state"), labels)
            return False
        logger.info("Issue #%s paused (label %r added).", iid, self.pause_label)
        return True

    def resume_issue(self, iid: int) -> bool:
        """
        Release an open, opted-in issue: drop the lock, then the pause label.

        A closed or opted-out issue is left untouched (never reopened).
        """
        try:
            current = self._get_raw(iid)
            if not self._opted_in_open(current):
                logger.warning("Refusing to resume issue #%s: state=%r, labels=%s.",
                               iid, current.get("state"), self._labels(current))
                return False
            self._remove_label(iid, self.in_progress_label)
            self._remove_label(iid, self.pause_label)
            updated = self._get_raw(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to resume issue #%s: %s", iid, exc)
            return False

        labels = self._labels(updated)
        if (not self._opted_in_open(updated) or self.pause_label in labels
                or self.in_progress_label in labels):
            logger.error("Issue #%s was NOT resumed: state=%r, labels=%s.",
                         iid, updated.get("state"), labels)
            return False
        logger.info("Issue #%s resumed (control labels removed).", iid)
        return True

    def current_user_id(self) -> int:
        """The numeric id of the token's user (``GET /user``), cached per client."""
        if self._user_id is None:
            response = self.session.get(f"{self.base_url}/user", timeout=_REQUEST_TIMEOUT)
            _raise_for_status(response)
            user_id = response.json().get("id")
            if not isinstance(user_id, int) or isinstance(user_id, bool):
                raise RuntimeError("GitHub /user returned no numeric id")
            self._user_id = user_id
        return self._user_id

    def create_issue(
        self, title: str, description: str, labels: list[str] | None = None
    ) -> dict:
        """
        Create one issue (exactly one POST, never retried) and verify it.

        Returns the normalised read-back; raises RuntimeError on a non-2xx
        answer or a read-back that lacks the title, description or labels
        (GitHub silently drops labels for a token without push rights).
        """
        payload: dict = {"title": title, "body": description}
        if labels:
            payload["labels"] = list(labels)
        response = self.session.post(f"{self._repo_api}/issues", json=payload, timeout=_REQUEST_TIMEOUT)
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"Issue creation failed: HTTP {response.status_code}: {response.text[:300]}")
        number = response.json().get("number")
        if type(number) is not int or number <= 0:
            raise RuntimeError("Issue creation returned no number")
        issue = self.get_issue(number)
        missing = [label for label in labels or [] if label not in issue["labels"]]
        if (issue["subject"] != title
                or _normalise_text(issue["description"]) != _normalise_text(description)
                or missing):
            raise RuntimeError(f"Issue #{number} did not read back as created (missing labels: {missing})")
        logger.info("Created issue #%s: %s", number, title)
        return issue

    def swap_poll_heartbeat(self, value: str) -> str | None:
        """
        Write *value* to the repository's poll-heartbeat Actions variable; return the previous value.

        Needs the Variables write permission. Every orchestrator polling the
        repository writes here, so a foreign value reveals a second poller.
        """
        url = f"{self._repo_api}/actions/variables/{_POLL_HEARTBEAT_VARIABLE}"
        current = self.session.get(url, timeout=_REQUEST_TIMEOUT)
        if current.status_code == 404:
            _raise_for_status(self.session.post(
                f"{self._repo_api}/actions/variables",
                json={"name": _POLL_HEARTBEAT_VARIABLE, "value": value}, timeout=_REQUEST_TIMEOUT,
            ))
            return None
        _raise_for_status(current)
        previous = current.json().get("value")
        _raise_for_status(self.session.patch(
            url, json={"name": _POLL_HEARTBEAT_VARIABLE, "value": value}, timeout=_REQUEST_TIMEOUT
        ))
        return previous
