"""
test_update.py – host-side `nesti update` (scripts/nesti_update.py) against
temporary local Git repositories: a local "upstream" stands in for GitHub,
the release API is mocked, Docker and pip calls go to a recording fake runner.
Also the notice cache and the real launcher routing (fake `docker`, stub
nesti_update.py, a PTY for the terminal checks). No network, Docker or tokens.

Run:  .venv/bin/python tests/test_update.py
"""

import ast
import contextlib
import io
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import nesti_update as nu  # noqa: E402

_failures = 0
_TMP = tempfile.TemporaryDirectory(prefix="nesti-update-test-")
BASE = Path(_TMP.name)
_gitconfig = BASE / "gitconfig"
_gitconfig.write_text("")
os.environ.update({
    "GIT_CONFIG_GLOBAL": str(_gitconfig), "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
})
os.environ.pop("NO_COLOR", None)
os.environ.pop("NESTI_NO_UPDATE_CHECK", None)


def check(condition, message):
    global _failures
    print(("  ✓ " if condition else "  ✗ ") + message)
    if not condition:
        _failures += 1


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, tag=None, annotated=False):
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        git(repo, "init", "-q", "-b", "main")
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c")
    if tag:
        git(repo, "tag", *(["-a", "-m", tag] if annotated else []), tag)
    return git(repo, "rev-parse", "HEAD")


# ---------------------------------------------------------------------------
print("[1] Version parsing and comparison")
check(nu.parse_version("v1.2.3") == (1, 2, 3) and nu.parse_version("v0.10.0") == (0, 10, 0), "stable vX.Y.Z parses")
check(all(nu.parse_version(t) is None for t in ("v0.5.2-rc", "0.5.3", "v1.2", "v1.2.3\n", "v1.2.3.4", None, 3)),
      "rc/pre tags, missing v and malformed tags are rejected")
check(nu.parse_version("v0.10.0") > nu.parse_version("v0.9.9"), "comparison is numeric: v0.10.0 > v0.9.9")
source = (REPO / "scripts" / "nesti_update.py").read_text()
try:
    ast.parse(source, feature_version=(3, 6))
    check("capture_output" not in source and "text=True" not in source, "nesti_update.py keeps Python 3.6 syntax and APIs")
except SyntaxError as exc:
    check(False, "nesti_update.py keeps Python 3.6 syntax: %s" % exc)

# ---------------------------------------------------------------------------
print("\n[2] Installed version from ancestor tags")
tags = BASE / "tags"
commit(tags, {"a": "1"}, "v0.5.2")
commit(tags, {"a": "2"}, "v0.5.2-rc", annotated=True)
commit(tags, {"a": "3"}, "v0.9.9")
commit(tags, {"a": "4"}, "v0.10.0", annotated=True)
git(tags, "switch", "-q", "-c", "side")
commit(tags, {"a": "side"}, "v0.12.0")
git(tags, "switch", "-q", "main")
commit(tags, {"a": "5"}, "v0.11.0-rc")
check(nu.installed_version(str(tags)) == "v0.10.0", "newest stable ancestor wins; rc on HEAD and a sibling branch's tag are ignored")
untagged = BASE / "untagged"
commit(untagged, {"a": "1"})
plain = BASE / "plain"
plain.mkdir()
check(nu.installed_version(str(untagged)) is None and nu.installed_version(str(plain)) is None,
      "no tag or no repository: unknown, no exception")

# ---------------------------------------------------------------------------
print("\n[3] Release JSON")
release = {"tag_name": "v0.6.0", "draft": False, "prerelease": False, "html_url": "x"}
check(nu.parse_release(release) == "v0.6.0", "published release yields its tag")
check(all(nu.parse_release(d) is None for d in (dict(release, prerelease=True), dict(release, draft=True),
                                                 dict(release, tag_name="v0.6.0-rc1"), [release], "x", None, {})),
      "prerelease, draft, rc tag and malformed payloads yield nothing")
