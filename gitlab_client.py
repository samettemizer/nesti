"""
GitLab client – handles all Git and GitLab operations.

Responsibilities:
- Clone the Hello World repository into the workspace.
- Create a feature branch named after the issue.
- Stage and commit the generated files.
- Push the branch to GitLab.
- Open a Merge Request via the GitLab REST API.

Authentication: personal access token (HTTPS) is the default; it travels as a
per-call http.extraHeader (git_auth), never in the remote URL or .git/config.
SSH key auth can be used by setting GITLAB_REPO_SSH and GITLAB_USE_SSH=true.
"""

import base64
import logging
import os

import requests

import forge
import git_auth

logger = logging.getLogger(__name__)


class GitLabClient(git_auth.GitRepoClient):
    def __init__(self):
        self.gitlab_url = os.environ["GITLAB_URL"].rstrip("/")
        self.token = os.environ["GITLAB_TOKEN"]
        self.project_path = forge.path()
        self.default_branch = forge.default_branch()
        # GITLAB_REPO_SSH names the orchestrator's project; a bound MCP client clones its own over HTTPS.
        self.use_ssh = (
            os.environ.get("GITLAB_USE_SSH", "false").lower() == "true"
            and not forge.client_bound()
        )
        self.repo_url = (
            os.environ.get("GITLAB_REPO_SSH")
            if self.use_ssh
            else self._https_clone_url()
        )
        self._session = requests.Session()
        self._session.headers.update(
            {"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"}
        )
        self._session.verify = os.environ.get("GITLAB_SSL_VERIFY", "true").lower() != "false"
        # install.sh authenticates its first clone with the same header.
        basic = base64.b64encode(f"oauth2:{self.token}".encode()).decode()
        header = f"Authorization: Basic {basic}"
        self._git_secrets = (header, basic, self.token)
        self._git_env = {} if self.use_ssh else git_auth.env(f"{self.gitlab_url}/", header)

    def open_merge_request(
        self,
        branch_name: str,
        issue_id: int,
        subject: str,
        description: str = "",
    ) -> dict | None:
        """Open a GitLab Merge Request and return the MR dict, or None on failure."""
        encoded_path = requests.utils.quote(self.project_path, safe="")
        url = f"{self.gitlab_url}/api/v4/projects/{encoded_path}/merge_requests"
        # "Closes #N" is a GitLab closing keyword: it cross-links the MR to the
        # issue in the UI and closes the issue when the MR is merged. Now that
        # issues live in the same GitLab project as the code, that linkage is
        # native — under Redmine it could only ever be a plain-text mention.
        payload = {
            "source_branch": branch_name,
            "target_branch": self.default_branch,
            "title": f"[Issue #{issue_id}] {subject}",
            "description": f"Closes #{issue_id}\n\n{description or subject}",
            "remove_source_branch": True,
        }
        response = self._session.post(url, json=payload, timeout=30)
        if response.status_code in (200, 201):
            mr = response.json()
            logger.info("Merge Request opened: %s", mr.get("web_url"))
            return mr
        logger.error(
            "Failed to open MR – HTTP %s: %s",
            response.status_code,
            response.text[:200],
        )
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _https_clone_url(self) -> str:
        return f"{self.gitlab_url}/{self.project_path}.git"

    def _open_merge_request_url(self, branch_name: str) -> str | None:
        """web_url of an open merge request from *branch_name*, or None."""
        encoded_path = requests.utils.quote(self.project_path, safe="")
        response = self._session.get(
            f"{self.gitlab_url}/api/v4/projects/{encoded_path}/merge_requests",
            params={"source_branch": branch_name, "state": "opened"},
            timeout=30,
        )
        response.raise_for_status()
        mrs = response.json()
        if not mrs:
            return None
        url = mrs[0].get("web_url")
        if not url:
            # An open MR without its link must stop the run, never fall through to a force push.
            raise RuntimeError(f"Open {forge.term('mr')} from {branch_name} has no web_url; not pushing.")
        return url
