"""
GitLab Issues client – task intake gateway.

Replaces the former Redmine intake. Responsibilities:
- Fetch the oldest pending issue from the configured GitLab project.
- Lock it so another worker cannot pick it up.
- Close it on success and return it to the pending pool on failure.

Why GitLab Issues have no "in progress" state
─────────────────────────────────────────────
GitLab issues are only ``opened`` or ``closed``, so the three-state intake
model lives in labels:

    <label>                    the opt-in marker a developer adds ("nesti")
    <label>::in-progress       the lock Nesti owns

    pending      = opened, has <label>, does NOT have <label>::in-progress
    in progress  = opened, has <label>::in-progress
    done         = closed

``<label>`` comes from GITLAB_ISSUE_LABEL (default "nesti"), so Nesti never
touches an issue a human opened for discussion: intake is opt-in.

Scoped labels (the ``::`` form) are mutually exclusive within their scope in
GitLab, which is what makes the lock single-valued.

Every mutation is verified by reading the issue back. The Redmine intake this
replaces trusted the HTTP status and silently stranded issues when a workflow
rule dropped the change; a lock or unlock that did not apply must be loud.
"""

import logging
import os
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

_DEFAULT_ISSUE_LABEL = "nesti"
_IN_PROGRESS_SUFFIX = "::in-progress"
_REQUEST_TIMEOUT = 15
_PER_PAGE = 100


class GitLabIssuesClient:
    """Issue intake and lifecycle against the GitLab Issues API."""

    def __init__(self) -> None:
        self.base_url = os.environ["GITLAB_URL"].rstrip("/")
        self.token = os.environ["GITLAB_TOKEN"]
        self.project_path = os.environ["GITLAB_PROJECT_PATH"]
        self.issue_label = (
            os.environ.get("GITLAB_ISSUE_LABEL", _DEFAULT_ISSUE_LABEL).strip()
            or _DEFAULT_ISSUE_LABEL
        )
        self.in_progress_label = f"{self.issue_label}{_IN_PROGRESS_SUFFIX}"

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
        return {
            "id": issue["iid"],
            "subject": issue.get("title", "") or "",
            "description": issue.get("description", "") or "",
            "iid": issue["iid"],
            "global_id": issue.get("id"),
            "state": issue.get("state"),
            "labels": issue.get("labels", []),
            "web_url": issue.get("web_url", ""),
            "author": (issue.get("author") or {}).get("username", ""),
        }

    def _get_raw(self, iid: int) -> dict:
        response = self.session.get(
            f"{self._project_api}/issues/{iid}", timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    def _update(self, iid: int, payload: dict) -> dict:
        response = self.session.put(
            f"{self._project_api}/issues/{iid}", json=payload, timeout=_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, iid: int) -> dict:
        """Fetch one issue by its project-scoped iid, in intake shape."""
        return self._normalise(self._get_raw(iid))

    def list_pending(self, limit: int = 25) -> list[dict]:
        """
        Return pending issues, oldest first.

        GitLab cannot express "has label A but not label B" in one query, so
        the opt-in label is filtered server-side and the lock is filtered
        client-side.
        """
        response = self.session.get(
            f"{self._project_api}/issues",
            params={
                "state": "opened",
                "labels": self.issue_label,
                "order_by": "created_at",
                "sort": "asc",
                "per_page": min(limit, _PER_PAGE),
            },
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        pending = [
            self._normalise(issue)
            for issue in response.json()
            if self.in_progress_label not in (issue.get("labels") or [])
        ]
        return pending[:limit]

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
        Claim the issue by adding the in-progress label.

        ``add_labels`` is used instead of replacing ``labels`` so a
        concurrently added human label is never dropped.
        """
        try:
            updated = self._update(iid, {"add_labels": self.in_progress_label})
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to lock issue #%s: %s", iid, exc)
            return False

        if self.in_progress_label not in (updated.get("labels") or []):
            logger.error(
                "Issue #%s was NOT locked: the label %r is still absent. Another "
                "worker may have taken it, or the token lacks Reporter rights on "
                "%s.",
                iid, self.in_progress_label, self.project_path,
            )
            return False
        logger.info("Issue #%s locked (label %r added).", iid, self.in_progress_label)
        return True

    def close_issue(self, iid: int, note: str = "") -> bool:
        """Comment, drop the lock label and close the issue."""
        if note:
            self._comment(iid, note)
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

        if updated.get("state") != "closed":
            logger.error(
                "Issue #%s was NOT closed: GitLab still reports state %r.",
                iid, updated.get("state"),
            )
            return False
        logger.info("Issue #%s closed.", iid)
        return True

    def reopen_issue(self, iid: int, note: str = "") -> bool:
        """
        Return the issue to the pending pool after a failed run.

        Dropping the in-progress label is what actually makes it pending again;
        ``state_event=reopen`` only matters when a previous run closed it. The
        opt-in label is re-added defensively: without it the issue would leave
        the queue silently and never be retried.
        """
        if note:
            self._comment(iid, note)
        try:
            updated = self._update(
                iid,
                {
                    "remove_labels": self.in_progress_label,
                    "add_labels": self.issue_label,
                    "state_event": "reopen",
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to reopen issue #%s: %s", iid, exc)
            return False

        labels = updated.get("labels") or []
        if updated.get("state") != "opened" or self.in_progress_label in labels:
            logger.error(
                "Issue #%s was NOT returned to the pending pool: state=%r, "
                "labels=%s. It will not be picked up again until the %r label "
                "is removed by hand.",
                iid, updated.get("state"), labels, self.in_progress_label,
            )
            return False
        logger.info("Issue #%s returned to pending (lock label removed).", iid)
        return True