with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release).encode())) as opened:
    latest = nu.fetch_latest(7)
request = opened.call_args[0][0]
check(latest == "v0.6.0" and request.full_url == nu.API_URL
      and request.full_url == "https://api.github.com/repos/samettemizer/nesti/releases/latest"
      and opened.call_args[1]["timeout"] == 7 and request.get_header("User-agent") == "nesti-update",
      "fetch_latest reads releases/latest with a timeout and a User-Agent")
not_found = urllib.error.HTTPError(nu.API_URL, 404, "Not Found", {}, None)
with mock.patch("urllib.request.urlopen", side_effect=not_found):
    check(nu.fetch_latest(1) is None, "HTTP 404: no release published")
for failure in (urllib.error.HTTPError(nu.API_URL, 403, "rate limited", {}, None), urllib.error.URLError("offline"),
                OSError("timed out")):
    with mock.patch("urllib.request.urlopen", side_effect=failure):
        try:
            nu.fetch_latest(1)
            check(False, "%s raises UpdateError" % type(failure).__name__)
        except nu.UpdateError:
            check(True, "%s raises UpdateError" % type(failure).__name__)
with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(b"<html>")):
    try:
        nu.fetch_latest(1)
        check(False, "invalid JSON raises UpdateError")
    except nu.UpdateError:
        check(True, "invalid JSON raises UpdateError")

# ---------------------------------------------------------------------------
print("\n[4] Decision")
check(nu.update_status("v0.5.3", "v0.6.0") == "available", "newer release: available")
check(nu.update_status("v0.6.0", "v0.6.0") == "current" and nu.update_status("v0.10.0", "v0.9.9") == "current",
      "same or older release: current")
check(nu.update_status(None, "v0.6.0") == "unknown" and nu.update_status(None, None) == "current"
      and nu.update_status("v0.5.3", None) == "current", "unknown installed version; no release is current")


# ---------------------------------------------------------------------------
class FakeRunner:
    """Records Docker/pip calls; `fail` maps an argv prefix (tuple) to an exit status."""

    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail or {}

    def __call__(self, argv, cwd, env=None):
        self.calls.append({"argv": list(argv), "cwd": cwd, "env": env})
        for prefix, code in self.fail.items():
            if tuple(argv[:len(prefix)]) == prefix:
                return code, "output of %s\n" % " ".join(argv)
        return 0, ""

    def argvs(self):
        return [c["argv"] for c in self.calls]


APPLY_STUB = ('import json, os, sys\n'
              'open(os.environ["APPLY_MARKER"], "w").write(json.dumps([os.path.abspath(__file__)] + sys.argv[1:]))\n')
GITIGNORE = "state/*\n.env\nlogs/\n.private/\n.venv/\n"
PERSONAL = {".env": "TOKEN=secret\n", ".private/plugins/x": "p", "state/keep.json": "{}", "logs/run.log": "l",
            ".venv/marker": "v", "notes.txt": "untracked"}


def make_install(name):
    """upstream: v0.5.3 then an annotated v0.6.0 whose nesti_update.py is APPLY_STUB; install: a clone at v0.5.3."""
    upstream = BASE / name / "upstream"
    commit(upstream, {"README.md": "v1\n", ".gitignore": GITIGNORE, "scripts/nesti_update.py": "raise SystemExit(9)\n"},
           "v0.5.3")
    install = BASE / name / "install"
    git(BASE, "clone", "-q", str(upstream), str(install))
    git(install, "remote", "set-url", "origin", "git@github-main:samettemizer/nesti.git")  # unreachable SSH alias
    release_commit = commit(upstream, {"README.md": "v2\n", "scripts/nesti_update.py": APPLY_STUB}, "v0.6.0", annotated=True)
    for rel, content in PERSONAL.items():
        (install / rel).parent.mkdir(parents=True, exist_ok=True)
        (install / rel).write_text(content)
    return upstream, install, release_commit


