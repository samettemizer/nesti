"""
GitLab client – handles all Git and GitLab operations.

Responsibilities:
- Clone the Hello World repository into the workspace.
- Create a feature branch named after the Redmine issue.
- Stage and commit the generated files.
- Push the branch to GitLab.
- Open a Merge Request via the GitLab REST API.

Authentication: personal access token (HTTPS) is the default.
SSH key auth can be used by setting GITLAB_REPO_SSH and GITLAB_USE_SSH=true.
"""

import logging
import os
import re

import git
import requests

logger = logging.getLogger(__name__)


_BRANCH_SLUG_MAX_LEN = 50


class GitLabClient:
    def __init__(self):
        self.gitlab_url = os.environ["GITLAB_URL"].rstrip("/")
        self.token = os.environ["GITLAB_TOKEN"]
        self.project_path = os.environ.get("GITLAB_PROJECT_PATH", "ai/hello-world")
        self.default_branch = os.environ.get("GITLAB_DEFAULT_BRANCH", "main")
        self.use_ssh = os.environ.get("GITLAB_USE_SSH", "false").lower() == "true"
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clone(self, target_path: str) -> git.Repo:
        """Clone the Hello World repo into *target_path* and return the Repo object."""
        clone_url = self.repo_url
        if not self.use_ssh:
            # Embed token for HTTPS auth
            clone_url = self._authenticated_https_url()
        # if gitlab is not in isolated environment; log will include access-token (clone-url)
        logger.info("Cloning %s into %s …", self.project_path, target_path)
        repo = git.Repo.clone_from(clone_url, target_path)
        repo.config_writer().set_value("user", "name", "AI Developer").release()
        repo.config_writer().set_value("user", "email", "ai-developer@yourdomain.com").release()
        return repo

    def create_branch(self, repo: git.Repo, issue_id: int, subject: str) -> str:
        """Create and check out a feature branch. Returns the branch name."""
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:_BRANCH_SLUG_MAX_LEN]
        branch_name = f"feature/issue-{issue_id}-{slug}"
        repo.git.checkout("-b", branch_name)
        logger.info("Created branch: %s", branch_name)
        return branch_name

    def commit_and_push(
        self, repo: git.Repo, branch_name: str, message: str
    ) -> bool:
        """Stage all changes, commit and push to origin."""
        repo.git.add(A=True)
        if not repo.index.diff("HEAD"):
            # Nothing staged
            logger.warning("No changes to commit.")
            return False
        repo.index.commit(message)
        origin = repo.remote("origin")
        if not self.use_ssh:
            origin.set_url(self._authenticated_https_url())
        origin.push(refspec=f"{branch_name}:{branch_name}")
        logger.info("Pushed branch %s to origin.", branch_name)
        return True

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
        payload = {
            "source_branch": branch_name,
            "target_branch": self.default_branch,
            "title": f"[Issue #{issue_id}] {subject}",
            "description": description or f"Closes Redmine issue #{issue_id}\n\n{subject}",
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

    def _authenticated_https_url(self) -> str:
        """Return HTTPS URL with embedded token for git operations."""
        base = self.gitlab_url
        # Insert oauth2:token@ before the host
        if "://" in base:
            scheme, rest = base.split("://", 1)
            return f"{scheme}://oauth2:{self.token}@{rest}/{self.project_path}.git"
        return f"https://oauth2:{self.token}@{base}/{self.project_path}.git"
