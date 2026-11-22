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
import hashlib
import hmac
import json
import logging
import os

import requests

import forge
import git_auth
from github_issues_client import api_session, api_url, fit_body, raise_for_status

logger = logging.getLogger(__name__)

_DEFAULT_URL = "https://github.com"
_REQUEST_TIMEOUT = 30
_EVENT_TIMEOUT = 10


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

    def pull_request_event(self, pr_number: int) -> tuple[bytes, dict]:
        """
        GitHub's ``pull_request`` webhook (``action=opened``) for PR *pr_number*: the exact body bytes and
        the unsigned headers.  Every value is read from the API; a missing one raises, never guessed.
        """
        response = self._session.get(f"{self._repo_api}/pulls/{pr_number}", timeout=_REQUEST_TIMEOUT)
        raise_for_status(response)
        pr = response.json()

        def field(*keys: str):
            value = pr
            for key in keys:
                value = value.get(key) if isinstance(value, dict) else None
            if value is None or value == "":
                raise RuntimeError(f"{forge.term('mr')} #{pr_number} has no {'.'.join(keys)} in GitHub's answer.")
            return value

        repo, head_sha = field("base", "repo", "full_name"), field("head", "sha")
        body = json.dumps({
            "action": "opened",
            "repository": {"full_name": repo},
            "pull_request": {
                "number": pr_number, "state": field("state"), "draft": field("draft"),
                "user": {"login": field("user", "login"), "type": field("user", "type")},
                "author_association": field("author_association"),
                "head": {"sha": head_sha},
            },
        }).encode()
        return body, {
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": f"nesti-{repo.replace('/', '__')}-{pr_number}-{head_sha}",
        }

    @staticmethod
    def deliver_event(url: str, body: bytes, headers: dict, secret: bytes) -> dict:
        """POST *body* signed with *secret* (``X-Hub-Signature-256``) to *url*; the receiver's JSON object reply."""
        signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
        # Plain requests, never self._session: the GitHub token must not reach a plugin.
        response = requests.post(url, data=body, timeout=_EVENT_TIMEOUT, allow_redirects=False,
                                 headers={**headers, "X-Hub-Signature-256": f"sha256={signature}"})
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"the receiver answered HTTP {response.status_code}: {response.text[:200]}")
        try:
            reply = response.json()
        except ValueError as exc:
            raise RuntimeError(f"the receiver answered non-JSON: {response.text[:200]}") from exc
        if not isinstance(reply, dict):
            raise RuntimeError(f"the receiver answered a non-object: {response.text[:200]}")
        return reply