def run_main(root, argv, upstream=None, latest="v0.6.0", runner=None, which=None):
    runner = runner or FakeRunner()
    marker = BASE / "apply-marker.json"
    if marker.exists():
        marker.unlink()
    fetch = mock.patch.object(nu, "fetch_latest", side_effect=latest) if isinstance(latest, Exception) \
        else mock.patch.object(nu, "fetch_latest", return_value=latest)
    with fetch, mock.patch.object(nu, "SOURCE_URL", str(upstream or BASE / "missing")), \
            mock.patch.object(nu, "_run", runner), mock.patch.object(nu.shutil, "which", return_value=which), \
            mock.patch.object(nu.time, "sleep"), mock.patch.dict(os.environ, {"APPLY_MARKER": str(marker)}), \
            contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        code = nu.main(argv, root=str(root))
    applied = json.loads(marker.read_text()) if marker.exists() else None
    return code, out.getvalue(), err.getvalue(), runner, applied


def snapshot(install):
    return (git(install, "rev-parse", "HEAD"), git(install, "status", "--porcelain"), git(install, "tag", "--list"),
            {rel: (install / rel).read_text() for rel in PERSONAL}, (install / "README.md").read_text(),
            sorted(os.listdir(install / "state")))


# ---------------------------------------------------------------------------
print("\n[5] nesti update --check")
upstream, install, release_commit = make_install("check")
before = snapshot(install)
code, out, err, runner, _ = run_main(install, ["update", "--check"], upstream)
check(code == nu.EXIT_AVAILABLE == 3 and "Installed: v0.5.3" in out and "Latest:    v0.6.0" in out
      and "nesti update" in out, "newer release: exit 3 with both versions")
code, out, _, _, _ = run_main(install, ["update", "--check"], upstream, latest="v0.5.3")
check(code == 0 and "up to date" in out, "same release: exit 0, up to date")
code, out, _, _, _ = run_main(install, ["update", "--check"], upstream, latest=None)
check(code == 0 and "No stable Nesti release is published" in out, "no release published: exit 0 with a clear message")
code, out, err, _, _ = run_main(install, ["update", "--check"], upstream, latest=nu.UpdateError("cannot read the latest release"))
check(code == 1 and "nesti update: cannot read the latest release" in err, "network error: exit 1 with the reason")
code, out, err, _, _ = run_main(untagged, ["update", "--check"], upstream)
check(code == 1 and "Installed: unknown" in out and "cannot determine the installed version" in err,
      "unknown installed version: exit 1, explained, no traceback")
check(snapshot(install) == before and not runner.calls and not (install / "state" / "update-check.json").exists(),
      "--check changes nothing: no Git, file, cache or Docker change")
with contextlib.redirect_stdout(io.StringIO()) as help_out:
    code = nu.main(["update", "--help"])
check(code == 0 and all(s in help_out.getvalue() for s in ("--check", "exit status", "  3  update available", "NESTI_NO_UPDATE_CHECK"))
      and "apply" not in help_out.getvalue() and "notice" not in help_out.getvalue(),
      "--help documents the exit statuses and hides internal subcommands")
with contextlib.redirect_stderr(io.StringIO()):
    check(nu.main(["update", "--bogus"]) == 2 and nu.main(["nonsense"]) == 2, "invalid arguments: exit 2")

# ---------------------------------------------------------------------------
print("\n[6] Refusals change nothing")
upstream, install, release_commit = make_install("refuse")


def refused(label, expected, prepare, undo, runner=None):
    prepare()
    before = snapshot(install)
    code, out, err, runner, applied = run_main(install, ["update"], upstream, runner=runner)
    check(code == 1 and expected in err and snapshot(install) == before and applied is None
          and not (install / ".git" / "FETCH_HEAD").exists() and "fetch" not in out.lower(),
          "%s: refused (%s), nothing changed" % (label, err.strip().splitlines()[0]))
    undo()
    return runner


