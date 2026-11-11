"""
GitHub client – the GitHub counterpart of ``gitlab_client.py``.

Clone, branch and push are the shared ``git_auth.GitRepoClient`` flow over a
token-less HTTPS remote ``{NESTI_GITHUB_URL}/{owner}/{repo}.git``; the token
travels as a per-call ``Authorization: Basic base64("x-access-token:<token>")``
header scoped to ``NESTI_GITHUB_URL``. Pull requests go through the REST API
with the issue client's session (``github_issues_client.api_session``).

What differs from GitLab:

- A PR body is limited to 65,536 characters; ``fit_body`` cuts the middle, so
  ``Closes #N`` and the provider line at the top survive.
- Opening a PR for a head that already has one answers 422 "already exists";
  the open PR is looked up and returned.
- Deleting the head branch on merge is a repository setting; Nesti never
  touches it.
"""

import base64
import logging
import os

import forge
import git_auth
from github_issues_client import api_session, api_url, fit_body, raise_for_status

logger = logging.getLogger(__name__)

_DEFAULT_URL = "https://github.com"
_REQUEST_TIMEOUT = 30


class GitHubClient(git_auth.GitRepoClient):
    """Repository and pull-request operations against GitHub (``forge.RepoClient``)."""

    def __init__(self) -> None:
        self.github_url = (os.environ.get("NESTI_GITHUB_URL") or _DEFAULT_URL).rstrip("/")
        token = os.environ["NESTI_GITHUB_TOKEN"]
        self.project_path = forge.path()
        self.default_branch = forge.default_branch()
        self.repo_url = f"{self.github_url}/{self.project_path}.git"
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        header = f"Authorization: Basic {basic}"
        self._git_secrets = (header, basic, token)
        self._git_env = git_auth.env(f"{self.github_url}/", header)
        self._session = api_session()
        self._repo_api = f"{api_url()}/repos/{self.project_path}"

    def open_merge_request(
        self,
        branch_name: str,
        issue_id: int,
        subject: str,
        description: str = "",
    ) -> dict | None:
        """Open a pull request (or return the one already open for the branch) as an MR-shaped dict."""
        payload = {
            "title": f"[Issue #{issue_id}] {subject}",
            "head": branch_name,
            "base": self.default_branch,
            "body": fit_body(f"Closes #{issue_id}\n\n{description or subject}"),
        }
        response = self._session.post(f"{self._repo_api}/pulls", json=payload, timeout=_REQUEST_TIMEOUT)
        if response.status_code in (200, 201):
            pr = self._mr_shape(response.json())
            if not pr["web_url"]:
                raise RuntimeError(f"{forge.term('mr')} opened from {branch_name} came back without an html_url.")
        elif response.status_code == 422 and "already exists" in response.text:
            pr = self._open_pull(branch_name)
        else:
            logger.error("Failed to open PR – HTTP %s: %s", response.status_code, response.text[:200])
            raise_for_status(response)
            return None
        if pr:
            logger.info("Pull Request opened: %s", pr["web_url"])
        return pr

    @staticmethod
    def _mr_shape(pr: dict) -> dict:
        """The PR plus the merge-request keys the pipeline reads (``web_url``, ``iid``)."""
        return {**pr, "web_url": pr.get("html_url") or "", "iid": pr.get("number")}

    def _open_pull(self, branch_name: str) -> dict | None:
        """The open PR from *branch_name*, or None; raises when the lookup fails or the PR has no link."""
        owner = self.project_path.split("/", 1)[0]
        response = self._session.get(
            f"{self._repo_api}/pulls",
            params={"head": f"{owner}:{branch_name}", "state": "open"},
            timeout=_REQUEST_TIMEOUT,
        )
        raise_for_status(response)
        pulls = response.json()
        if not pulls:
            return None
        pr = self._mr_shape(pulls[0])
        if not pr["web_url"]:
            # An open PR without its link must stop the run, never fall through to a force push.
            raise RuntimeError(f"Open {forge.term('mr')} from {branch_name} has no html_url; not pushing.")
        return pr

    def _open_merge_request_url(self, branch_name: str) -> str | None:
        """html_url of an open pull request from *branch_name*, or None."""
        pr = self._open_pull(branch_name)
        return pr["web_url"] if pr else None
