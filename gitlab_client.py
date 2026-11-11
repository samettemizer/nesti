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
import re

import git
import requests

import forge
import git_auth

logger = logging.getLogger(__name__)


_BRANCH_SLUG_MAX_LEN = 50


class GitLabClient:
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clone(self, target_path: str) -> git.Repo:
        """
        Clone the configured repository into *target_path* and return the Repo.

        The configured target branch (GITLAB_DEFAULT_BRANCH) is checked out
        explicitly rather than the server's default HEAD: a merge request
        targets that branch, and a parent resumed after its fixture dependency
        merged must start from the branch that carries the merge.

        An empty project (no branches) gets one empty commit pushed to the
        default branch, so issue branches have a base to branch from and merge into.
        """
        url = self.repo_url
        logger.info("Cloning %s (%s) into %s …", self.project_path, self.default_branch, target_path)
        with git_auth.redacted(*self._git_secrets):
            empty = not git.cmd.Git().ls_remote("--heads", url, env=self._git_env).strip()
            if empty:
                repo = git.Repo.clone_from(url, target_path, env=self._git_env)
            else:
                repo = git.Repo.clone_from(url, target_path, branch=self.default_branch, env=self._git_env)
            name = os.environ.get("NESTI_GIT_AUTHOR_NAME") or "AI Developer"
            email = os.environ.get("NESTI_GIT_AUTHOR_EMAIL") or "nesti@yourdomain.com"
            repo.config_writer().set_value("user", "name", name).release()
            repo.config_writer().set_value("user", "email", email).release()
            if empty:
                repo.git.symbolic_ref("HEAD", f"refs/heads/{self.default_branch}")
                repo.git.commit("--allow-empty", "-m", "Initial commit")
                # raise_if_error: a refused push (protected branch) must stop the run, not branch off nothing.
                repo.remote("origin").push(
                    refspec=f"{self.default_branch}:{self.default_branch}", env=self._git_env
                ).raise_if_error()
                logger.info("Empty repository: pushed an empty initial commit to %s", self.default_branch)
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
        """
        Stage all changes, commit and push to origin; False when nothing changed.

        A branch already on the remote is either under an open merge request
        (raises ``forge.OpenMergeRequestError``, nothing is pushed) or left over
        from an earlier run (overwritten, leased to the observed remote SHA).
        The push is verified by reading the remote branch back.
        """
        repo.git.add(A=True)
        if not repo.index.diff("HEAD"):
            # Nothing staged
            logger.warning("No changes to commit.")
            return False
        repo.index.commit(message)
        ref = f"refs/heads/{branch_name}"
        with git_auth.redacted(*self._git_secrets):
            observed = self._remote_sha(repo, ref)
            lease = {}
            if observed:
                mr_url = self._open_merge_request_url(branch_name)
                if mr_url:
                    raise forge.OpenMergeRequestError(
                        f"Branch {branch_name} already has an open {forge.term('mr')}: {mr_url}; not pushing.",
                        mr_url,
                    )
                lease = {"force_with_lease": f"{branch_name}:{observed}"}
                logger.info("Overwriting leftover remote branch %s (%s).", branch_name, observed)
            repo.remote("origin").push(
                refspec=f"{branch_name}:{branch_name}", env=self._git_env, **lease
            ).raise_if_error()
            pushed = self._remote_sha(repo, ref)
        if pushed != repo.head.commit.hexsha:
            raise RuntimeError(
                f"Push of {branch_name} not applied: remote is at {pushed or 'nothing'}, "
                f"local HEAD is {repo.head.commit.hexsha}."
            )
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

    def _remote_sha(self, repo: git.Repo, ref: str) -> str:
        """The SHA of *ref* on origin, or "" when origin has no such ref."""
        line = repo.git.ls_remote("origin", ref, env=self._git_env)
        return line.split()[0] if line else ""

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