readme = install / "README.md"
refused("dirty tracked file", "uncommitted changes", lambda: readme.write_text("edited\n"), lambda: git(install, "checkout", "-q", "--", "README.md"))
refused("staged change", "uncommitted changes", lambda: (readme.write_text("staged\n"), git(install, "add", "README.md")),
        lambda: git(install, "reset", "-q", "--hard"))
refused("detached HEAD", "HEAD is detached", lambda: git(install, "checkout", "-q", "--detach"), lambda: git(install, "switch", "-q", "main"))
docker_down = refused("Docker not running", "'docker info' failed", lambda: None, lambda: None,
                      runner=FakeRunner({("docker", "info"): 1}))
check(docker_down.argvs() == [["docker", "info"]], "the Docker check runs before any Git change")
refused("no Compose", "neither 'docker-compose' nor 'docker compose'", lambda: None, lambda: None,
        runner=FakeRunner({("docker", "compose", "version"): 1}))

(install / "local.txt").write_text("mine\n")
git(install, "add", "local.txt")
git(install, "commit", "-q", "-m", "local")
before = snapshot(install)
code, out, err, runner, applied = run_main(install, ["update"], upstream)
check(code == 1 and "cannot fast-forward" in err and "Nothing was changed" in err and snapshot(install) == before
      and applied is None and "v0.6.0" not in git(install, "tag", "--list"),
      "local commits (diverged): refused, branch and tags unchanged")
git(install, "reset", "-q", "--hard", "HEAD~1")

# ---------------------------------------------------------------------------
print("\n[7] Successful update")
untracked_before = {rel: (install / rel).read_text() for rel in PERSONAL}
code, out, err, runner, applied = run_main(install, ["update"], upstream)
check(code == 0 and git(install, "rev-parse", "HEAD") == release_commit and git(install, "symbolic-ref", "--short", "HEAD") == "main",
      "branch fast-forwards to the release commit: %s" % (err.strip() or "ok"))
check(git(install, "rev-parse", "refs/tags/v0.6.0") == git(upstream, "rev-parse", "refs/tags/v0.6.0")
      and nu.installed_version(str(install)) == "v0.6.0", "release tag stored locally; installed version is now v0.6.0")
check(applied == [str(install / "scripts" / "nesti_update.py"), "apply", "v0.5.3", "v0.6.0"],
      "post-update phase re-executed from the newly merged nesti_update.py")
check({rel: (install / rel).read_text() for rel in PERSONAL} == untracked_before and git(install, "status", "--porcelain") == "?? notes.txt",
      "personal data, .venv and untracked files untouched")
check(runner.argvs() == [["docker", "info"], ["docker", "compose", "version"]], "only the Docker pre-check ran in the old copy")
check("Fast-forwarded main to v0.6.0." in out and "Updating Nesti v0.5.3 -> v0.6.0" in out and len(out.splitlines()) <= 4,
      "progress output is concise")
check(git(install, "remote", "get-url", "origin") == "git@github-main:samettemizer/nesti.git", "origin remote unchanged")

code, out, _, runner, applied = run_main(install, ["update"], upstream)
check(code == 0 and "is up to date" in out and not runner.calls and applied is None, "re-run: already current, exit 0, nothing runs")
commit(install, {"ahead.txt": "dev\n"})
code, out, _, runner, applied = run_main(install, ["update"], upstream)
check(code == 0 and "is up to date" in out and applied is None, "branch ahead of the latest release counts as up to date")

upstream, install, release_commit = make_install("unknown")
git(install, "tag", "-d", "v0.5.3")
code, out, err, _, applied = run_main(install, ["update"], upstream)
check(code == 0 and "installed version is unknown" in out and git(install, "rev-parse", "HEAD") == release_commit
      and applied[1:] == ["apply", "unknown", "v0.6.0"], "unknown installed version: decided by Git ancestry")

