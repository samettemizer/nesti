"""
test_issue_clients.py – one contract scenario suite run against both issue
clients (``GitLabIssuesClient`` and ``GitHubIssuesClient``) over an in-memory
fake HTTP session, plus the GitHub-only rules (label API, trust, body limit,
rate limits). No network.

Run:  .venv/bin/python test_issue_clients.py
"""

import json
import logging
import os
import sys
from copy import deepcopy
from unittest.mock import patch
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

import requests

os.environ["GITLAB_URL"] = "https://gitlab.test"
os.environ["GITLAB_TOKEN"] = "t"
os.environ["GITLAB_PROJECT_PATH"] = "ai/hello-world"
os.environ["GITLAB_ISSUE_LABEL"] = "nesti"
os.environ["NESTI_GITHUB_REPOSITORY"] = "acme/shop"
os.environ["NESTI_GITHUB_TOKEN"] = "t"
os.environ["NESTI_GITHUB_API_URL"] = "https://api.github.test"
os.environ["NESTI_GITHUB_ISSUE_LABEL"] = "nesti"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
os.environ.pop("NESTI_FORGE", None)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "WARNING"))

import forge  # noqa: E402
import github_issues_client as ghc  # noqa: E402
import gitlab_issues_client as glc  # noqa: E402
import graph.tools as tools  # noqa: E402
import issue_domain  # noqa: E402
from github_client import GitHubClient  # noqa: E402

NESTI_USER = 15
_failures = 0


def check(condition: bool, message: str) -> None:
    global _failures
    print(("  ✓ " if condition else "  ✗ ") + message)
    if not condition:
        _failures += 1


