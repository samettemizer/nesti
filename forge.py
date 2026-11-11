"""
The forge (GitLab or GitHub) this process acts on: client contracts, client
factory, display words, the failed-run marker and the acted-on project.

Forge-specific code lives only here and in ``*_client.py``; everything else
builds its clients through ``issue_client()`` / ``repo_client()`` and names the
forge through ``term()``. ``NESTI_FORGE`` selects the forge (default ``gitlab``).

The orchestrator acts on ``GITLAB_PROJECT_PATH`` (GitHub: ``NESTI_GITHUB_REPOSITORY``) from ``.env``. An MCP server
process serves one client connection and acts on that client's project, read
from the client checkout's git remote (``bind_client``); without a resolvable
remote it refuses project tools instead of falling back to ``.env``.
"""

import hashlib
import json
import logging
import os
import re
from typing import Protocol
from urllib.parse import quote, urlsplit

import git
import requests

logger = logging.getLogger(__name__)

_TERMS = {
    "gitlab": {"forge": "GitLab", "mr": "MR", "merge_request": "Merge Request"},
    "github": {"forge": "GitHub", "mr": "PR", "merge_request": "Pull Request"},
}
FAILED_RUN_RE = re.compile(r"^<!-- NESTI_FAILED_RUN_V1 [0-9a-f]{64} -->$", re.M)

# None in the orchestrator; in an MCP process {"path": ..., "default_branch"?: ...} or {"error": ...}.
_bound: dict | None = None


class IssueClient(Protocol):
    """Issue intake and lifecycle surface the pipeline uses (``GitLabIssuesClient``, ``GitHubIssuesClient``)."""

    issue_label: str
    in_progress_label: str
    pause_label: str
    project_path: str

    def get_issue(self, iid: int) -> dict: ...
    def project_info(self) -> dict:
        """The forge's project record; carries at least ``path_with_namespace``, ``default_branch``, ``issues_enabled``."""
    def list_issues(self, *, state: str = "opened", labels: list[str] | None = None) -> list[dict]: ...
    def list_pending(self, limit: int = 25) -> list[dict]: ...
    def get_next_issue(self) -> dict | None: ...
    def lock_issue(self, iid: int) -> bool: ...
    def close_issue(self, iid: int, note: str = "", require_note: bool = False) -> bool: ...
    def reopen_issue(self, iid: int, note: str = "") -> bool: ...
    def pause_issue(self, iid: int, note: str = "") -> bool: ...
    def resume_issue(self, iid: int) -> bool: ...
    def handoff_issue(self, iid: int, appendix: str) -> bool: ...
    def list_notes(self, iid: int) -> list[dict]: ...
    def post_note(self, iid: int, body: str) -> int: ...
    def current_user_id(self) -> int: ...
    def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> dict: ...
    def swap_poll_heartbeat(self, value: str) -> str | None: ...


class RepoClient(Protocol):
    """Repository and merge-request surface the pipeline uses (``GitLabClient``)."""

    default_branch: str

    def clone(self, target_path: str) -> git.Repo: ...
    def create_branch(self, repo: git.Repo, issue_id: int, subject: str) -> str: ...
    def commit_and_push(self, repo: git.Repo, branch_name: str, message: str) -> bool: ...
    def open_merge_request(
        self, branch_name: str, issue_id: int, subject: str, description: str = ""
    ) -> dict | None: ...


class OpenMergeRequestError(RuntimeError):
    """The issue branch is already under an open merge/pull request; nothing was pushed."""

    def __init__(self, message: str, url: str) -> None:
        super().__init__(message)
        self.url = url


def kind() -> str:
    """The configured forge (``NESTI_FORGE``, default ``gitlab``); ``ValueError`` for an unsupported one."""
    value = os.environ.get("NESTI_FORGE", "").strip().lower() or "gitlab"
    if value not in _TERMS:
        raise ValueError(f"NESTI_FORGE={value!r} is not supported; use one of: {', '.join(_TERMS)}")
    return value


def term(key: str) -> str:
    """The forge's display word: ``forge`` → "GitLab", ``mr`` → "MR", ``merge_request`` → "Merge Request"."""
    return _TERMS[kind()][key]


def failed_run_marker(subject: str, description: str, head_sha: str) -> str:
    """The hidden note line fingerprinting a failed run's title, description and target HEAD."""
    digest = hashlib.sha256(json.dumps([subject, description, head_sha]).encode()).hexdigest()
    return f"<!-- NESTI_FAILED_RUN_V1 {digest} -->"