upstream, install, release_commit = make_install("contains")
git(install, "tag", "-d", "v0.5.3")
git(install, "fetch", "-q", str(upstream), "main")
git(install, "merge", "-q", "--ff-only", "FETCH_HEAD")
code, out, _, _, applied = run_main(install, ["update"], upstream)
check(code == 0 and "already contains v0.6.0" in out and applied is None, "branch already containing the release commit: nothing to do")

upstream, install, release_commit = make_install("blocked")
(install / "scripts" / "new.txt").write_text("x")
commit(upstream, {"scripts/new.txt": "upstream"}, "v0.7.0")
before = snapshot(install)
code, out, err, _, applied = run_main(install, ["update"], upstream, latest="v0.7.0")
check(code == 1 and "refused the fast-forward" in err and snapshot(install)[:5] == before[:5] and applied is None
      and (install / "scripts" / "new.txt").read_text() == "x", "an untracked file in the way: Git refuses, the file survives")

# ---------------------------------------------------------------------------
print("\n[8] Post-update phase (apply)")
apply_root = BASE / "apply"
apply_root.mkdir()
code, out, err, runner, _ = run_main(apply_root, ["apply", "v0.5.3", "v0.6.0"])
compose = ["docker", "compose"]
check(code == 0 and runner.argvs() == [["docker", "info"], compose + ["version"], compose + ["build"], compose + ["up", "-d"],
                                       ["docker", "exec", "nesti-orchestrator", "nesti", "/provider"]],
      "install.sh order: build, up -d, readiness; no .venv, no pip")
check(runner.calls[2]["env"]["COMPOSE_PARALLEL_LIMIT"] == "1" and runner.calls[3]["env"]["COMPOSE_PARALLEL_LIMIT"] == "1",
      "COMPOSE_PARALLEL_LIMIT=1 like install.sh")
check(out.splitlines()[-1] == "Nesti is now v0.6.0 (was v0.5.3).", "final line names the new version")
(apply_root / ".venv" / "bin").mkdir(parents=True)
code, out, err, runner, _ = run_main(apply_root, ["apply", "v0.5.3", "v0.6.0"], which="/usr/bin/docker-compose")
check(code == 0 and runner.argvs()[1:3] == [["docker-compose", "build"], ["docker-compose", "up", "-d"]]
      and runner.argvs()[-1] == [str(apply_root / ".venv" / "bin" / "python"), "-m", "pip", "install",
                                 "--disable-pip-version-check", "-q", "-r", str(apply_root / "requirements-host.txt")],
      "docker-compose preferred when installed; existing .venv refreshed from requirements-host.txt")
(apply_root / ".venv" / "Scripts").mkdir()
(apply_root / ".venv" / "Scripts" / "python.exe").write_text("")
code, _, _, runner, _ = run_main(apply_root, ["apply", "v0.5.3", "v0.6.0"])
check(runner.argvs()[-1][0] == str(apply_root / ".venv" / "Scripts" / "python.exe"), "Windows .venv layout uses Scripts/python.exe")
code, out, err, runner, _ = run_main(apply_root, ["apply", "v0.5.3", "v0.6.0"], runner=FakeRunner({(str(apply_root / ".venv" / "Scripts" / "python.exe"),): 1}))
check(code == 0 and "Warning: refreshing .venv failed" in err, "pip failure is a warning, like install.sh")
code, out, err, runner, _ = run_main(apply_root, ["apply", "v0.5.3", "v0.6.0"], runner=FakeRunner({tuple(compose + ["build"]): 2}))
check(code == 1 and "output of docker compose build" in err and "docker compose build && docker compose up -d" in err
      and compose + ["up", "-d"] not in runner.argvs(), "build failure stops with its output and the manual retry command")
code, out, err, runner, _ = run_main(apply_root, ["apply", "v0.5.3", "v0.6.0"],
                                     runner=FakeRunner({("docker", "exec", "nesti-orchestrator"): 1}))