class _Response:
    def __init__(self, payload, status=200, headers=None, links=None, url=""):
        self._payload = deepcopy(payload)
        self.status_code = status
        self.headers = headers or {}
        self.links = links or {}
        self.url = url
        self.text = json.dumps(payload)

    def json(self):
        return deepcopy(self._payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class Store:
    """Forge-neutral issue tracker state behind both fake dialects."""

    def __init__(self):
        self.issues: dict[int, dict] = {}
        self.notes: dict[int, list[dict]] = {}
        self.variables: dict[str, str] = {}
        self.head: str | None = "h1"
        self.requests: list[tuple] = []
        self.apply_writes = True
        self.mangle_notes = False
        self.drop_create_labels = False
        self.failures: dict[tuple[str, str], tuple[int, dict]] = {}
        self.note_id = 100

    def add_issue(self, n, labels=("nesti",), state="open", body="", assoc="MEMBER", pr=False):
        self.issues[n] = {"n": n, "title": f"Issue {n}", "body": body, "state": state,
                          "labels": list(labels), "assoc": assoc, "pr": pr}
        return self.issues[n]

    def add_note(self, n, body, author=NESTI_USER, assoc="MEMBER"):
        self.note_id += 1
        note = {"id": self.note_id, "body": body, "author": author, "assoc": assoc}
        self.notes.setdefault(n, []).append(note)
        return note

    def fail(self, method, fragment, status=500, headers=None):
        self.failures[(method, fragment)] = (status, headers or {})

    def failure(self, method, url):
        for (m, fragment), (status, headers) in self.failures.items():
            if m == method and fragment in url:
                return _Response({"message": "injected"}, status, headers, url=url)
        return None


class _Fake:
    """Session double: logs every call, applies injected failures, dispatches to the dialect."""

    def __init__(self, store: Store):
        self.store = store
        self.headers = {}

    def _call(self, method, url, params=None, json=None, **_):
        self.store.requests.append((method, urlsplit(url).path, deepcopy(params), deepcopy(json)))
        return self.store.failure(method, url) or self.dispatch(method, url, params or {}, json)

    def get(self, url, **kw):
        return self._call("GET", url, **kw)

    def post(self, url, **kw):
        return self._call("POST", url, **kw)

    def put(self, url, **kw):
        return self._call("PUT", url, **kw)

    def patch(self, url, **kw):
        return self._call("PATCH", url, **kw)

    def delete(self, url, **kw):
        return self._call("DELETE", url, **kw)

    def _write(self, n, change):
        candidate = deepcopy(self.store.issues[n])
        change(candidate)
        if self.store.apply_writes:
            self.store.issues[n] = candidate

    def _create(self, title, body, labels):
        n = max(self.store.issues, default=0) + 1
        issue = self.store.add_issue(n, [] if self.store.drop_create_labels else labels, body=body)
        issue["title"] = title
        return n

    def _posted_note(self, n, body):
        note = self.store.add_note(n, body)
        if self.store.mangle_notes:
            note["body"] = body + " (edited)"
        return note


class GitLabFake(_Fake):
    UNLOCK = ("PUT", "/issues/")

    def _issue(self, i):
        return {"iid": i["n"], "id": i["n"] + 1000, "project_id": 63, "title": i["title"],
                "description": i["body"], "labels": list(i["labels"]),
                "state": "opened" if i["state"] == "open" else i["state"],
                "web_url": f"https://gitlab.test/issues/{i['n']}",
                "author": {"id": 20, "username": "dev"}}

    @staticmethod
    def _note(n):
        return {"id": n["id"], "body": n["body"], "system": False,
                "author": {"id": n["author"], "username": f"u{n['author']}"}, "created_at": "t"}

    @staticmethod
    def _page(items, params):
        page = int(params.get("page", 1))
        return _Response(items[page - 1:page], headers={"X-Next-Page": str(page + 1) if page < len(items) else ""})

    def dispatch(self, method, url, params, body):
        path = unquote(urlsplit(url).path).split("/projects/ai/hello-world", 1)[-1]
        s = self.store
        if path == "/api/v4/user":
            return _Response({"id": NESTI_USER})
        if path == "":
            return _Response({"path_with_namespace": "ai/hello-world", "default_branch": "main",
                              "issues_enabled": True})
        if path.startswith("/repository/branches/"):
            return _Response({}, 404) if s.head is None else _Response({"commit": {"id": s.head}})
        if path.startswith("/variables"):
            name = path.removeprefix("/variables").strip("/") or body.get("key")
            if method == "GET":
                return _Response({"value": s.variables[name]}) if name in s.variables else _Response({}, 404)
            s.variables[name] = body["value"]
            return _Response({}, 201)
        parts = path.removeprefix("/issues").strip("/").split("/") if path.startswith("/issues") else None
        if parts == [""]:
            if method == "POST":
                n = self._create(body["title"], body["description"],
                                 [x for x in body.get("labels", "").split(",") if x])
                return _Response(self._issue(s.issues[n]), 201)
            state = {"opened": "open"}.get(params.get("state"), params.get("state"))
            wanted = [x for x in (params.get("labels") or "").split(",") if x]
            items = [self._issue(i) for _, i in sorted(s.issues.items())
                     if (state == "all" or i["state"] == state) and all(x in i["labels"] for x in wanted)]
            return self._page(items, params)
        n = int(parts[0])
        if len(parts) == 1 and method == "GET":
            return _Response(self._issue(s.issues[n]))
        if len(parts) == 1 and method == "PUT":
            def change(i):
                for x in (body.get("remove_labels") or "").split(","):
                    if x in i["labels"]:
                        i["labels"].remove(x)
                for x in (body.get("add_labels") or "").split(","):
                    if x and x not in i["labels"]:
                        i["labels"].append(x)
                if "state_event" in body:
                    i["state"] = "closed" if body["state_event"] == "close" else "open"
                if "description" in body:
                    i["body"] = body["description"]
            self._write(n, change)
            return _Response(self._issue(s.issues[n]))
        if parts[1] == "notes":
            if method == "POST":
                return _Response(self._note(self._posted_note(n, body["body"])), 201)
            notes = [self._note(x) for x in s.notes.get(n, [])]
            if len(parts) == 3:
                return _Response(next(x for x in notes if x["id"] == int(parts[2])))
            return self._page(notes, params)
        raise AssertionError(f"Unexpected GitLab {method} {url}")


class GitHubFake(_Fake):
    UNLOCK = ("DELETE", "/labels/")
    BASE = "https://api.github.test/repos/acme/shop"

    def _issue(self, i):
        record = {"number": i["n"], "id": i["n"] + 5000, "title": i["title"], "body": i["body"] or None,
                  "state": i["state"], "labels": [{"name": x} for x in i["labels"]],
                  "html_url": f"https://github.test/acme/shop/issues/{i['n']}",
                  "user": {"id": 20, "login": "dev"}, "author_association": i["assoc"]}
        if i["pr"]:
            record["pull_request"] = {"url": "x"}
        return record

    @staticmethod
    def _note(n):
        return {"id": n["id"], "body": n["body"], "created_at": "t", "author_association": n["assoc"],
                "user": {"id": n["author"], "login": f"u{n['author']}"}}

    def _page(self, path, items, query):
        page = int(query.get("page", 1))
        links = {}
        if page < len(items):
            links["next"] = {"url": f"https://api.github.test{path}?{urlencode({**query, 'page': page + 1})}"}
        return _Response(items[page - 1:page], links=links)

    def dispatch(self, method, url, params, body):
        split = urlsplit(url)
        query = {**dict(parse_qsl(split.query)), **{k: str(v) for k, v in params.items()}}
        path = split.path.split("/repos/acme/shop", 1)[-1]
        s = self.store
        if split.path == "/user":
            return _Response({"id": NESTI_USER})
        if path == "":
            return _Response({"full_name": "acme/shop", "default_branch": "main", "has_issues": True})
        if path.startswith("/branches/"):
            return _Response({}, 404) if s.head is None else _Response({"commit": {"sha": s.head}})
        if path.startswith("/actions/variables"):
            name = path.removeprefix("/actions/variables").strip("/") or body.get("name")
            if method == "GET":
                return _Response({"name": name, "value": s.variables[name]}) if name in s.variables \
                    else _Response({}, 404)
            if method == "PATCH" and name not in s.variables:
                return _Response({}, 404)
            s.variables[name] = body["value"]
            return _Response({}, 201 if method == "POST" else 204)
        if path.startswith("/issues/comments/"):
            note = next(x for notes in s.notes.values() for x in notes if x["id"] == int(path.rsplit("/", 1)[1]))
            return _Response(self._note(note))
        parts = path.removeprefix("/issues").strip("/").split("/") if path.startswith("/issues") else None
        if parts == [""]:
            if method == "POST":
                n = self._create(body["title"], body["body"], body.get("labels", []))
                return _Response(self._issue(s.issues[n]), 201)
            wanted = [x for x in query.get("labels", "").split(",") if x]
            items = [self._issue(i) for _, i in sorted(s.issues.items())
                     if (query["state"] == "all" or i["state"] == query["state"])
                     and all(x in i["labels"] for x in wanted)]
            return self._page(split.path, items, query)
        n = int(parts[0])
        if len(parts) == 1 and method == "GET":
            return _Response(self._issue(s.issues[n]))
        if len(parts) == 1 and method == "PATCH":
            def change(i):
                i["state"] = body.get("state", i["state"])
                i["body"] = body.get("body", i["body"])
            self._write(n, change)
            return _Response(self._issue(s.issues[n]))
        if parts[1] == "labels" and method == "POST":
            self._write(n, lambda i: i["labels"].extend(x for x in body["labels"] if x not in i["labels"]))
            return _Response(self._issue(s.issues[n])["labels"])
        if parts[1] == "labels" and method == "DELETE":
            name = unquote(parts[2])
            if name not in s.issues[n]["labels"]:
                return _Response({"message": "Label does not exist"}, 404)
            self._write(n, lambda i: i["labels"].remove(name))
            return _Response(self._issue(s.issues[n])["labels"])
        if parts[1] == "comments":
            if method == "POST":
                return _Response(self._note(self._posted_note(n, body["body"])), 201)
            return self._page(split.path, [self._note(x) for x in s.notes.get(n, [])], query)
        raise AssertionError(f"Unexpected GitHub {method} {url}")


FORGES = {
    "gitlab": (glc.GitLabIssuesClient, GitLabFake),
    "github": (ghc.GitHubIssuesClient, GitHubFake),
}


def make(forge_name: str, store: Store):
    client_class, fake_class = FORGES[forge_name]
    client = client_class()
    client.session = fake_class(store)
    return client


def scenarios(name: str) -> None:
    """The forge-neutral contract, run once per client."""
    os.environ["NESTI_FORGE"] = name
    print(f"\n── {name}: contract scenarios ──")
    fake_class = FORGES[name][1]

    s = Store()
    s.add_issue(7, ["nesti", "nesti::in-progress", "bug"])
    s.add_issue(8, ["nesti", "nesti::pause"])
    s.add_issue(9, ["nesti", "human"])
    s.add_issue(10, [])
    s.add_issue(11, state="closed")
    s.add_issue(12)
    s.add_issue(13)
    s.add_note(12, "failed\n\n" + forge.failed_run_marker("Issue 12", "", "h1"))
    s.add_note(13, forge.failed_run_marker("Issue 13", "", "h1"), author=99)
    c = make(name, s)
    check([i["id"] for i in c.list_pending(1)] == [9], "limit 1 passes locked and paused pages")
    s.requests.clear()
    pending = c.list_pending()
    check([i["id"] for i in pending] == [9, 13],
          "control labels, missing opt-in, closed and an unchanged failed run are not pending; "
          "a stranger's marker does not count")
    check(sum(r[0] == "GET" and r[1].endswith("/issues") for r in s.requests) > 1,
          "the list is followed across pages")
    check(sum("branches/" in r[1] for r in s.requests) == 1, "target HEAD is read once per poll")
    check(set(pending[0]) >= {"id", "iid", "subject", "description", "state", "labels", "web_url",
                              "author", "author_id", "global_id", "project_id"}
          and pending[0]["state"] == "opened" and pending[0]["subject"] == "Issue 9",
          "intake dict shape, state 'opened'")
    s.head = "h2"
    check([i["id"] for i in c.list_pending()] == [9, 12, 13], "a new target HEAD makes the failed issue pending")
    s.head = None
    check([i["id"] for i in c.list_pending()] == [9, 12, 13], "a missing target branch matches no marker")
    s.head = "h1"
    check(c.get_next_issue()["id"] == 9, "next issue is the oldest pending one")
    check(c.project_info()["path_with_namespace"] and c.project_info()["issues_enabled"] is True,
          "project_info carries path_with_namespace and issues_enabled")

    print(f"── {name}: lock / reopen ──")
    check(c.lock_issue(9) and set(s.issues[9]["labels"]) == {"nesti", "human", "nesti::in-progress"},
          "lock adds the in-progress label and keeps the human label")
    check(not c.lock_issue(9), "an already locked issue is refused")
    check(not c.lock_issue(8) and not c.lock_issue(10) and not c.lock_issue(11),
          "paused, unlabelled and closed issues are refused")
    check(c.reopen_issue(9) and set(s.issues[9]["labels"]) == {"nesti", "human"},
          "reopen drops only the lock label")
    s.apply_writes = False
    check(not c.lock_issue(9), "a write the read-back does not show fails the lock")
    s.apply_writes = True

    print(f"── {name}: close ──")
    c.lock_issue(9)
    check(c.close_issue(9, note="Merged") and s.issues[9]["state"] == "closed"
          and "nesti::in-progress" not in s.issues[9]["labels"] and s.notes[9][-1]["body"] == "Merged",
          "close posts the note, closes and unlocks")
    c.lock_issue(13)
    s.fail("POST", "/notes" if name == "gitlab" else "/comments")
    check(not c.close_issue(13, note="Merged", require_note=True) and s.issues[13]["state"] == "open",
          "a failed required note leaves the issue open")
    s.failures.clear()
    s.fail(*fake_class.UNLOCK)
    check(not c.close_issue(13), "a half-done close reports failure")
    s.failures.clear()
    check(13 not in [i["id"] for i in c.list_pending()], "a half-done close never returns the issue to pending")

    print(f"── {name}: pause / resume ──")
    s.add_issue(20, ["nesti", "nesti::in-progress"])
    check(c.pause_issue(20, note="Which domain?")
          and set(s.issues[20]["labels"]) == {"nesti", "nesti::pause"}, "pause swaps lock for pause")
    check(not c.reopen_issue(20), "crash recovery cannot undo a pause")
    s.issues[20]["labels"].append("urgent")
    check(c.resume_issue(20) and set(s.issues[20]["labels"]) == {"nesti", "urgent"},
          "resume drops both control labels and keeps a concurrently added label")
    s.issues[20]["state"] = "closed"
    check(not c.pause_issue(20) and not c.resume_issue(20) and not c.reopen_issue(20),
          "a human-closed issue is never resurrected")
    s.issues[20].update(state="open", labels=["human"])
    check(not c.pause_issue(20) and not c.resume_issue(20) and not c.reopen_issue(20),
          "a manual opt-out is never reversed")

    print(f"── {name}: handoff / notes / create ──")
    s.add_issue(21, [], body="Do X.")
    check(c.handoff_issue(21, "## Appendix\nmore") and "nesti" in s.issues[21]["labels"]
          and s.issues[21]["body"].rstrip().endswith("more"), "handoff appends and opts in")
    check(not c.handoff_issue(21, "again"), "an opted-in issue is not handed off again")
    note_id = c.post_note(21, "hello")
    check(note_id == s.notes[21][-1]["id"], "post_note returns the read-back id")
    notes = c.list_notes(21)
    check([set(n) for n in notes] == [{"id", "author", "author_id", "created_at", "body", "trusted"}]
          and notes[0]["trusted"] is True, "note dict shape with trusted")
    s.mangle_notes = True
    try:
        c.post_note(21, "hello")
        check(False, "a note that reads back different raises")
    except RuntimeError:
        check(True, "a note that reads back different raises")
    s.mangle_notes = False
    created = c.create_issue("Probe", "Body.", labels=["nesti"])
    check(created["subject"] == "Probe" and created["labels"] == ["nesti"] and created["state"] == "opened",
          "create_issue returns the read-back")
    s.drop_create_labels = True
    try:
        c.create_issue("Probe", "Body.", labels=["nesti"])
        check(False, "a silently dropped label fails create_issue")
    except RuntimeError as exc:
        check("missing labels" in str(exc), "a silently dropped label fails create_issue")
    s.drop_create_labels = False

    print(f"── {name}: heartbeat ──")
    check(c.swap_poll_heartbeat("a") is None and s.variables == {"NESTI_POLL_HEARTBEAT": "a"},
          "a missing heartbeat variable is created")
    check(c.swap_poll_heartbeat("b") == "a" and s.variables["NESTI_POLL_HEARTBEAT"] == "b",
          "the swap returns the previous heartbeat")
    s.fail("GET", "variables", 403)
    try:
        c.swap_poll_heartbeat("c")
        check(False, "no Variables permission raises (task_engine warns once and continues)")
    except requests.HTTPError:
        check(True, "no Variables permission raises (task_engine warns once and continues)")


def github_only() -> None:
    os.environ["NESTI_FORGE"] = "github"
    print("\n── github: forge selection ──")
    with patch.dict(os.environ, {"NESTI_GITHUB_REPOSITORY": "Acme/Shop", "NESTI_GITHUB_URL": ""}):
        os.environ.pop("NESTI_GITHUB_URL")
        check(forge.kind() == "github" and forge.term("mr") == "PR"
              and forge.term("merge_request") == "Pull Request" and forge.term("forge") == "GitHub",
              "NESTI_FORGE=github selects the GitHub words")
        check(forge.identity() == "github.com/acme/shop" and forge.default_branch() == "main",
              "identity is github.com/owner/repo in lower case; default branch main")
        os.environ["NESTI_GITHUB_URL"] = ""
        check(forge.identity() == "github.com/acme/shop", "an empty NESTI_GITHUB_URL counts as unset")
    check(isinstance(forge.issue_client(), ghc.GitHubIssuesClient), "issue_client builds GitHubIssuesClient")
    check(isinstance(forge.repo_client(), GitHubClient), "repo_client builds GitHubClient")
    gh = forge.issue_client().session.headers
    check(gh["Authorization"] == "Bearer t" and gh["Accept"] == "application/vnd.github+json"
          and gh["X-GitHub-Api-Version"], "Bearer token, GitHub media type and pinned API version")

    print("── github: label API, order, records ──")
    s = Store()
    s.add_issue(30, pr=True)
    s.add_issue(31)
    c = make("github", s)
    check([i["id"] for i in c.list_pending()] == [31] and [i["id"] for i in c.list_issues()] == [31],
          "pull request records are never issues")
    check(not c.lock_issue(30), "a pull request is never locked")
    check(c.get_issue(31)["state"] == "opened" and c.get_issue(31)["description"] == "",
          "open → opened, null body → ''")
    s.requests.clear()
    c.lock_issue(31)
    c.close_issue(31, note="Merged")
    writes = [(r[0], r[1].rsplit("/", 1)[-1]) for r in s.requests if r[0] != "GET"]
    check(writes == [("POST", "labels"), ("POST", "comments"), ("PATCH", "31"),
                     ("DELETE", "nesti%3A%3Ain-progress")],
          "lock POSTs the label; close: comment → PATCH state → DELETE lock (URL-encoded)")
    s.add_issue(32, ["nesti", "nesti::in-progress"])
    s.requests.clear()
    c.pause_issue(32)
    c.resume_issue(32)
    writes = [(r[0], unquote(r[1].rsplit("/", 1)[-1])) for r in s.requests if r[0] != "GET"]
    check(writes == [("POST", "labels"), ("DELETE", "nesti::in-progress"),
                     ("DELETE", "nesti::in-progress"), ("DELETE", "nesti::pause")],
          "pause: POST pause → DELETE lock; resume: DELETE lock → DELETE pause")
    s.add_issue(33, [])
    s.requests.clear()
    c.handoff_issue(33, "more")
    check([r[0] for r in s.requests if r[0] != "GET"] == ["PATCH", "POST"], "handoff: PATCH body → POST label")
    s.add_issue(34, ["nesti", "nesti::in-progress"])
    c.reopen_issue(34, note="failed")
    everything = s.requests
    check(not any(r[0] == "PUT" for r in everything)
          and not any(r[0] == "PATCH" and "labels" in (r[3] or {}) for r in everything),
          "no call ever replaces the label set (no PUT, no PATCH with labels)")

    print("── github: 65,536-character limit ──")
    marker = forge.failed_run_marker("Issue 34", "", "h1")
    long_note = "x" * 70_000 + "\n\n" + marker
    c.post_note(34, long_note)
    body = s.notes[34][-1]["body"]
    check(len(body) <= ghc.BODY_LIMIT and body.endswith("\n" + marker) and "(truncated)" in body,
          "post_note cuts the middle and keeps the trailing marker line")
    c.lock_issue(34)
    c.reopen_issue(34, note=long_note)
    body = s.notes[34][-1]["body"]
    check(len(body) <= ghc.BODY_LIMIT and body.endswith(marker), "transition notes are fitted the same way")
    check(ghc.fit_body("short\n" + marker) == "short\n" + marker, "a body within the limit is untouched")
    padded = "y" * (ghc.BODY_LIMIT - 10) + " " * 100
    check(ghc.fit_body(padded) == "y" * (ghc.BODY_LIMIT - 10),
          "a body over the limit only by trailing whitespace is just stripped, never duplicated")

    print("── github: trust ──")
    s = Store()
    s.add_issue(40, assoc="NONE")
    s.add_issue(41, assoc="CONTRIBUTOR")
    s.add_issue(42, assoc="COLLABORATOR")
    s.add_issue(43, [], assoc="NONE")
    c = make("github", s)
    with patch.object(ghc.logger, "info") as info:
        pending = [i["id"] for i in c.list_pending()]
    check(pending == [42], "only OWNER/MEMBER/COLLABORATOR authors are pending")
    check(sum("is not pending" in str(call.args[0]) and call.args[1] in (40, 41)
              for call in info.call_args_list) == 2, "each untrusted skip is logged with its reason")
    check(not c.lock_issue(40), "an untrusted author's issue is never locked")
    check(not c.handoff_issue(43, "more") and "nesti" not in s.issues[43]["labels"],
          "an untrusted author's issue is not handed off")
    s.add_issue(44, ["nesti", "nesti::pause"])
    c.post_note(44, issue_domain.format_question(["Announcements", "Members"]))
    s.add_note(44, "Members", author=99, assoc="NONE")
    result = issue_domain.reconcile(c)
    check(result["waiting"] == [44] and result["asked"] == [] and "nesti::pause" in s.issues[44]["labels"],
          "an untrusted reply neither resolves nor re-asks the domain question")
    check(issue_domain.answer(c.list_notes(44), NESTI_USER, ["Announcements", "Members"]) == [],
          "answer ignores untrusted replies")
    s.add_note(44, "2", author=98, assoc="MEMBER")
    check(issue_domain.reconcile(c)["resumed"] == [44] and s.issues[44]["labels"] == ["nesti"],
          "a trusted reply resumes the issue")

    print("── github: rate limits ──")
    for status, headers, hint in ((403, {"X-RateLimit-Reset": "1700000000"}, "X-RateLimit-Reset=1700000000"),
                                  (429, {"Retry-After": "60"}, "Retry-After=60")):
        s.fail("GET", "/repos/acme/shop/issues", status, headers)
        try:
            c.list_pending()
            check(False, f"HTTP {status} on the list raises")
        except requests.HTTPError as exc:
            check(hint in str(exc) and exc.response.status_code == status,
                  f"HTTP {status} on the list raises with {hint}")
        with patch.object(tools.forge, "issue_client", lambda: c):
            check(tools.tool_issue_list_pending()["success"] is False,
                  f"HTTP {status}: tool_issue_list_pending fails, so the poll is skipped")
        s.failures.clear()


def gitlab_default() -> None:
    os.environ.pop("NESTI_FORGE", None)
    print("\n── NESTI_FORGE unset ──")
    check(forge.kind() == "gitlab" and forge.term("mr") == "MR"
          and isinstance(forge.issue_client(), glc.GitLabIssuesClient)
          and forge.identity() == "gitlab.test/ai/hello-world", "GitLab stays the default")


for _name in FORGES:
    scenarios(_name)
github_only()
gitlab_default()

print(f"\n{'All issue-client checks passed.' if not _failures else f'{_failures} check(s) FAILED.'}")
sys.exit(1 if _failures else 0)
