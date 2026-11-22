"""
test_github_client.py – GitHubClient against a local bare repository (clone,
initial commit, token-less remote, push verification, existing-branch rule)
and a fake HTTP session (PR open, 422 "already exists", 65,536 body limit,
signed pull_request plugin event).
No network.

Run:  .venv/bin/python test_github_client.py
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import git
import requests

_TOKEN = "github_pat_G2SecretToken"
os.environ.update({
    "NESTI_FORGE": "github", "NESTI_GITHUB_REPOSITORY": "acme/shop", "NESTI_GITHUB_TOKEN": _TOKEN,
    "NESTI_GITHUB_API_URL": "https://api.github.test", "NESTI_GITHUB_DEFAULT_BRANCH": "main",
    "NESTI_GIT_AUTHOR_NAME": "Nesti Bot", "NESTI_GIT_AUTHOR_EMAIL": "bot@example.invalid",
})
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "WARNING"))

import forge  # noqa: E402
import git_auth  # noqa: E402
import github_issues_client as ghc  # noqa: E402
from github_client import GitHubClient  # noqa: E402

_failures = 0


def check(condition: bool, message: str) -> None:
    global _failures
    print(("  ✓ " if condition else "  ✗ ") + message)
    if not condition:
        _failures += 1


class _Response:
    def __init__(self, payload, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.url = "https://api.github.test/fake"
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class _Session:
    """Answers each method from its queue and records every call."""

    def __init__(self, **queues):
        self.queues = {method: list(responses) for method, responses in queues.items()}
        self.calls = []

    def _call(self, method, url, params=None, json=None, **_):
        self.calls.append((method, url, params, json))
        return self.queues[method].pop(0)

    def get(self, url, **kw):
        return self._call("get", url, **kw)

    def post(self, url, **kw):
        return self._call("post", url, **kw)


def _setup(root, session=None):
    """An empty bare origin at <root>/acme/shop.git, cloned over file://, on an issue branch."""
    bare = git.Repo.init(Path(root, "acme", "shop.git"), bare=True, mkdir=True)
    with patch.dict(os.environ, {"NESTI_GITHUB_URL": f"file://{root}"}):
        client = GitHubClient()
    client._session = session or _Session()
    repo = client.clone(str(Path(root, "clone")))
    return bare, client, repo, client.create_branch(repo, 7, "Add thing")


def _sha(bare, branch):
    return bare.git.for_each_ref("--format=%(objectname)", f"refs/heads/{branch}")


def _leftover(repo, branch):
    """Push an earlier run's commit to *branch*, then reset the clone back to main."""
    Path(repo.working_tree_dir, "old.txt").write_text("old run")
    repo.git.add(A=True)
    repo.git.commit("-m", "leftover")
    repo.git.push("origin", f"{branch}:{branch}")
    sha = repo.head.commit.hexsha
    repo.git.reset("--hard", "main")
    return sha


def _raises(fn, exc=Exception):
    try:
        fn()
    except exc as error:
        return error
    return None


print("── clone, token-less remote, push ──")
with tempfile.TemporaryDirectory(prefix="nesti-g2-") as root:
    bare, client, repo, branch = _setup(root)
    check(len(list(bare.iter_commits("main"))) == 1 and repo.heads.main.commit.hexsha == _sha(bare, "main"),
          "an empty repository gets one empty initial commit on main, the clone's base")
    check(branch == "feature/issue-7-add-thing", "branch is feature/issue-<n>-<slug>")
    Path(repo.working_tree_dir, "thing.txt").write_text("thing")
    check(client.commit_and_push(repo, branch, "feat: thing") and _sha(bare, branch) == repo.head.commit.hexsha,
          "the issue branch is pushed and read back")
    check(repo.remote("origin").url == f"file://{root}/acme/shop.git"
          and _TOKEN not in Path(repo.git_dir, "config").read_text(),
          "the remote is {NESTI_GITHUB_URL}/owner/repo.git and .git/config holds no token")
    author = bare.commit(_sha(bare, branch)).author
    check((author.name, author.email) == ("Nesti Bot", "bot@example.invalid"),
          "NESTI_GIT_AUTHOR_NAME/EMAIL author the pushed commit")
    with patch.dict(os.environ, {"NESTI_GITHUB_URL": f"file://{root}"}):
        target = GitHubClient()
    repo.git.push("origin", "main:develop")
    target.default_branch = "develop"
    second = target.clone(str(Path(root, "second")))
    check(second.active_branch.name == "develop" and len(list(bare.iter_commits("main"))) == 1,
          "a non-empty clone checks out the configured target and adds no commit")

print("── auth header ──")
with patch.dict(os.environ, {"NESTI_GITHUB_URL": "https://github.test/"}):
    gh = GitHubClient()
basic = base64.b64encode(f"x-access-token:{_TOKEN}".encode()).decode()
header = f"Authorization: Basic {basic}"
check(gh._git_env == git_auth.env("https://github.test/", header) and gh.repo_url == "https://github.test/acme/shop.git",
      "git sends Basic base64(x-access-token:<token>), scoped to NESTI_GITHUB_URL; remote URL is token-less")