readiness = [a for a in runner.argvs() if a[:2] == ["docker", "exec"]]
check(code == 1 and len(readiness) == 60 and compose + ["logs", "--tail", "50", "nesti-orchestrator"] in runner.argvs()
      and "within 120 s" in err, "readiness timeout: 60 attempts, logs shown, exit 1")

# ---------------------------------------------------------------------------
print("\n[9] Notice cache and suppression")
upstream, notice_root, _ = make_install("notice")
now = 1_800_000_000.0
check(nu.read_cache(str(notice_root)) is None and nu.cache_is_stale(None, now), "missing cache is stale")
cache_file = Path(nu.cache_path(str(notice_root)))
check(cache_file == notice_root / "state" / "update-check.json", "cache lives at state/update-check.json")
for bad in ("{", "[]", '{"version": 2, "checked_at": 1, "latest": null}', '{"version": 1, "checked_at": "x", "latest": null}',
            '{"version": 1, "checked_at": 1, "latest": "v1-rc"}'):
    cache_file.write_text(bad)
    check(nu.read_cache(str(notice_root)) is None, "malformed cache ignored: %s" % bad)
nu.write_cache(str(notice_root), "v0.6.0", now - 3600)
cache = nu.read_cache(str(notice_root))
check(cache == {"checked_at": now - 3600, "latest": "v0.6.0"} and not nu.cache_is_stale(cache, now), "1 h old cache is fresh")
check(nu.cache_is_stale({"checked_at": now - 25 * 3600, "latest": None}, now)
      and nu.cache_is_stale({"checked_at": now + 3600, "latest": None}, now), "older than 24 h or in the future: stale")
check(not [f for f in os.listdir(notice_root / "state") if f.endswith(".tmp")], "atomic write leaves no temp file")

check(not nu.should_notify("mcp", {}, True) and not nu.should_notify("update", {}, True), "never for mcp or update")
check(not nu.should_notify("/provider", {"NESTI_NO_UPDATE_CHECK": "1"}, True), "NESTI_NO_UPDATE_CHECK=1 opts out")
check(not nu.should_notify("/provider", {}, False), "never when stderr is not a terminal")
check(nu.should_notify("", {}, True) and nu.should_notify("/plugin", {"NESTI_NO_UPDATE_CHECK": "0"}, True),
      "menu and other commands notify; =0 does not opt out")


def run_notice(root, command="/provider", environ=None, now=now):
    stream = io.StringIO()
    with mock.patch.object(nu, "_spawn_refresh") as spawn:
        nu.notice(str(root), command, {} if environ is None else environ, True, stream, now=now)
    return stream.getvalue(), spawn.called


text, spawned = run_notice(notice_root)
check("v0.6.0" in text and "v0.5.3" in text and "nesti update" in text and "\x1b[32m" in text and not spawned,
      "fresh cache with a newer release: green notice, no refresh")
check("New version available" not in text and "omp" not in text, "wording differs from oh-my-pi's notice")
text, _ = run_notice(notice_root, environ={"NO_COLOR": "1"})
check(text.startswith("+---") and "|  Nesti release v0.6.0 is out." in text and "|  Update with:  nesti update" in text
      and "\x1b" not in text, "NO_COLOR: same box without ANSI codes (ASCII border on a non-UTF-8 stream)")
box = nu.render_notice("v0.5.3", "v0.6.0", False, True).splitlines()
check(box[0].startswith("╭") and box[-1].endswith("╯") and len({len(line) for line in box}) == 1,
      "Unicode bordered box with aligned edges:\n" + "\n".join("      " + line for line in box))
check(run_notice(notice_root, command="mcp") == ("", False) and run_notice(notice_root, command="update") == ("", False)
      and run_notice(notice_root, environ={"NESTI_NO_UPDATE_CHECK": "1"}) == ("", False), "suppressed: no output and no refresh")