def issue_client() -> IssueClient:
    """A fresh issue client for the configured forge."""
    if kind() == "github":
        from github_issues_client import GitHubIssuesClient  # clients import this module

        return GitHubIssuesClient()
    from gitlab_issues_client import GitLabIssuesClient  # clients import this module

    return GitLabIssuesClient()


def repo_client() -> RepoClient:
    """A fresh repository client for the configured forge."""
    if kind() == "github":
        raise ValueError(
            "NESTI_FORGE=github: the GitHub repository client (github_client.py, package G2) does not exist yet"
        )
    from gitlab_client import GitLabClient  # clients import this module

    return GitLabClient()


def project_from_remote(remote: str, gitlab_url: str) -> str:
    """Return ``namespace/…/project`` for a git remote on ``gitlab_url``'s host; ``ValueError`` otherwise."""
    remote = remote.strip()
    if not remote:
        raise ValueError("no git remote was passed")
    if "://" in remote:
        parts = urlsplit(remote)
        host, path = parts.hostname or "", parts.path
    else:
        match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", remote)
        if not match:
            raise ValueError("the git remote is neither a URL nor host:path")
        host, path = match.groups()
    gitlab = urlsplit(gitlab_url)
    if host.lower() != (gitlab.hostname or "").lower():
        raise ValueError(
            f"the git remote is on {host or 'an unknown host'}, not on GITLAB_URL's {gitlab.hostname}"
        )
    path = path.strip("/")
    if (prefix := gitlab.path.strip("/")) and path.startswith(prefix + "/"):
        path = path[len(prefix) + 1:]
    path = path.removesuffix(".git").strip("/")
    # GitLab paths are [A-Za-z0-9_.-] segments; anything else (e.g. `*`, `[ab]`) would glob Redis keys.
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+", path):
        raise ValueError(f"the git remote path {path!r} is not a GitLab namespace/project path")
    return path


def bind_client(remote: str) -> None:
    """Bind this (MCP) process to the GitLab project of the client's git remote, or to an error."""
    global _bound
    try:
        _bound = {"path": project_from_remote(remote, os.environ["GITLAB_URL"])}
        logger.info("Nesti MCP acts on the client's project %s.", identity())
    except (KeyError, ValueError) as exc:
        _bound = {
            "error": f"Nesti MCP does not know this client's GitLab project: {exc}. "
            "Start it with `nesti mcp` inside the project's git checkout."
        }
        logger.warning(_bound["error"])


def client_bound() -> bool:
    """True in an MCP process bound to a client (successfully or not)."""
    return _bound is not None


def path() -> str:
    """The acted-on project's ``namespace/project`` path; raises ``ValueError`` for an unresolved client."""
    if _bound is None:
        return os.environ["NESTI_GITHUB_REPOSITORY" if kind() == "github" else "GITLAB_PROJECT_PATH"]
    if "error" in _bound:
        raise ValueError(_bound["error"])
    return _bound["path"]


def default_branch() -> str:
    """The acted-on project's target branch: ``.env`` for the orchestrator, GitLab's default for a client."""
    if _bound is None:
        if kind() == "github":
            return os.environ.get("NESTI_GITHUB_DEFAULT_BRANCH", "main")
        return os.environ.get("GITLAB_DEFAULT_BRANCH", "main")
    project = path()
    if "default_branch" not in _bound:
        response = requests.get(
            f"{os.environ['GITLAB_URL'].rstrip('/')}/api/v4/projects/{quote(project, safe='')}",
            headers={"PRIVATE-TOKEN": os.environ["GITLAB_TOKEN"]},
            verify=os.environ.get("GITLAB_SSL_VERIFY", "true").lower() != "false",
            timeout=15,
        )
        response.raise_for_status()
        _bound["default_branch"] = response.json()["default_branch"] or "main"
    return _bound["default_branch"]


def identity() -> str:
    """``host/namespace/project`` in lower case, e.g. ``gitlab.com/acme/shop``; scopes Redis records."""
    if _bound is None and kind() == "github":
        url = os.environ.get("NESTI_GITHUB_URL", "https://github.com")
    else:
        url = os.environ["GITLAB_URL"]
    return f"{urlsplit(url).hostname}/{path()}".lower()