check(git.Git().config("--get-urlmatch", "http.extraHeader", "https://github.test/acme/shop.git",
                       env=gh._git_env) == header, "git resolves the header for the GitHub URL")
check(_raises(lambda: git.Git().config("--get-urlmatch", "http.extraHeader", "https://other.test/a.git",
                                       env=gh._git_env), git.GitCommandError) is not None,
      "the header is never configured for another host")
check(git_auth.redact(f"{header} {basic} {_TOKEN}", *gh._git_secrets) == "*** *** ***",
      "header, credential and token are redacted")
with patch.dict(os.environ, {"NESTI_GITHUB_URL": ""}):
    check(GitHubClient().repo_url == "https://github.com/acme/shop.git", "an empty NESTI_GITHUB_URL means github.com")

print("── rejected push, leftover branch, open PR ──")
with tempfile.TemporaryDirectory(prefix="nesti-g2-") as root:
    bare, client, repo, branch = _setup(root)
    hook = Path(bare.git_dir, "hooks", "pre-receive")
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    Path(repo.working_tree_dir, "thing.txt").write_text("thing")
    check(_raises(lambda: client.commit_and_push(repo, branch, "feat: thing"), RuntimeError) is not None
          and not _sha(bare, branch), "a push the remote rejects raises")

with tempfile.TemporaryDirectory(prefix="nesti-g2-") as root:
    bare, client, repo, branch = _setup(root)
    old = _leftover(repo, branch)
    Path(repo.working_tree_dir, "thing.txt").write_text("thing")
    stale = repo.heads.main.commit.hexsha
    real = client._remote_sha
    observed = iter([stale])
    client._session = _Session(get=[_Response([])])
    with patch.object(client, "_remote_sha", lambda r, ref: next(observed, None) or real(r, ref)):
        check(_raises(lambda: client.commit_and_push(repo, branch, "feat: thing")) is not None
              and _sha(bare, branch) == old, "the overwrite is leased: a moved remote branch is not clobbered")
    Path(repo.working_tree_dir, "thing2.txt").write_text("thing")
    client._session = _Session(get=[_Response([])])
    check(client.commit_and_push(repo, branch, "feat: thing") and _sha(bare, branch) == repo.head.commit.hexsha != old,
          "a leftover branch without an open PR is overwritten")

with tempfile.TemporaryDirectory(prefix="nesti-g2-") as root:
    bare, client, repo, branch = _setup(root)
    old = _leftover(repo, branch)
    url = "https://github.test/acme/shop/pull/9"
    session = _Session(get=[_Response([{"number": 9, "html_url": url}])])
    client._session = session
    Path(repo.working_tree_dir, "thing.txt").write_text("thing")
    error = _raises(lambda: client.commit_and_push(repo, branch, "feat: thing"), forge.OpenMergeRequestError)
    check(error is not None and error.url == url and _sha(bare, branch) == old,
          "an open PR on the branch raises OpenMergeRequestError(html_url) and nothing is pushed")
    check(session.calls[0][1] == "https://api.github.test/repos/acme/shop/pulls"
          and session.calls[0][2] == {"head": f"acme:{branch}", "state": "open"},
          "the lookup asks for open PRs with head=owner:branch")
    for n, answer in enumerate((_Response([{"number": 9}]), _Response({"message": "boom"}, 500))):
        client._session = _Session(get=[answer])
        Path(repo.working_tree_dir, f"more{n}.txt").write_text("thing")
        check(_raises(lambda: client.commit_and_push(repo, branch, "feat: more")) is not None
              and _sha(bare, branch) == old,
              f"{'a PR without html_url' if n == 0 else 'a failed lookup'} fails closed: nothing is pushed")

print("── open pull request ──")
pr = {"number": 12, "html_url": "https://github.test/acme/shop/pull/12"}
gh._session = _Session(post=[_Response(pr, 201)])
mr = gh.open_merge_request("feature/issue-7-add-thing", 7, "Add thing", "## Summary\nplan")
method, url, _, payload = gh._session.calls[0]
check(url == "https://api.github.test/repos/acme/shop/pulls"
      and payload == {"title": "[Issue #7] Add thing", "head": "feature/issue-7-add-thing", "base": "main",
                      "body": "Closes #7\n\n## Summary\nplan"},
      "POST /pulls with title, head, base = target branch and a Closes #N body; no branch-deletion setting")
check(mr["web_url"] == pr["html_url"] and mr["iid"] == 12, "the PR comes back MR-shaped (web_url, iid)")

gh._session = _Session(post=[_Response({"message": "Validation Failed", "errors": [
    {"message": "A pull request already exists for acme:feature/issue-7-add-thing."}]}, 422)],
    get=[_Response([pr])])
mr = gh.open_merge_request("feature/issue-7-add-thing", 7, "Add thing", "d")
check(mr["web_url"] == pr["html_url"]
      and gh._session.calls[1][2] == {"head": "acme:feature/issue-7-add-thing", "state": "open"},
      "422 already exists returns the open PR for owner:branch")