text, spawned = run_notice(notice_root, now=now + 2 * 24 * 3600)
check(spawned and "v0.6.0" in text, "stale cache: background refresh started, last known notice still shown")
nu.write_cache(str(notice_root), "v0.5.3", now)
check(run_notice(notice_root) == ("", False), "no newer release: silent")
nu.write_cache(str(untagged), "v0.6.0", now)
check(run_notice(untagged)[0] == "", "unknown installed version: silent")
cache_file.unlink()
text, spawned = run_notice(notice_root)
check(text == "" and spawned, "missing cache: silent, refresh started")

with mock.patch.object(nu, "fetch_latest", return_value="v0.7.0"):
    nu.refresh(str(notice_root))
cache = nu.read_cache(str(notice_root))
check(cache["latest"] == "v0.7.0" and abs(cache["checked_at"] - time.time()) < 60, "refresh stores the latest release")
nu.write_cache(str(notice_root), "v0.7.0", 0)
with mock.patch.object(nu, "fetch_latest", side_effect=nu.UpdateError("offline")):
    nu.refresh(str(notice_root))
cache = nu.read_cache(str(notice_root))
check(cache["latest"] == "v0.7.0" and not nu.cache_is_stale(cache, time.time()), "failed refresh keeps the last answer for a day")
with mock.patch.object(nu, "fetch_latest", side_effect=RuntimeError("boom")), \
        contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
    code = nu.main(["refresh"], root=str(notice_root))
with mock.patch.object(nu, "read_cache", side_effect=RuntimeError("boom")), \
        contextlib.redirect_stdout(io.StringIO()) as out2, contextlib.redirect_stderr(io.StringIO()) as err2:
    code2 = nu.main(["notice", "/provider"], root=str(notice_root))
check(code == code2 == 0 and not (out.getvalue() + err.getvalue() + out2.getvalue() + err2.getvalue()),
      "refresh and notice errors are silent")
with mock.patch.object(nu.subprocess, "Popen") as popen:
    nu._spawn_refresh(str(notice_root))
argv, kwargs = popen.call_args
check(argv[0] == [sys.executable, str(REPO / "scripts" / "nesti_update.py"), "refresh"] and kwargs["start_new_session"]
      and all(kwargs[k] is subprocess.DEVNULL for k in ("stdin", "stdout", "stderr")) and "close_fds" not in kwargs
      and not popen.return_value.wait.called, "refresh runs detached (new session, no stdio, no close_fds for Windows 3.6), never awaited")
with mock.patch.object(nu.os, "name", "nt"), mock.patch.object(nu.subprocess, "Popen") as popen:
    nu._spawn_refresh(str(notice_root))
check(popen.call_args[1]["creationflags"] == 0x208 and "start_new_session" not in popen.call_args[1],
      "Windows Python: DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP")

# ---------------------------------------------------------------------------
print("\n[10] Launcher routing")
launch_root = BASE / "launch-root"
(launch_root / "scripts").mkdir(parents=True)
shutil.copyfile(REPO / "scripts" / "nesti", launch_root / "scripts" / "nesti")
(launch_root / "scripts" / "nesti_update.py").write_text(
    'import sys\nsys.stderr.write("STUB %s\\n" % " ".join(sys.argv[1:]))\nsys.stderr.flush()\n')
fakebin = BASE / "bin"
fakebin.mkdir()
(fakebin / "docker").write_text('#!/bin/sh\necho "docker $*"\necho "marker=${NESTI_UPDATE_NOTICE_SHOWN-}" >&2\n')
(fakebin / "docker").chmod(0o755)
env = {k: v for k, v in os.environ.items()
       if k not in ("VIRTUAL_ENV", "NO_COLOR", "NESTI_NO_UPDATE_CHECK", "NESTI_UPDATE_NOTICE_SHOWN")}
env["PATH"] = "%s:%s" % (fakebin, env["PATH"])
nesti = str(launch_root / "scripts" / "nesti")


def launcher(*args, **extra):
    return subprocess.run(["sh", nesti, *args], env=dict(env, **extra), stdin=subprocess.DEVNULL, capture_output=True, text=True)


