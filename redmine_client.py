"""
Redmine client – task intake gateway.

Responsibilities:
- Fetch the last pending (new) issue from the configured Redmine project.
- Lock the issue by updating its status so another worker cannot pick it up.
- Provide issue details consumed by the orchestrator.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


class RedmineClient:
    def __init__(self):
        self.base_url = os.environ["REDMINE_URL"].rstrip("/")
        self.api_key = os.environ["REDMINE_API_KEY"]
        self.project_id = os.environ.get("REDMINE_PROJECT_ID", "hello-world")
        self.new_status_id = int(os.environ.get("REDMINE_NEW_STATUS_ID", "1"))
        self.in_progress_status_id = int(
            os.environ.get("REDMINE_IN_PROGRESS_STATUS_ID", "2")
        )
        self.closed_status_id = int(os.environ.get("REDMINE_CLOSED_STATUS_ID", "5"))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Redmine-API-Key": self.api_key,
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_next_issue(self) -> dict | None:
        """Return the oldest open/new issue for the project, or None."""
        params = {
            "project_id": self.project_id,
            "status_id": self.new_status_id,
            "sort": "id:asc",
            "limit": 1,
        }
        response = self.session.get(
            f"{self.base_url}/issues.json", params=params, timeout=15
        )
        response.raise_for_status()
        data = response.json()
        issues = data.get("issues", [])
        if not issues:
            logger.info("No pending issues found in Redmine.")
            return None
        issue = issues[0]
        logger.info("Fetched issue #%s: %s", issue["id"], issue["subject"])
        return issue

    def lock_issue(self, issue_id: int) -> bool:
        """Mark the issue as 'in progress' so it is not picked up again."""
        payload = {"issue": {"status_id": self.in_progress_status_id}}
        response = self.session.put(
            f"{self.base_url}/issues/{issue_id}.json",
            json=payload,
            timeout=15,
        )
        if response.status_code in (200, 204):
            logger.info("Issue #%s locked (status → in-progress).", issue_id)
            return True
        logger.warning(
            "Failed to lock issue #%s – HTTP %s", issue_id, response.status_code
        )
        return False

    def close_issue(self, issue_id: int, note: str = "") -> bool:
        """Mark the issue as closed with an optional note."""
        payload: dict = {"issue": {"status_id": self.closed_status_id}}
        if note:
            payload["issue"]["notes"] = note
        response = self.session.put(
            f"{self.base_url}/issues/{issue_id}.json",
            json=payload,
            timeout=15,
        )
        if response.status_code in (200, 204):
            logger.info("Issue #%s closed.", issue_id)
            return True
        logger.warning(
            "Failed to close issue #%s – HTTP %s", issue_id, response.status_code
        )
        return False

    def reopen_issue(self, issue_id: int, note: str = "") -> bool:
        """Reset the issue back to 'new' status on failure."""
        payload: dict = {"issue": {"status_id": self.new_status_id}}
        if note:
            payload["issue"]["notes"] = note
        response = self.session.put(
            f"{self.base_url}/issues/{issue_id}.json",
            json=payload,
            timeout=15,
        )
        if response.status_code in (200, 204):
            logger.info("Issue #%s reopened (status → new).", issue_id)
            return True
        logger.warning(
            "Failed to reopen issue #%s – HTTP %s", issue_id, response.status_code
        )
        return False