import graph.tools as tools  # noqa: E402
for answer, get, case in ((_Response({"message": "A pull request already exists for acme:b."}, 422), [_Response([])],
                           "422 already exists whose lookup finds no open PR"),
                          (_Response({"number": 12}, 201), [], "201 without html_url")):
    gh._session = _Session(post=[answer], get=get)
    with patch.object(tools.forge, "repo_client", lambda: gh):
        check(tools.tool_gitlab_open_mr("b", 7, "Add thing", "d")["success"] is False,
              f"{case} fails the open-MR tool")

provider = "**AI provider:** claude — subscription (model `opus`)"
gh._session = _Session(post=[_Response(pr, 201)])
gh.open_merge_request("b", 7, "Add thing", f"## Summary\n{provider}\n\n" + "z" * 70_000 + "\n\nTEST TAIL")
body = gh._session.calls[0][3]["body"]
check(len(body) <= ghc.BODY_LIMIT and body.startswith("Closes #7\n\n## Summary\n" + provider)
      and "(truncated)" in body and body.endswith("TEST TAIL"),
      "a >65,536 body is cut in the middle; Closes #N, the provider line and the test tail stay")

gh._session = _Session(post=[_Response({"message": "rate limited"}, 403, {"Retry-After": "60"})])
error = _raises(lambda: gh.open_merge_request("b", 7, "Add thing"), requests.HTTPError)
check(error is not None and "Retry-After=60" in str(error), "403 on PR open raises with GitHub's retry hint")

print("── pull_request plugin event ──")
_pull = {"number": 12, "state": "open", "draft": False, "author_association": "MEMBER",
         "user": {"login": "nesti-bot", "type": "User"}, "head": {"sha": "abc123"},
         "base": {"repo": {"full_name": "acme/shop"}}}
gh._session = _Session(get=[_Response(_pull), _Response(_pull)])
event_body, event_headers = gh.pull_request_event(12)
check(gh._session.calls[0][1] == "https://api.github.test/repos/acme/shop/pulls/12"
      and json.loads(event_body) == {
          "action": "opened", "repository": {"full_name": "acme/shop"},
          "pull_request": {"number": 12, "state": "open", "draft": False,
                           "user": {"login": "nesti-bot", "type": "User"}, "author_association": "MEMBER",
                           "head": {"sha": "abc123"}}},
      "the event is read from the PR API: real author, association, state, draft flag and head sha")
check(event_headers["X-GitHub-Event"] == "pull_request"
      and event_headers["X-GitHub-Delivery"] == "nesti-acme__shop-12-abc123"
      and gh.pull_request_event(12) == (event_body, event_headers),
      "event name and delivery id per GitHub; the same PR and head sha give the same bytes and id")
for _drop in (("user", "login"), ("author_association",), ("head", "sha"), ("draft",)):
    _broken = json.loads(json.dumps(_pull))
    _parent = _broken
    for _key in _drop[:-1]:
        _parent = _parent[_key]
    del _parent[_drop[-1]]
    gh._session = _Session(get=[_Response(_broken)])
    error = _raises(lambda: gh.pull_request_event(12), RuntimeError)
    check(error is not None and ".".join(_drop) in str(error), f"a PR without {'.'.join(_drop)} raises, never guessed")

_posts = []
with patch("requests.post", lambda url, **kw: _posts.append((url, kw))
           or _Response({"delivery": "d", "state": "queued"}, 202)):
    reply = GitHubClient.deliver_event("http://plugin.test/hook", event_body, event_headers, b"s3cret")
url, sent = _posts[0]
headers = sent["headers"]
check(url == "http://plugin.test/hook" and reply == {"delivery": "d", "state": "queued"} and sent["data"] is event_body,
      "the exact event bytes go to the subscription URL; the receiver's reply is returned")
check(headers["X-Hub-Signature-256"] == "sha256=" + hmac.new(b"s3cret", event_body, hashlib.sha256).hexdigest(),
      "the signature is HMAC-SHA256 over the exact sent bytes with the subscription's secret")
check("Authorization" not in headers and not any(_TOKEN in str(v) for v in sent.values())
      and sent["allow_redirects"] is False and sent["timeout"] <= 10,
      "the GitHub token never reaches a plugin; no redirects; a short timeout")


class _NotJson(_Response):
    def json(self):
        raise ValueError("Expecting value")


for answer, case in ((_Response({"error": "bad sig"}, 401), "a 401"),
                     (_Response({}, 302, {"Location": "http://elsewhere.test"}), "a redirect"),
                     (_NotJson("<html>", 200), "a non-JSON reply"),
                     (_Response(["queued"], 200), "a non-object reply")):
    with patch("requests.post", lambda url, **kw: answer):
        error = _raises(lambda: GitHubClient.deliver_event("http://plugin.test/hook", event_body, {}, b"s3cret"),
                        RuntimeError)
    check(error is not None and "s3cret" not in str(error), f"{case} raises, without the secret in the error")

print(f"\n{'All GitHub client checks passed.' if not _failures else f'{_failures} check(s) FAILED.'}")
sys.exit(1 if _failures else 0)