def terminal(args, **extra):
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(["sh", nesti, *args], stdin=slave, stdout=slave, stderr=slave, env=dict(env, **extra)) as proc:
            os.close(slave)
            slave = None
            chunks = []
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if not select.select([master], [], [], 0.1)[0]:
                    continue
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
            return proc.wait(timeout=10), b"".join(chunks).decode()
    finally:
        if slave is not None:
            os.close(slave)
        os.close(master)


result = launcher("update", "--check")
check(result.stderr.strip() == "STUB update --check" and "docker" not in result.stdout, "update --check runs on the host, never docker")
result = launcher("/provider")
check("STUB" not in result.stderr and result.stdout.strip() == "docker exec -i nesti-orchestrator nesti /provider",
      "stderr not a terminal: no notice")
code, out = terminal(["/provider"])
check(code == 0 and "STUB notice /provider" in out and out.index("STUB notice") < out.index("docker exec -it"),
      "terminal: notice before the container command")
check("marker=1" in out, "the launcher exports NESTI_UPDATE_NOTICE_SHOWN=1 to nested runs")
code, out = terminal(["update"])
check(out.strip() == "STUB update", "terminal: update itself never shows the notice")
code, out = terminal(["mcp"])
check("STUB" not in out and "nesti-mcp" in out, "terminal: never for mcp")
code, out = terminal(["/provider"], NESTI_NO_UPDATE_CHECK="1")
check("STUB" not in out and "docker exec -it" in out, "terminal: NESTI_NO_UPDATE_CHECK=1 opts out")
code, out = terminal(["/provider"], NESTI_UPDATE_NOTICE_SHOWN="1")
check("STUB" not in out and "docker exec -it" in out, "terminal: nested launcher run (inherited marker) shows no notice")
code, out = terminal([])
check("STUB notice" in out and "docker exec -it nesti-orchestrator nesti" in out, "terminal without arguments: notice, then the menu path")

# Container start: a stopped or removed service brings the stack up with existing images; running ones are left alone.
(fakebin / "docker").write_text(
    '#!/bin/sh\necho "docker $*" >> "$DOCKER_LOG"\n'
    'case "$1" in inspect) printf "%s\\n" $DOCKER_STATES; [ -z "$DOCKER_MISSING" ] ;; esac\n')
(fakebin / "docker-compose").write_text('#!/bin/sh\necho "compose $* in $(pwd)" >> "$DOCKER_LOG"\n')
(fakebin / "docker-compose").chmod(0o755)
docker_log = BASE / "docker.log"
for label, states, missing, starts in (("all running", "true true true true true", "", False),
                                       ("one stopped", "true false true true true", "", True),
                                       ("removed (down)", "", "1", True)):
    docker_log.write_text("")
    result = launcher("/provider", DOCKER_LOG=str(docker_log), DOCKER_STATES=states, DOCKER_MISSING=missing)
    calls = docker_log.read_text()
    started = "compose up -d --no-build --no-recreate in %s" % launch_root.resolve() in calls
    check(started == starts and "build" not in calls.replace("--no-build", "")
          and calls.rstrip().endswith("docker exec -i nesti-orchestrator nesti /provider"),
          "%s: containers %s, never built, then the command" % (label, "started" if starts else "left alone"))
docker_log.write_text("")
result = launcher("mcp", DOCKER_LOG=str(docker_log), DOCKER_STATES="", DOCKER_MISSING="1")
check("compose up -d --no-build --no-recreate" in docker_log.read_text() and result.stdout == "",
      "mcp: containers started with stdout left to the protocol")
docker_log.write_text("")
launcher("update", "--check", DOCKER_LOG=str(docker_log), DOCKER_STATES="", DOCKER_MISSING="1")
check(docker_log.read_text() == "", "update never touches the containers itself")

print("\n%s" % ("All checks passed." if not _failures else "%d check(s) FAILED." % _failures))
_TMP.cleanup()
sys.exit(1 if _failures else 0)
