"""
test_plugins.py – host-side `nesti /plugin` (scripts/nesti_plugins.py) against
temporary local Git repositories: a Ponytail-shaped plain skill repository
whose package.json/hooks must never run, and a small service manifest whose
Compose/prepare/probe calls go to a recording fake runner. Also the real
launcher routing (fake `docker` on PATH) and the container CLI's /plugin
notice. No network, SSH keys or tokens.

Run:  .venv/bin/python test_plugins.py
"""

import ast
import contextlib
import io
import json
import os
import pty
import select
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "scripts"))

import nesti_plugins as np  # noqa: E402
import nesti_menu as nm  # noqa: E402

_failures = 0
_TMP = tempfile.TemporaryDirectory(prefix="nesti-plugins-test-")
BASE = Path(_TMP.name)
_gitconfig = BASE / "gitconfig"
_gitconfig.write_text("")
os.environ.update({
    "GIT_CONFIG_GLOBAL": str(_gitconfig), "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
})
ROOT = BASE / "nesti"
ROOT.mkdir()
PATHS = np.Paths(str(ROOT))
SECRET = "s3cr3t-signing-key-value"


def check(condition, message):
    global _failures
    print(("  ✓ " if condition else "  ✗ ") + message)
    if not condition:
        _failures += 1


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, tag=None, symlinks=None):
    """Write files (and symlinks) into repo, commit, optionally tag; returns the commit SHA."""
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        git(repo, "init", "-q", "-b", "main")
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    for rel, target in (symlinks or {}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, repo / rel)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c")
    if tag:
        git(repo, "tag", tag)
    return git(repo, "rev-parse", "HEAD")


class FakeDocker:
    """Records every argv and answers like docker/compose would."""

    def __init__(self):
        self.calls = []
        self.containers = {}
        self.network = False
        self.image = True
        self.probe_ok = True
        self.fail = set()
        self.fail_up_dirs = set()
        self.interrupt = False
        self.contexts = []

    def __call__(self, argv, cwd=None, env=None, timeout=None, stream=False, merge_output=False):
        argv = list(argv)
        self.calls.append({"argv": argv, "cwd": cwd, "env": dict(env or {})})
        if argv[:2] == ["docker", "ps"] and "ps" in self.fail:
            return 1, "cannot connect to the Docker daemon"
        if argv[:2] == ["docker", "compose"]:
            if "config" in argv:
                compose_dir = os.path.dirname(argv[argv.index("-f") + 1])  # Compose's project dir, like the real one
                return 0, json.dumps({
                    "services": {"receiver": {"image": "hookbox:test", "networks": {"default": None, "nesti-plugins": None},
                                              "volumes": [{"type": "volume", "source": "data", "target": "/data"},
                                                          {"type": "bind", "source": os.path.join(compose_dir, "${STAGE:?unset}") + "/omp",
                                                           "target": "/stage", "read_only": True},
                                                          {"type": "bind", "source": os.path.join(compose_dir, "$LONG2") + "/y",
                                                           "target": "/y"}]}},
                    "volumes": {"data": {}}, "networks": {"nesti-plugins": {"external": True}}})
            if "up" in argv:
                if "up" in self.fail or cwd in self.fail_up_dirs:
                    return 1, "up failed"
                project = argv[argv.index("-p") + 1]
                self.containers[project] = [["%s-receiver-1" % project, "running", "receiver"]]
                return 0, ""
        if argv[:2] == ["docker", "ps"]:
            project = argv[argv.index("--filter") + 1].rsplit("=", 1)[1]
            return 0, "".join("\t".join(c) + "\n" for c in self.containers.get(project, []))
        if argv[:2] == ["docker", "stop"]:
            if "stop" in self.fail:
                return 1, "cannot stop"
            for rows in self.containers.values():
                for row in rows:
                    if row[0] in argv:
                        row[1] = "exited"
            return 0, ""
        if argv[:2] == ["docker", "rm"]:
            for project in list(self.containers):
                self.containers[project] = [r for r in self.containers[project] if r[0] not in argv]
            return 0, ""
        if argv[:3] == ["docker", "network", "inspect"]:
            return (0 if self.network else 1), ""
        if argv[:3] == ["docker", "network", "create"]:
            self.network = True
            return 0, ""
        if argv[:3] == ["docker", "image", "inspect"]:
            return (0 if self.image else 1), ""
        if argv[:2] == ["docker", "run"]:
            if self.interrupt:
                raise KeyboardInterrupt
            return (0 if self.probe_ok else 1), ""
        if argv[0] == "sh":  # prepare.sh / configure.sh: fails when its step name is in self.fail
            if "NESTI_PLUGIN_CONTEXT" in (env or {}):
                self.contexts.append(json.loads(Path(env["NESTI_PLUGIN_CONTEXT"]).read_text()))
            if argv[1] == "configure.sh" and "configure-oserror" in self.fail:
                raise OSError("disk full")
            return (1 if argv[1].split(".")[0] in self.fail else 0), ""
        raise AssertionError("unexpected argv %r" % argv)

    def argvs(self, word):
        return [c for c in self.calls if word in c["argv"]]


FAKE = FakeDocker()


def run(*argv, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(sys, "stdin", io.StringIO(stdin)):
        code = np.main(list(argv), root=str(ROOT), runner=FAKE, compose=["docker", "compose"])
    return code, out.getvalue(), err.getvalue()


def registry():
    return json.loads(Path(PATHS.registry).read_text())


def runtime():
    return json.loads(Path(PATHS.runtime).read_text())


def bindings_path(name):
    return Path(PATHS.config(name)) / "bindings.json"


# ---------------------------------------------------------------------------
print("\n[1] Module boundary: Python 3.6 syntax, standard library only")
source = (REPO / "scripts" / "nesti_plugins.py").read_text()
tree = ast.parse(source, feature_version=(3, 6))
imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
check(imports <= set(sys.stdlib_module_names), "imports only the standard library: %s" % sorted(imports - set(sys.stdlib_module_names)))
check("__future__" not in imports and "dataclasses" not in imports, "no __future__/dataclasses")
meta = np.parse_frontmatter("---\nname: 'ponytail'\ndescription: >\n  Lazy senior\n  dev mode.\nlicense: MIT\n---\nbody\n")
check(meta == {"name": "ponytail", "description": "Lazy senior dev mode.", "license": "MIT"}, "frontmatter: limited key/value metadata")
if os.name != "nt":
    transports = ("git@host:o/r", "host:repo", "C:/x", "https://h/o/r", "ssh://git@host/o/r", "file:///tmp/o/r")
    check([np.absolute_local(u) for u in transports] == list(transports),
          "POSIX: scp-like, SSH alias, C:/x, HTTPS, SSH and file URLs stay as typed")
    check(np.absolute_local("dir/a:b") == os.path.join(os.getcwd(), "dir", "a:b"), "POSIX: a local path with a later colon becomes absolute")
envfile = BASE / "sample.env"
envfile.write_text('A=abc123 # rotated\nB="abc #123" # note\nC=\'x # y\'\nD=a#b\nexport E=plain\n# F=no\n')
check(np._read_env(str(envfile)) == {"A": "abc123", "B": "abc #123", "C": "x # y", "D": "a#b", "E": "plain"},
      ".env: unquoted ' #' comments stripped, quoted '#' kept (Compose rules)")

# ---------------------------------------------------------------------------
print("\n[2] Plain skill repository (Ponytail-shaped)")
PONY = BASE / "ponytail"
pony_files = {
    "plugin.json": '{"name": "ponytail"}',
    "package.json": json.dumps({"name": "ponytail-npm", "scripts": {"postinstall": "node hooks/pwn.js"}}),
    "hooks/pwn.js": "require('fs').writeFileSync('PWNED', 'x')\n",
    "skills/plugin.json": "{}",
    "skills/ponytail/SKILL.md": "---\nname: ponytail\ndescription: >\n  Lazy.\nlicense: MIT\n---\n\n# Ponytail\nBe lazy.\n",
    "skills/ponytail-review/SKILL.md": "---\nname: ponytail-review\n---\nReview.\n",
}
sha1 = commit(PONY, pony_files, tag="v1")
sha2 = commit(PONY, {"skills/ponytail/SKILL.md": "---\nname: ponytail\n---\nBe lazier.\n"}, tag="v2")
code, out, err = run("install", str(PONY), "--ref", "v1")
rec = registry()["packages"].get("ponytail", {})
src = Path(PATHS.package("ponytail", sha1))
check(code == 0, "install by tag succeeds: %s" % err.strip())
check(rec.get("ref") == "v1" and rec.get("sha") == sha1 and len(sha1) == 40, "requested ref and full SHA recorded")
check((src / "skills" / "ponytail" / "SKILL.md").is_file() and not (src / ".git").exists(), "sources at packages/<name>/<sha> without .git")
check(not any("PWNED" in files for _, _, files in os.walk(BASE)) and FAKE.calls == [], "package.json/hooks never ran; no docker/npm call")
check(json.loads(bindings_path("ponytail").read_text()) == {"skills": {
    "ponytail": {"phases": ["plan", "code"], "arguments": {}}, "ponytail-review": {"phases": [], "arguments": {}}}},
    "bindings.json template: main skill bound to plan+code, others listed only")
check(str(bindings_path("ponytail")) in out and "ponytail (main, plan, code)" in out, "install prints the configuration path and skills")
check(rec.get("enabled") is False and runtime() == {"version": 1, "skills": [], "subscriptions": []}, "installed, not enabled")

installed_at = rec["installed_at"]
code, out, _ = run("install", str(PONY) + "/", "--ref", "v1")
check(code == 0 and "already installed" in out and registry()["packages"]["ponytail"]["installed_at"] == installed_at,
      "same repository + SHA again is a no-op")
code, _, err = run("install", str(PONY), "--ref", "v2")
check(code == 1 and "update" in err, "same source at another SHA is refused (use update)")
IMPOSTOR = BASE / "impostor"
commit(IMPOSTOR, {"plugin.json": '{"name": "ponytail"}', "skills/ponytail/SKILL.md": "evil\n"}, tag="v1")
code, _, err = run("install", str(IMPOSTOR), "--ref", "v1")
check(code == 1 and "another source cannot reuse" in err, "another source cannot reuse the name")

for url in ("https://user:tok@github.com/a/b.git", "https://ghp_abc@github.com/a/b", "https://github.com/a/b?access_token=x",
            "ext::sh -c touch% /tmp/pwned", "-uhttps://github.com/a/b", "http://github.com/a/b", "user:pw@host:a/b",
            "sftp://host/a/b", "ssh://user:pw@host/a/b", "https://github.com/a/b#token", "owner/repo\n"):
    code, _, err = run("install", "--", url)
    check(code == 1, "URL refused: %s" % url)
check(not os.listdir(PATHS.tmp), "refused/failed installs leave no scratch directories")
for ref in ("", "--upload-pack=evil", "v1..v2", "HEAD~1"):
    code, _, err = run("install", str(PONY), "--ref=" + ref)
    check(code == 1 and "invalid --ref" in err, "invalid explicit ref %r is rejected" % ref)
    code, _, err = run("update", "ponytail", "--ref=" + ref)
    check(code == 1 and "invalid --ref" in err, "update rejects invalid explicit ref %r" % ref)
OTHER = BASE / "Misc Skills"
misc_sha = commit(OTHER, {"skills/alpha/SKILL.md": "Alpha.\n", "skills/beta/SKILL.md": "Beta.\n"})
code, _, err = run("install", str(OTHER), "--ref", "main")
check(code == 1 and "not a tag or commit" in err, "a branch name is not a tag or commit")
code, out, err = run("install", str(OTHER), "--ref", misc_sha[:10])
check(code == 0 and registry()["packages"]["misc-skills"]["sha"] == misc_sha, "abbreviated commit resolves to the full SHA; name normalized from the repo")
check("No skill is bound by default" in out, "no main skill: install asks for a bindings.json choice")
REL = BASE / "relpkg"
rel1 = commit(REL, {"skills/relpkg/SKILL.md": "Rel.\n"}, tag="v1")
rel2 = commit(REL, {"skills/relpkg/SKILL.md": "Rel 2.\n"}, tag="v2")
cwd = os.getcwd()
os.chdir(BASE)
code, _, err = run("install", "./relpkg", "--ref", "v1")
os.chdir(cwd)
check(code == 0 and registry()["packages"]["relpkg"]["source"] == str(REL), "relative local path recorded as absolute: %s" % err.strip())
code, out, _ = run("install", str(REL), "--ref", "v1")
check(code == 0 and "already installed" in out, "the same repository by absolute path is the same source")
code, _, err = run("update", "relpkg", "--ref", "v2")
check(code == 0 and registry()["packages"]["relpkg"]["sha"] == rel2, "update from another cwd succeeds: %s" % err.strip())
run("remove", "relpkg")

print("\n[2b] Default branch snapshots and GitHub shorthand through the CLI")
SNAP = BASE / "local-owner" / "local-repo"
old_snapshot = commit(SNAP, {"plugin.json": '{"name": "snapshot"}',
                             "skills/snapshot/SKILL.md": "---\nname: snapshot\n---\nOld.\n"}, tag="old")
git(SNAP, "checkout", "-q", "-b", "stable")
snapshot = commit(SNAP, {"skills/snapshot/SKILL.md": "---\nname: snapshot\n---\nLatest.\n"})
https_url = "https://github.com/DietrichGebert/ponytail.git"
git(BASE, "config", "--global", "url.%s.insteadOf" % SNAP.as_uri(), https_url)
cwd = os.getcwd()
try:
    os.chdir(BASE)
    for url in (https_url, "DietrichGebert/ponytail"):
        code, _, err = run("install", url)
        rec = registry()["packages"].get("snapshot", {})
        check(code == 0 and rec.get("ref") == rec.get("sha") == snapshot,
              "install %s without --ref pins the non-main default branch HEAD: %s" % (url, err.strip()))
        check(rec.get("url") == https_url and rec.get("source") == https_url[:-4],
              "HTTPS and shorthand record the same canonical URL and source")
        src = Path(PATHS.package("snapshot", snapshot))
        check((src / "skills/snapshot/SKILL.md").read_text().endswith("Latest.\n") and not (src / ".git").exists(),
              "snapshot contains the default branch revision, without live Git metadata")
        before = registry()
        code, out, err = run("install", "DietrichGebert/ponytail.git")
        check(code == 0 and "already installed" in out and registry() == before,
              "equivalent shorthand with .git is idempotent")
        code, _, err = run("enable", "snapshot")
        check(code == 0 and all(s["ref"] == s["revision"] == snapshot
                               for s in runtime()["skills"] if s["package"] == "snapshot"),
              "enabled default snapshot publishes a concrete ref and revision")
        run("remove", "snapshot")

    for url in ("local-owner/local-repo", "./local-owner/local-repo", str(SNAP), SNAP.as_uri()):
        code, _, err = run("install", url)
        rec = registry()["packages"].get("snapshot", {})
        check(code == 0 and rec.get("url") == (url if url.startswith("file:") else str(SNAP))
              and rec.get("sha") == snapshot, "existing bare and explicit local paths remain local: %s" % url)
        run("remove", "snapshot")
    os.chdir(SNAP.parent)
    code, _, err = run("install", "../local-owner/local-repo")
    check(code == 0 and registry()["packages"]["snapshot"]["source"] == str(SNAP),
          "../ paths remain local")
    check(np.absolute_local("./missing/repo") == str(SNAP.parent / "missing/repo")
          and np.absolute_local("missing/repo") == "https://github.com/missing/repo.git",
          "./ explicitly selects a local path even before it exists")
    before = registry()
    newer_snapshot = commit(SNAP, {"skills/snapshot/SKILL.md": "---\nname: snapshot\n---\nNewer.\n"})
    code, _, err = run("install", str(SNAP))
    check(code == 1 and "update snapshot --ref %s" % newer_snapshot in err and registry() == before,
          "later upstream HEAD does not auto-update; refusal gives a concrete update command")
    code, _, err = run("update", "snapshot", "--ref", "old")
    check(code == 0 and registry()["packages"]["snapshot"]["ref"] == "old"
          and registry()["packages"]["snapshot"]["sha"] == old_snapshot,
          "default snapshot can still switch to an explicit tag")
    code, _, err = run("update", "snapshot", "--ref", snapshot[:10])
    check(code == 0 and registry()["packages"]["snapshot"]["ref"] == snapshot[:10]
          and registry()["packages"]["snapshot"]["sha"] == snapshot,
          "update accepts an abbreviated explicit commit")
    run("enable", "snapshot")
    code, _, err = run("update", "snapshot")
    rec = registry()["packages"]["snapshot"]
    check(code == 0 and rec["sha"] == rec["ref"] == newer_snapshot and rec["enabled"]
          and [s["revision"] for s in runtime()["skills"] if s["package"] == "snapshot"] == [newer_snapshot],
          "reference-free update switches an enabled package to default HEAD and pins its full SHA")
    before, saved_runtime = registry(), runtime()
    code, out, err = run("update", "snapshot")
    check(code == 0 and "nothing to update" in out and registry() == before and runtime() == saved_runtime
          and not os.listdir(PATHS.tmp), "same-HEAD update is a no-op and removes its scratch checkout")
    run("remove", "snapshot")
finally:
    os.chdir(cwd)
    git(BASE, "config", "--global", "--unset", "url.%s.insteadOf" % SNAP.as_uri())
EMPTY = BASE / "empty-repo"
EMPTY.mkdir()
git(EMPTY, "init", "-q", "-b", "empty")
code, _, err = run("install", str(EMPTY))
check(code == 1 and not os.listdir(PATHS.tmp), "an unborn default HEAD fails cleanly and removes scratch checkout")
for command in ("install", "update"):
    code, out, err = run(command, "--help")
    check(code == 0 and "[--ref REF]" in out,
          "%s --help exposes the optional ref" % command)

# ---------------------------------------------------------------------------
print("\n[3] Path and identity safety")
for label, files, links in (
    ("escaping symlink", {"skills/evil/README": "x"}, {"skills/evil/SKILL.md": "../../../../../etc/passwd"}),
    ("absolute symlink", {"skills/evil/README": "x"}, {"skills/evil/SKILL.md": "/etc/passwd"}),
    ("duplicate skill names", {"skills/a/SKILL.md": "---\nname: same\n---\n", "skills/b/SKILL.md": "---\nname: same\n---\n"}, None),
    ("invalid skill name", {"skills/Bad Name/SKILL.md": "x\n"}, None),
    ("compose ../", {"nesti-plugin.json": json.dumps({"schema_version": 1, "name": "bad", "nesti_plugin_api": 1, "compose": "../x.yml"})}, None),
    ("compose absolute", {"nesti-plugin.json": json.dumps({"schema_version": 1, "name": "bad", "nesti_plugin_api": 1, "compose": "/etc/x.yml"})}, None),
    ("unknown manifest key", {"nesti-plugin.json": json.dumps({"schema_version": 1, "name": "bad", "nesti_plugin_api": 1, "hooks": "x", "skills": []})}, None),
):
    repo = BASE / ("bad-" + label.replace(" ", "-").replace("/", ""))
    commit(repo, files, tag="v1", symlinks=links)
    code, _, err = run("install", str(repo), "--ref", "v1")
    check(code == 1, "%s rejected: %s" % (label, err.strip()[-90:]))
check(not os.listdir(PATHS.tmp) and sorted(os.listdir(Path(PATHS.package("x")).parent)) == ["misc-skills", "ponytail"],
      "rejected packages leave nothing behind")

# ---------------------------------------------------------------------------
print("\n[4] Enable, bindings, size limit, disable")
code, _, err = run("enable", "misc-skills")
check(code == 1 and "bindings.json" in err, "ambiguous main: enable needs a bindings.json choice")
bindings_path("misc-skills").write_text(json.dumps({"skills": {"alpha": {"phases": ["code"], "arguments": {"level": "ultra"}}}}))
code, _, err = run("enable", "misc-skills")
check(code == 0, "enable after choosing a skill: %s" % err.strip())
check(runtime()["skills"] == [{"package": "misc-skills", "revision": misc_sha, "ref": misc_sha[:10], "skill": "alpha",
                               "path": "/orchestrator/plugins/packages/misc-skills/%s/skills/alpha/SKILL.md" % misc_sha,
                               "phases": ["code"], "arguments": {"level": "ultra"}}], "runtime binding contract")
code, _, err = run("enable", "ponytail")
pony_binding = [s for s in runtime()["skills"] if s["package"] == "ponytail"]
check(code == 0 and pony_binding == [{"package": "ponytail", "revision": sha1, "ref": "v1", "skill": "ponytail",
      "path": "/orchestrator/plugins/packages/ponytail/%s/skills/ponytail/SKILL.md" % sha1,
      "phases": ["plan", "code"], "arguments": {}}], "ponytail main skill published for plan+code only")
before = runtime()
bindings_path("ponytail").write_text(json.dumps({"skills": {"nope": {"phases": ["plan"]}}}))
code, _, err = run("enable", "ponytail")
check(code == 1 and "unknown skill" in err and runtime() == before, "unknown skill in bindings.json fails; runtime unchanged")
bindings_path("ponytail").write_text(json.dumps({"skills": {"ponytail": {"arguments": {"level": "x" * 65}}}}))
code, _, err = run("enable", "ponytail")
check(code == 1 and runtime() == before, "oversized argument fails; runtime unchanged")
bindings_path("ponytail").unlink()
BIG = BASE / "bigskill"
commit(BIG, {"skills/bigskill/SKILL.md": "x" * (np.PHASE_BINDING_CHAR_LIMIT - 10) + "\n"}, tag="v1")
run("install", str(BIG), "--ref", "v1")
code, _, err = run("enable", "bigskill")
check(code == 1 and "limit" in err and "truncated" in err and runtime() == before, "phase total above the limit fails; nothing truncated or published")
code, _, _ = run("disable", "ponytail")
check(code == 0 and not [s for s in runtime()["skills"] if s["package"] == "ponytail"]
      and registry()["packages"]["ponytail"]["enabled"] is False, "disable removes bindings")
code, out, _ = run("list")
check(code == 0 and "ponytail  skills  disabled" in out and sha1 in out and "(ref v1)" in out, "list shows source, ref, SHA, activation")

# ---------------------------------------------------------------------------
print("\n[5] Update and remove a skill package")
run("enable", "ponytail")
code, _, err = run("update", "ponytail", "--ref", "v2")
check(code == 0 and registry()["packages"]["ponytail"]["sha"] == sha2, "update switches to the new SHA: %s" % err.strip())
check([s["revision"] for s in runtime()["skills"] if s["package"] == "ponytail"] == [sha2]
      and not Path(PATHS.package("ponytail", sha1)).exists(), "runtime follows; the old checkout is gone")
commit(PONY, {}, tag="v3", symlinks={"skills/ponytail/escape.md": "/etc/hostname"})
before = runtime()
code, _, err = run("update", "ponytail", "--ref", "v3")
check(code == 1 and "escapes" in err and registry()["packages"]["ponytail"]["sha"] == sha2 and runtime() == before,
      "failed update preparation leaves the running revision")
check(sorted(os.listdir(PATHS.package("ponytail"))) == [sha2], "failed update leaves no new checkout")
code, out, _ = run("remove", "ponytail")
check(code == 0 and "ponytail" not in registry()["packages"] and not Path(PATHS.package("ponytail")).exists(),
      "remove deletes record and sources")
check(Path(PATHS.config("ponytail")).is_dir() and not [s for s in runtime()["skills"] if s["package"] == "ponytail"],
      "remove keeps the config dir; bindings gone")
check(FAKE.calls == [], "skill packages never touch docker")

# ---------------------------------------------------------------------------
print("\n[6] Service package: trust, prepare, enable")
np.READY_TIMEOUT = 0
HOOK = BASE / "hookbox"
manifest = {"schema_version": 1, "name": "hookbox", "nesti_plugin_api": 1, "compose": "compose.yml",
            "prepare": ["sh", "prepare.sh"], "config": {"env_example": ".env.example", "required": ["API_TOKEN"]},
            "events": [{"name": "github.pull_request.ready", "service": "receiver", "port": 8080, "path": "/hook",
                        "readiness_path": "/ready", "secret_key": "HOOK_SECRET"}]}
hook1 = commit(HOOK, {"nesti-plugin.json": json.dumps(manifest), "compose.yml": "services: {}\n",
                      "prepare.sh": "touch \"$NESTI_PLUGIN_WORK_DIR/built\"\n", ".env.example": "API_TOKEN=\nHOOK_SECRET=\n"}, tag="v1")
hook2 = commit(HOOK, {"prepare.sh": "echo v2\n"}, tag="v2")
code, out, err = run("install", str(HOOK), "--ref", "v1")
check(code == 1 and "--trust" in err and not FAKE.argvs("sh") and not Path(PATHS.package("hookbox")).exists(),
      "noninteractive install without --trust is refused before any prepare")
check("repository: %s" % HOOK in out and hook1 in out and "prepare:    sh prepare.sh" in out
      and "service receiver: hookbox:test" in out and "mount: volume data -> /data" in out and "network nesti-plugins (external)" in out
      and "mount: bind ${STAGE:?unset}/omp -> /stage (read-only)" in out and "mount: bind $LONG2/y -> /y" in out,
      "trust summary shows repository, SHA, prepare, services, volumes/mounts (variable sources as written), networks")
code, out, err = run("install", str(HOOK))
check(code == 1 and "--trust" in err and hook2 in out and not FAKE.argvs("sh")
      and not Path(PATHS.package("hookbox")).exists() and "hookbox" not in registry()["packages"],
      "omitted ref still requires trust for the resolved service SHA before prepare")
sub = os.path.join(os.sep + "pkg", "deploy")
lines = np._describe_compose({"services": {"s": {"image": "i", "volumes": [
    {"type": "bind", "source": os.path.join(sub, "${X}") + "/a", "target": "/a"},
    {"type": "bind", "source": os.path.join(sub + "x", "${Z}"), "target": "/z"},
    {"type": "bind", "source": os.path.join(sub, "data"), "target": "/d"}]}}}, sub)
check("    mount: bind ${X}/a -> /a" in lines and "    mount: bind %s -> /z" % os.path.join(sub + "x", "${Z}") in lines
      and "    mount: bind %s -> /d" % os.path.join(sub, "data") in lines,
      "a compose file in a package subdir: only its own dir is stripped, at a separator boundary, only before $")
code, out, err = run("install", str(HOOK), "--ref", "v1", "--trust")
prep = FAKE.argvs("sh")
check(code == 0 and len(prep) == 1 and prep[0]["argv"] == ["sh", "prepare.sh"] and prep[0]["cwd"] == PATHS.package("hookbox", hook1),
      "prepare runs once with its fixed argv in the source dir: %s" % err.strip())
check(prep[0]["env"]["NESTI_PLUGIN_WORK_DIR"] == PATHS.work("hookbox", hook1) and Path(PATHS.work("hookbox", hook1)).is_dir(),
      "prepare gets its own work dir")
check(not FAKE.argvs("up") and registry()["packages"]["hookbox"]["trusted_sha"] == hook1, "install prepares only; trust recorded")
check(os.path.join(PATHS.config("hookbox"), ".env") in out and "API_TOKEN, HOOK_SECRET" in out, "install prints settings path and required keys")

code, _, err = run("enable", "hookbox")
check(code == 1 and "API_TOKEN, HOOK_SECRET" in err and not FAKE.argvs("up"), "missing settings: no Compose start")
Path(PATHS.config("hookbox"), ".env").write_text("API_TOKEN=tok-123\nHOOK_SECRET=%s\n" % SECRET)
FAKE.image = False
code, _, err = run("enable", "hookbox")
check(code == 1 and "build Nesti first" in err and not FAKE.argvs("up"), "missing probe image: clear message, no start")
FAKE.image, FAKE.probe_ok = True, False
code, _, err = run("enable", "hookbox")
check(code == 1 and "not ready" in err and FAKE.argvs("stop") and registry()["packages"]["hookbox"]["enabled"] is False
      and runtime()["subscriptions"] == [], "readiness failure: stopped, not enabled, no subscriptions")
FAKE.probe_ok = True
code, out, err = run("enable", "hookbox")
up = FAKE.argvs("up")[-1]["argv"]
key = Path(PATHS.secrets("hookbox"), "github.pull_request.ready.key")
check(code == 0 and ["docker", "network", "create", "--internal", "nesti-plugins"] in [c["argv"] for c in FAKE.calls],
      "enable creates the internal event network: %s" % err.strip())
check("--no-build" in up and up[up.index("--env-file") + 1] == os.path.join(PATHS.config("hookbox"), ".env"),
      "compose up uses the package .env and never builds")
check(runtime()["subscriptions"] == [{"package": "hookbox", "revision": hook1, "event": "github.pull_request.ready",
                                      "url": "http://nesti-plugin-hookbox-receiver-1:8080/hook",
                                      "secret_file": "/orchestrator/plugins/secrets/hookbox/github.pull_request.ready.key"}],
      "subscription published after readiness")
check(key.read_text() == SECRET and stat.S_IMODE(key.stat().st_mode) == 0o600, "signing key file holds only the key, mode 600")
check(SECRET not in Path(PATHS.registry).read_text() + Path(PATHS.runtime).read_text() + out + err, "secret never in registry, runtime or output")
code, out, _ = run("list")
check("service:  running 1/1" in out, "list shows the running service")
FAKE.containers["nesti-plugin-hookbox"][0][1] = "exited"
code, out, _ = run("list")
check("service:  stopped" in out and "running" not in out.split("hookbox", 1)[1], "a stopped service is never labelled running")
FAKE.containers["nesti-plugin-hookbox"][0][1] = "running"

# ---------------------------------------------------------------------------
print("\n[7] Service update: trust, failed prepare, restore")
before = runtime()
code, _, err = run("update", "hookbox")
check(code == 1 and "--trust" in err and registry()["packages"]["hookbox"]["sha"] == hook1 and runtime() == before
      and not Path(PATHS.package("hookbox", hook2)).exists(), "reference-free service update still needs renewed trust")
FAKE.fail.add("prepare")
code, _, err = run("update", "hookbox", "--ref", "v2", "--trust")
FAKE.fail.discard("prepare")
check(code == 1 and "prepare step failed" in err and registry()["packages"]["hookbox"]["sha"] == hook1 and runtime() == before
      and not Path(PATHS.package("hookbox", hook2)).exists() and not Path(PATHS.work("hookbox", hook2)).exists(),
      "failed prepare: running revision and subscriptions intact, new checkout/work dir removed")
FAKE.fail_up_dirs = {PATHS.package("hookbox", hook2)}
code, _, err = run("update", "hookbox", "--ref", "v2", "--trust")
rec = registry()["packages"]["hookbox"]
check(code == 1 and "restored %s" % hook1 in err and rec["sha"] == hook1 and rec["enabled"] and runtime() == before,
      "activation failure restores the previous revision and its subscription")
check(FAKE.argvs("up")[-1]["cwd"] == PATHS.package("hookbox", hook1), "restore started the old revision")
FAKE.fail_up_dirs, FAKE.interrupt = set(), True
code, _, _ = run("update", "hookbox", "--ref", "v2", "--trust")
FAKE.interrupt = False
rec = registry()["packages"]["hookbox"]
check(code == 130 and not Path(PATHS.package("hookbox", hook2)).exists() and not Path(PATHS.work("hookbox", hook2)).exists(),
      "interrupted activation removes the new revision's dirs")
check(rec["sha"] == hook1 and rec["enabled"] is False and "interrupted" in rec["error"] and runtime()["subscriptions"] == [],
      "interrupted update: old revision recorded, subscriptions off")
code, _, err = run("enable", "hookbox")
check(code == 0 and runtime()["subscriptions"][0]["revision"] == hook1, "re-enable after the interruption: %s" % err.strip())
FAKE.fail.add("up")
code, _, err = run("update", "hookbox", "--ref", "v2", "--trust")
rec = registry()["packages"]["hookbox"]
check(code == 1 and "restoring %s failed" % hook1 in err and rec["enabled"] is False and rec["sha"] == hook1
      and runtime()["subscriptions"] == [] and not key.exists(), "restore failure: subscriptions stay off, real error recorded")
FAKE.fail.discard("up")
FAKE.fail_up_dirs = set()
code, out, _ = run("list")
check("error:    update to %s failed" % hook2 in out, "list reports the recorded failure")
code, _, err = run("update", "hookbox", "--ref", "v2", "--trust")
check(code == 0 and registry()["packages"]["hookbox"]["sha"] == hook2, "update of a disabled service switches the revision: %s" % err.strip())
code, _, err = run("enable", "hookbox")
check(code == 0 and runtime()["subscriptions"][0]["revision"] == hook2 and not Path(PATHS.package("hookbox", hook1)).exists()
      and not Path(PATHS.work("hookbox", hook1)).exists(), "re-enabled at the new revision; old checkout and work dir gone")

# ---------------------------------------------------------------------------
print("\n[8] Disable with a failed stop, remove")
FAKE.fail.add("stop")
code, _, err = run("disable", "hookbox")
rec = registry()["packages"]["hookbox"]
check(code == 1 and "disabled; service still running" in err and rec["enabled"] is False and runtime()["subscriptions"] == []
      and not key.exists(), "failed stop: disabled with a running-service error, subscriptions off")
FAKE.fail.discard("stop")
code, _, err = run("remove", "hookbox")
argvs = [c["argv"] for c in FAKE.calls]
check(code == 0 and "hookbox" not in registry()["packages"] and not Path(PATHS.package("hookbox")).exists()
      and not Path(PATHS.work("hookbox")).exists(), "remove deletes record, sources and work dir: %s" % err.strip())
check(any(a[:2] == ["docker", "rm"] for a in argvs) and FAKE.containers["nesti-plugin-hookbox"] == [], "remove deletes the service containers")
check(not any(w in a for a in argvs for w in ("down", "-v", "prune", "volume")), "no down/-v/prune/volume command ever ran")
check(Path(PATHS.config("hookbox"), ".env").read_text().startswith("API_TOKEN="), "settings survive remove")

# ---------------------------------------------------------------------------
print("\n[9] Registry lock and atomic files")
child = subprocess.Popen([sys.executable, "-c",
                          "import sys, time; sys.path.insert(0, %r); import nesti_plugins as n\n"
                          "with n._locked(n.Paths(%r)):\n    print('locked', flush=True); time.sleep(1.5)"
                          % (str(REPO / "scripts"), str(ROOT))], stdout=subprocess.PIPE, text=True)
child.stdout.readline()
started = time.time()
with contextlib.redirect_stderr(io.StringIO()) as waited, np._locked(PATHS):
    elapsed = time.time() - started
child.wait()
check(elapsed >= 1.0 and "Waiting for another" in waited.getvalue(), "a second writer waits for the lock (%.1f s)" % elapsed)
check(not [f for f in os.listdir(PATHS.state) + os.listdir(os.path.dirname(PATHS.runtime)) if ".tmp-" in f], "no partial temp files left")

# ---------------------------------------------------------------------------
print("\n[10] Launcher routing, container CLI, ignore rules")
fakebin = BASE / "bin"
fakebin.mkdir()
(fakebin / "docker").write_text('#!/bin/sh\necho "docker $*"\nexit ${FAKE_DOCKER_EXIT:-0}\n')
(fakebin / "docker").chmod(0o755)
env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
env["PATH"] = "%s:%s" % (fakebin, env["PATH"])


def launcher(*args, **extra):
    return subprocess.run(["sh", str(REPO / "scripts" / "nesti"), *args], env=dict(env, **extra),
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)


result = launcher()
check(result.returncode == 0 and result.stdout.strip() == "docker exec -i nesti-orchestrator nesti",
      "no arguments without a TTY keeps the container help path")


def terminal(argv, environment):
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, env=environment) as proc:
            os.close(slave)
            slave = None
            chunks = []
            deadline = time.monotonic() + 10
            while True:
                if time.monotonic() >= deadline:
                    proc.kill()
                    raise AssertionError("PTY command timed out")
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


menu_root = BASE / "menu-root"
(menu_root / "scripts").mkdir(parents=True)
(menu_root / ".venv" / "bin").mkdir(parents=True)
shutil.copyfile(REPO / "scripts" / "nesti", menu_root / "scripts" / "nesti")
stub = menu_root / ".venv" / "bin" / "python"
stub.write_text('#!/bin/sh\ncase "$*" in "-c import questionary") exit ${FAKE_Q:-0};; esac\necho "menu $*"\n')
stub.chmod(0o755)
code, out = terminal(["sh", str(menu_root / "scripts" / "nesti")], dict(env, FAKE_Q="0"))
check(code == 0 and "menu %s/scripts/nesti_menu.py" % menu_root in out and "docker" not in out,
      "TTY without arguments opens the checkout-venv menu")
code, out = terminal(["sh", str(menu_root / "scripts" / "nesti")], dict(env, FAKE_Q="1"))
check(code == 0 and "docker exec -it nesti-orchestrator nesti" in out and "needs Questionary" in out,
      "missing Questionary falls back to the command list with guidance")
result = launcher("/plugin", "list")
check(result.returncode == 0 and "docker" not in result.stdout + result.stderr, "/plugin runs the host module, never docker exec")
result = launcher("/plugin")
check(result.returncode == 2 and "nesti /plugin" in result.stderr, "/plugin without a command: usage, exit 2")
result = launcher("/provider")
check(result.returncode == 0 and result.stdout.strip() == "docker exec -i nesti-orchestrator nesti /provider", "/provider still goes to the container")
result = launcher("/usage", FAKE_DOCKER_EXIT="3")
check(result.returncode == 3, "container exit codes pass through")
result = launcher("mcp")
check(result.stdout.strip() == "docker exec -i -e NESTI_CLIENT_REMOTE nesti-mcp python -m mcp_server.server", "mcp routing unchanged")
result = subprocess.run([sys.executable, "-m", "scripts.oauth", "/plugin", "list"], cwd=REPO, capture_output=True, text=True,
                        env=dict(os.environ, REDIS_URL="redis://127.0.0.1:1/0"))
check(result.returncode == 1 and "runs on the host" in result.stdout and "Redis —" not in result.stdout,
      "container CLI explains /plugin is host-only, without a Redis error")
ignore_paths = [".private/plugins/config/x/.env", "state/plugins/registry.json", "state/plugins/runtime/active.json"]
ignored = subprocess.run(["git", "check-ignore", "--", *ignore_paths], cwd=REPO, capture_output=True, text=True)
ignored = 0 if ignored.stdout.split() == ignore_paths else 1
dockerignore = (REPO / ".dockerignore").read_text().split()
check(ignored == 0 and ".private" in dockerignore and "state/" in dockerignore, ".private and state/plugins stay out of Git and images")
compose = (REPO / "docker-compose.yml").read_text()
check(compose.count("create_host_path: false") == 2 and ":/orchestrator/plugins/" not in compose,
      "the plugin mounts never let Docker create (root-owned) host dirs")

# ---------------------------------------------------------------------------
print("\n[11] Service configure step: settings, runtime context, controlled restart")
for label, extra in (("configure as a string", {"compose": "compose.yml", "configure": "sh configure.sh"}),
                     ("configure without compose", {"skills": [], "configure": ["sh", "configure.sh"]}),
                     ("configure entry point outside", {"compose": "compose.yml", "configure": ["../configure.sh"]})):
    repo = BASE / ("bad-" + label.replace(" ", "-"))
    commit(repo, {"nesti-plugin.json": json.dumps(dict({"schema_version": 1, "name": "bad", "nesti_plugin_api": 1}, **extra)),
                  "compose.yml": "services: {}\n"}, tag="v1")
    code, _, err = run("install", str(repo), "--ref", "v1", "--trust")
    check(code == 1 and not Path(PATHS.package("bad")).exists(), "%s rejected: %s" % (label, err.strip()[-90:]))
CONF = BASE / "confbox"
conf_manifest = dict(manifest, name="confbox", configure=["sh", "configure.sh"])
conf1 = commit(CONF, {"nesti-plugin.json": json.dumps(conf_manifest), "compose.yml": "services: {}\n",
                      "prepare.sh": "true\n", "configure.sh": "true\n", ".env.example": "API_TOKEN=\nHOOK_SECRET=\n"}, tag="v1")
code, out, err = run("install", str(CONF), "--ref", "v1", "--trust")
check(code == 0 and "configure:  sh configure.sh (runs at every enable" in out and not FAKE.argvs("configure.sh"),
      "trust summary shows the configure step; install never runs it: %s" % err.strip())
FAKE.fail.add("ps")
code, _, err = run("enable", "confbox")
FAKE.fail.discard("ps")
check(code == 1 and "missing settings" in err and "service state unknown: docker ps failed" in err
      and "still running" not in err, "docker ps failing on a first enable: state unknown, never 'still running'")
(ROOT / ".env").write_text("NESTI_PROJECT_PATH=/srv/managed\n")
Path(PATHS.config("confbox"), ".env").write_text("API_TOKEN=tok-456\nHOOK_SECRET=%s\n" % SECRET)
ups_before = len(FAKE.argvs("up"))
FAKE.fail.add("configure")
code, _, err = run("enable", "confbox")
FAKE.fail.discard("configure")
check(code == 1 and "configure step failed" in err and len(FAKE.argvs("up")) == ups_before
      and registry()["packages"]["confbox"]["enabled"] is False
      and not [s for s in runtime()["subscriptions"] if s["package"] == "confbox"], "failed configure: nothing started, inactive")
FAKE.contexts = []
code, out, err = run("enable", "confbox")
calls = [c["argv"] for c in FAKE.calls]
conf_call = FAKE.argvs("configure.sh")[-1]
up = FAKE.argvs("up")[-1]["argv"]
check(code == 0 and calls.index(conf_call["argv"]) < calls.index(up), "configure runs before compose up: %s" % err.strip())
check(conf_call["cwd"] == PATHS.package("confbox", conf1) and conf_call["env"]["API_TOKEN"] == "tok-456"
      and conf_call["env"]["NESTI_PROJECT_PATH"] == "/srv/managed"
      and conf_call["env"]["NESTI_PLUGIN_WORK_DIR"] == PATHS.work("confbox", conf1),
      "configure gets the package settings, Nesti's project path and its work dir")
check(FAKE.contexts == [{"version": 1, "project_path": "/srv/managed", "skills": [
    {"package": "misc-skills", "skill": "alpha", "revision": misc_sha, "ref": misc_sha[:10], "arguments": {"level": "ultra"},
     "phases": ["code"], "text": "Alpha.\n"}]}], "runtime context: project path and other packages' enabled skills with text")
check(not os.path.exists(conf_call["env"]["NESTI_PLUGIN_CONTEXT"]), "the context file is removed after configure")
check("--force-recreate" in up and FAKE.argvs("up")[-1]["env"]["NESTI_PROJECT_PATH"] == "/srv/managed",
      "compose up recreates services and interpolates the project path")
code, out, _ = run("list")
check(registry()["packages"]["confbox"]["context_digest"] and "stale" not in out, "fresh enable: context digest recorded, not stale")
stops_before = len(FAKE.argvs("stop"))
FAKE.fail.add("configure")
code, _, err = run("enable", "confbox")
FAKE.fail.discard("configure")
rec = registry()["packages"]["confbox"]
check(code == 1 and "configure step failed" in err and len(FAKE.argvs("stop")) == stops_before + 1
      and FAKE.containers["nesti-plugin-confbox"][0][1] == "exited" and rec["enabled"] is False
      and "enable failed: configure step failed" in rec["error"] and not Path(PATHS.secrets("confbox")).exists()
      and not [s for s in runtime()["subscriptions"] if s["package"] == "confbox"],
      "failed configure on re-enable: running service stopped, disabled with the error, subscriptions off")
code, _, err = run("enable", "confbox")
check(code == 0 and FAKE.containers["nesti-plugin-confbox"][0][1] == "running", "enable again after the failure: %s" % err.strip())
FAKE.interrupt = True
code, _, _ = run("enable", "confbox")
FAKE.interrupt = False
rec = registry()["packages"]["confbox"]
check(code == 130 and rec["enabled"] is False and rec["error"] == "enable interrupted; service state unknown"
      and FAKE.containers["nesti-plugin-confbox"][0][1] == "exited" and not Path(PATHS.secrets("confbox")).exists()
      and not [s for s in runtime()["subscriptions"] if s["package"] == "confbox"],
      "interrupt during readiness: best-effort stop, disabled with 'state unknown', subscriptions off")
run("enable", "confbox")
FAKE.fail.add("configure-oserror")
code, _, err = run("enable", "confbox")
FAKE.fail.discard("configure-oserror")
rec = registry()["packages"]["confbox"]
check(code == 1 and "disk full" in err and rec["enabled"] is False and rec["error"] == "enable failed: disk full"
      and FAKE.containers["nesti-plugin-confbox"][0][1] == "exited"
      and not [s for s in runtime()["subscriptions"] if s["package"] == "confbox"],
      "OSError during configure: stopped, disabled with the error recorded, subscriptions off")
code, _, err = run("enable", "confbox")
check(code == 0 and FAKE.containers["nesti-plugin-confbox"][0][1] == "running", "enable after the OSError: %s" % err.strip())
bindings_path("misc-skills").write_text(json.dumps({"skills": {"alpha": {"phases": ["code"], "arguments": {"level": "lite"}}}}))
code, out, _ = run("enable", "misc-skills")
check(code == 0 and "Stale: confbox:" in out and "nesti /plugin enable confbox" in out, "a skill argument change reports the service as stale")
code, out, _ = run("list")
check("stale:    author skills" in out.split("confbox", 1)[1], "list shows the stale service")
FAKE.probe_ok = False
code, _, err = run("enable", "confbox")
rec = registry()["packages"]["confbox"]
check(code == 1 and rec["enabled"] is False and "enable failed" in rec["error"]
      and not [s for s in runtime()["subscriptions"] if s["package"] == "confbox"],
      "re-enable unpublishes first; a failed restart leaves it inactive with the error")
FAKE.probe_ok = True
code, out, err = run("enable", "confbox")
code_list, list_out, _ = run("list")
check(code == 0 and [s["package"] for s in runtime()["subscriptions"]] == ["confbox"] and "stale" not in out + list_out
      and FAKE.contexts[-1]["skills"][0]["arguments"] == {"level": "lite"},
      "re-enable regenerates with the new context and republishes after readiness: %s" % err.strip())
run("disable", "misc-skills")
code, out, _ = run("remove", "confbox")
check(code == 0 and "Stale" not in out and Path(PATHS.config("confbox"), ".env").exists(), "remove keeps settings")

# ---------------------------------------------------------------------------
print("\n[12] Plugin settings: a plain skill's argument-hint, a manifest setting")
LEVELS = BASE / "levels"
level_skill = '---\nname: levels\ndescription: >\n  Levels: lite, full (default), ultra.\nargument-hint: "[lite|full|ultra|off]"\n---\nLevels.\n'
level1 = commit(LEVELS, {"skills/levels/SKILL.md": level_skill,
                         "skills/levels-extra/SKILL.md": "---\nname: levels-extra\n---\nExtra.\n"}, tag="v1")
code, out, err = run("install", str(LEVELS), "--ref", "v1")
check(code == 0 and "setting:  args = full (plugin default) (choices: lite, full, ultra, off); change with: nesti /levels <value>"
      in out, "install prints the declared default, not the first argument-hint choice: %s" % err.strip())
code, out, _ = run("settings", "levels")
check(code == 0 and out == "levels settings:\n  args = full (plugin default) (choices: lite, full, ultra, off)\n"
      "Change with: nesti /levels <value>\n", "settings shows the upstream default and choices")
saved = bindings_path("levels").read_text()
check(json.loads(saved)["skills"]["levels"]["arguments"] == {}, "inferred default is not frozen in the bindings template")
code, _, err = run("enable", "levels")
check(code == 0 and [(s["phases"], s["arguments"]) for s in runtime()["skills"] if s["package"] == "levels"]
      == [(["plan", "code"], {"args": "full"})], "default reaches both effective runtime phases")
level2 = commit(LEVELS, {"skills/levels/SKILL.md": level_skill.replace("full (default), ultra", "full, ultra (default)")})
code, out, err = run("update", "levels")
check(code == 0 and registry()["packages"]["levels"]["sha"] == registry()["packages"]["levels"]["ref"] == level2
      and [s["arguments"] for s in runtime()["skills"] if s["package"] == "levels"] == [{"args": "ultra"}]
      and "args = ultra (plugin default)" in out and bindings_path("levels").read_text() == saved,
      "update picks the revised upstream default without rewriting the empty operator configuration")
for description in ("Levels: lite, full, ultra.", "Levels: lite (default), full (default), ultra.",
                    "Levels: max (default).", "The default is full."):
    commit(LEVELS, {"skills/levels/SKILL.md": level_skill.replace("Levels: lite, full (default), ultra.", description)})
    code, _, err = run("update", "levels")
    check(code == 0 and [s["arguments"] for s in runtime()["skills"] if s["package"] == "levels"] == [{}],
          "unknown or ambiguous declaration supplies no inferred arguments: %s" % description)
    code, out, _ = run("settings", "levels")
    check(code == 0 and "not set (plugin default unknown)" in out, "settings honestly reports an unknown default")
run("disable", "levels")
bindings_path("levels").write_text(json.dumps({"skills": {"levels": {"phases": ["code"], "arguments": {"level": "lite"}}}}))
saved = bindings_path("levels").read_text()
code, out, err = run("update", "levels", "--ref", "v1")
check(code == 0 and not registry()["packages"]["levels"]["enabled"]
      and bindings_path("levels").read_text() == saved
      and 'arguments = {"level": "lite"} (plugin default: full)' in out,
      "disabled update preserves and truthfully displays the arbitrary explicit argument")
code, out, _ = run("settings", "levels")
check(code == 0 and 'arguments = {"level": "lite"} (plugin default: full)' in out
      and "not set" not in out, "settings does not hide an explicit non-args override")
run("enable", "levels")
code, _, err = run("update", "levels", "--ref", level2[:10])
check(code == 0 and registry()["packages"]["levels"]["enabled"] and bindings_path("levels").read_text() == saved
      and [s["arguments"] for s in runtime()["skills"] if s["package"] == "levels"] == [{"level": "lite"}],
      "enabled update preserves the exact explicit argument without contradictory inferred args")
run("disable", "levels")
before = runtime()
code, out, err = run("settings", "levels", "ultra")
check(code == 0 and json.loads(bindings_path("levels").read_text())
      == {"skills": {"levels": {"phases": ["code"], "arguments": {"args": "ultra"}}}}
      and "next 'nesti /plugin enable levels'" in out and runtime() == before,
      "disabled: arguments become exactly {args}, phases kept, applied at the next enable: %s" % err.strip())
saved = bindings_path("levels").read_text()
code, _, err = run("settings", "levels", "max")
check(code == 2 and "one of: lite, full, ultra, off" in err and bindings_path("levels").read_text() == saved,
      "a value outside the choices: usage error, nothing written")
run("enable", "levels")
code, out, err = run("settings", "levels", "lite")
check(code == 0 and "Enabled levels" in out
      and [s["arguments"] for s in runtime()["skills"] if s["package"] == "levels"] == [{"args": "lite"}],
      "enabled: re-enabled with the new argument: %s" % err.strip())
run("disable", "levels")
code, out, _ = run("settings", "misc-skills")
check(code == 0 and out == "misc-skills offers no settings.\n", "no argument-hint: no settings")
code, _, err = run("settings", "misc-skills", "x")
check(code == 1 and "offers no settings" in err, "setting a plugin without a setting fails")
code, _, err = run("settings", "nope")
check(code == 1 and "not installed" in err, "an unknown plugin fails")
for label, settings in (("a repeated key", [{"key": "A"}, {"key": "A"}]), ("empty choices", [{"key": "A", "choices": []}]),
                        ("a secret with choices", [{"key": "A", "secret": True, "choices": ["x"]}]),
                        ("a non-boolean secret", [{"key": "A", "secret": "yes"}]),
                        ("a choice with a space", [{"key": "A", "choices": ["a b"]}]),
                        ("settings without compose", [{"key": "A"}])):
    extra = {"skills": [{"name": "s", "path": "s.md"}]} if "without compose" in label else {"compose": "compose.yml"}
    repo = BASE / ("bad-setting-" + label.replace(" ", "-"))
    commit(repo, {"nesti-plugin.json": json.dumps(dict({"schema_version": 1, "name": "bad", "nesti_plugin_api": 1,
                                                        "settings": settings}, **extra)),
                  "compose.yml": "services: {}\n", "s.md": "S.\n"}, tag="v1")
    code, _, err = run("install", str(repo), "--ref", "v1", "--trust")
    check(code == 1 and "settings must list" in err and not Path(PATHS.package("bad")).exists(), "%s rejected" % label)
SETBOX = BASE / "setbox"
commit(SETBOX, {"nesti-plugin.json": json.dumps(dict(manifest, name="setbox", settings=[{"key": "MODEL"}])),
                "compose.yml": "services: {}\n", "prepare.sh": "true\n", ".env.example": "API_TOKEN=\nHOOK_SECRET=\nMODEL=\n"},
       tag="v1")
code, out, err = run("install", str(SETBOX), "--ref", "v1", "--trust")
check(code == 0 and "setting:  MODEL = not set (plugin default); change with: nesti /setbox <value>" in out,
      "install prints the manifest setting: %s" % err.strip())
env_file = Path(PATHS.config("setbox"), ".env")
original = ("# reviewer settings\r\nAPI_TOKEN=tok-789\nexport MODEL=old/model # pick one\nHOOK_SECRET=%s\n\n# trailing" % SECRET).encode()
env_file.write_bytes(original)
os.chmod(str(env_file), 0o600)
ups = len(FAKE.argvs("up"))
model = "nvidia/nemotron-3-ultra-550b-a55b:free"
code, out, err = run("settings", "setbox", model)
check(code == 0 and env_file.read_bytes() == original.replace(b"export MODEL=old/model # pick one", b"export MODEL=" + model.encode())
      and stat.S_IMODE(env_file.stat().st_mode) == 0o600, "only the MODEL line changes; other bytes and mode 600 kept: %s" % err.strip())
check(len(FAKE.argvs("up")) == ups and "next 'nesti /plugin enable setbox'" in out, "disabled: saved, nothing restarted")
code, out, _ = run("settings", "setbox")
check(code == 0 and out == "setbox settings:\n  MODEL = %s\nChange with: nesti /setbox <value>\n" % model,
      "settings prints only the declared key, never other .env values")
saved = env_file.read_bytes()
for bad in ("a b", 'x"y', "a#b", "$HOME", "a\\b", "x" * 129, ""):
    code, _, err = run("settings", "setbox", bad)
    check(code == 2 and env_file.read_bytes() == saved, "invalid value %r rejected, nothing written" % bad[:12])
env_file.write_text("API_TOKEN=tok-789\nHOOK_SECRET=%s" % SECRET)
code, _, err = run("settings", "setbox", "deepseek/deepseek-v4-pro")
check(code == 0 and env_file.read_text() == "API_TOKEN=tok-789\nHOOK_SECRET=%s\nMODEL=deepseek/deepseek-v4-pro\n" % SECRET,
      "an absent key is appended on its own line: %s" % err.strip())
code, _, err = run("enable", "setbox")
ups = len(FAKE.argvs("up"))
code, out, err = run("settings", "setbox", model)
check(code == 0 and len(FAKE.argvs("up")) == ups + 1 and "Enabled setbox" in out
      and np._read_env(str(env_file))["MODEL"] == model and registry()["packages"]["setbox"]["enabled"],
      "enabled: the value is saved and the service re-enabled: %s" % err.strip())
run("remove", "setbox")

MULTIBOX = BASE / "multibox"
commit(MULTIBOX, {"nesti-plugin.json": json.dumps(dict(manifest, name="multibox", configure=["sh", "configure.sh"],
                   settings=[{"key": "MODEL", "choices": ["a/b", "c/d"]}, {"key": "API_KEY", "secret": True}])),
                  "compose.yml": "services: {}\n", "prepare.sh": "true\n", "configure.sh": "true\n",
                  ".env.example": "API_TOKEN=\nHOOK_SECRET=\n"}, tag="v1")
code, _, err = run("install", str(MULTIBOX), "--ref", "v1", "--trust")
check(code == 0, "multiple distinct settings install: %s" % err.strip())
env_file = Path(PATHS.config("multibox"), ".env")
original = ("API_TOKEN=tok-789\r\nAPI_KEY=old-key\nHOOK_SECRET=%s\n" % SECRET).encode()
env_file.write_bytes(original)
env_file.chmod(0o640)
code, out, err = run("settings", "multibox")
check(code == 0 and "MODEL = not set (plugin default) (choices: a/b, c/d)" in out
      and "API_KEY = set (secret)" in out and not any(s in out + err for s in ("old-key", "tok-789", SECRET)),
      "multiple settings display only declared public values and secret presence")
for args, diagnostic in ((("a/b",), "2 settings"), (("UNKNOWN", "c/d"), "has no setting UNKNOWN"),
                         (("API_KEY", "new-key"), "'-'")):
    code, out, err = run("settings", "multibox", *args)
    check(code == 2 and diagnostic in err and "new-key" not in out + err and env_file.read_bytes() == original,
          "ambiguous key, unknown key and argv secrets fail without writes: %s" % diagnostic)
code, _, _ = run("settings", "multibox", "MODEL", "c/d")
check(code == 0 and env_file.read_bytes() == original + b"MODEL=c/d\n", "explicit key appends only its value")
code, out, err = run("settings", "multibox", "API_KEY", "-", stdin="new-key\n")
check(code == 0 and env_file.read_bytes() == original.replace(b"old-key", b"new-key") + b"MODEL=c/d\n"
      and stat.S_IMODE(env_file.stat().st_mode) == 0o640 and "new-key" not in out + err,
      "stdin secret changes only its key, preserves mode and never echoes")
saved = env_file.read_bytes()
for bad in ("", "invalid secret\n", "$bad\n", "x" * 129 + "\n"):
    code, out, err = run("settings", "multibox", "API_KEY", "-", stdin=bad)
    check(code == 2 and env_file.read_bytes() == saved and (not bad.strip() or bad.strip() not in out + err),
          "invalid/EOF secret input is rejected without disclosure or writes")
with mock.patch.object(sys, "stdin") as stream, mock.patch.object(np.getpass, "getpass", return_value="hidden") as prompt:
    stream.isatty.return_value = True
    check(np._read_value("Value: ") == "hidden" and prompt.call_args == mock.call("Value: "),
          "TTY values use getpass")
    prompt.side_effect = EOFError
    check(np._read_value("Value: ") == "", "TTY EOF becomes empty input")
overview = np.plugin_overview(PATHS)
entry = next(e for e in overview if e["name"] == "multibox")
check([s["name"] for s in entry["settings"]] == ["MODEL", "API_KEY"]
      and entry["settings"][1]["text"] == "API_KEY = set (secret)"
      and [e["name"] for e in overview] == sorted(e["name"] for e in overview)
      and not any(s in json.dumps(overview) for s in ("new-key", "tok-789", SECRET)),
      "overview is sorted and secret-safe")
source_dir = Path(PATHS.package("multibox", registry()["packages"]["multibox"]["sha"]))
with mock.patch.object(np, "inspect_package", wraps=np.inspect_package) as inspect:
    original_inspect = inspect._mock_wraps
    inspect.side_effect = lambda path, source: (_ for _ in ()).throw(np.PluginError("broken package")) \
        if path == str(source_dir) else original_inspect(path, source)
    broken = np.plugin_overview(PATHS)
check(next(e for e in broken if e["name"] == "multibox")["error"] == "broken package"
      and any(e["settings"] for e in broken if e["name"] != "multibox"), "broken package does not hide other packages")
with mock.patch.object(np, "load_registry", return_value={"packages": {}}):
    check(np.plugin_overview(PATHS) == [], "empty overview")
with mock.patch.object(np, "load_registry", side_effect=np.PluginError("broken registry")):
    try:
        np.plugin_overview(PATHS)
        check(False, "registry errors propagate")
    except np.PluginError as exc:
        check(str(exc) == "broken registry", "registry errors propagate")


def noisy_runner(argv, **kwargs):
    result = FAKE(argv, **kwargs)
    if argv[:2] == ["sh", "configure.sh"]:
        assert not kwargs.get("stream"), "env-bearing output must be captured"
        assert kwargs.get("merge_output"), "both diagnostic streams must be captured"
        return result[0], "configured new-key tok-789 %s\n" % SECRET
    if "up" in argv and result[0]:
        return result[0], "compose failed new-key tok-789 %s" % SECRET
    return result


code, diagnostics = np.run_command([sys.executable, "-c", "import sys; print('ready'); print('notice', file=sys.stderr)"],
                                   merge_output=True)
check(code == 0 and "ready" in diagnostics and "notice" in diagnostics,
      "successful configure capture retains stdout and stderr diagnostics")
with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
    code = np.main(["enable", "multibox"], root=str(ROOT), runner=noisy_runner, compose=["docker", "compose"])
check(code == 0 and "configured [redacted]" in out.getvalue()
      and not any(s in out.getvalue() + err.getvalue() for s in ("new-key", "tok-789", SECRET)),
      "configure diagnostics remain useful but redact env values")
FAKE.fail.add("up")
with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
    code = np.main(["enable", "multibox"], root=str(ROOT), runner=noisy_runner, compose=["docker", "compose"])
FAKE.fail.discard("up")
error = registry()["packages"]["multibox"]["error"]
check(code == 1 and "compose failed [redacted]" in error and not registry()["packages"]["multibox"]["enabled"]
      and not any(s in out.getvalue() + err.getvalue() + error + json.dumps(np.plugin_overview(PATHS))
                  for s in ("new-key", "tok-789", SECRET)), "activation failures are redacted before persistence and overview")


boundary_secret = "sk-sensitive-credential-0123456789"
np._set_env(str(env_file), "API_KEY", boundary_secret)
for failing_command in ("up", "ps", "stop", "network"):
    run("enable", "multibox")
    failed_output = boundary_secret + "X" * 790

    def boundary_runner(argv, **kwargs):
        if failing_command == "network" and argv[:3] == ["docker", "network", "inspect"]:
            return 1, ""
        if ((failing_command == "up" and "up" in argv)
                or (failing_command in ("ps", "stop") and argv[:2] == ["docker", failing_command])
                or (failing_command == "network" and argv[:3] == ["docker", "network", "create"])):
            return 1, failed_output
        if "up" in argv:
            return 1, "activation refused"
        return FAKE(argv, **kwargs)

    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        code = np.main(["enable", "multibox"], root=str(ROOT), runner=boundary_runner, compose=["docker", "compose"])
    record = registry()["packages"]["multibox"]
    displayed = out.getvalue() + err.getvalue() + record["error"] + json.dumps(np.plugin_overview(PATHS))
    check(code == 1 and "failed (exit 1)" in err.getvalue() and "X" * 790 in displayed
          and boundary_secret not in displayed and "0123456789" not in displayed
          and not record["enabled"] and not Path(PATHS.secrets("multibox")).exists()
          and not [s for s in runtime()["subscriptions"] if s["package"] == "multibox"],
          "redaction precedes diagnostic truncation for activation/cleanup %s, including persisted errors" % failing_command)
    check(FAKE.containers["nesti-plugin-multibox"][0][1] == ("running" if failing_command in ("ps", "stop") else "exited")
          and (failing_command != "ps" or "service state unknown" in err.getvalue())
          and (failing_command != "stop" or "service still running" in err.getvalue()),
          "activation failure cleanup and state diagnostics remain intact for %s" % failing_command)

print("\n[13] Host menu actions and optional installer")
ast.parse((REPO / "scripts" / "nesti_menu.py").read_text(), feature_version=(3, 9))


class MenuUI:
    def __init__(self):
        self.prompts = []

    def Choice(self, title, value=None, disabled=False):
        return {"title": title, "value": value, "disabled": disabled}

    def Separator(self, title):
        return {"title": title, "separator": True}

    def select(self, message, **kwargs):
        self.prompts.append(("select", message, kwargs))

    def password(self, message, **kwargs):
        self.prompts.append(("password", message, kwargs))

    def text(self, message, **kwargs):
        self.prompts.append(("text", message, kwargs))

    def confirm(self, message, **kwargs):
        self.prompts.append(("confirm", message, kwargs))


ui = MenuUI()
secret = entry["settings"][1]
public = entry["settings"][0]
for name in ("stats", "arch", "boost", "provider", "usage"):
    with mock.patch.object(nm, "_ask", side_effect=[secret, "menu-secret"]), mock.patch.object(nm, "_run") as action:
        nm._plugin_menu(ui, dict(entry, name=name))
        check(action.call_args == mock.call(["/plugin", "settings", name, "API_KEY", "-"], stdin_text="menu-secret\n"),
              "conflicting plugin %s stays host-routed and keeps secrets off argv" % name)
for replies in ([None], ["back"], [secret, None], [secret, ""], [public, None]):
    with mock.patch.object(nm, "_ask", side_effect=replies), mock.patch.object(nm, "_run") as action:
        nm._plugin_menu(ui, entry)
        check(not action.called, "plugin cancellation/back never runs an action")
for replies, expected in (([public, "c/d"], ["/plugin", "settings", "multibox", "MODEL", "c/d"]),
                           (["enable"], ["/plugin", "enable", "multibox"]),
                           (["disable"], ["/plugin", "disable", "multibox"])):
    with mock.patch.object(nm, "_ask", side_effect=replies), mock.patch.object(nm, "_run") as action:
        nm._plugin_menu(ui, entry)
        check(action.call_args == mock.call(expected), "plugin selection runs the direct command")
free = dict(public, choices=None)
with mock.patch.object(nm, "_ask", side_effect=[free, "free/value"]), mock.patch.object(nm, "_run") as action:
    nm._plugin_menu(ui, dict(entry, settings=[free]))
    validate = ui.prompts[-1][2]["validate"]
    check(validate("free/value") is True and validate("bad value") is not True
          and action.call_args == mock.call(["/plugin", "settings", "multibox", "MODEL", "free/value"]),
          "free text validates and routes a declared key")
with mock.patch.object(nm.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "")) as child:
    check(nm._run(["/plugin", "settings", "multibox", "API_KEY", "-"], "hidden\n") == 0
          and child.call_args == mock.call(["sh", nm.LAUNCHER, "/plugin", "settings", "multibox", "API_KEY", "-"],
                                          input="hidden\n", text=True), "secret reaches child stdin, not argv")
with mock.patch.object(nm.subprocess, "run", side_effect=KeyboardInterrupt):
    check(nm._run(["/provider"]) == 130, "interrupted child preserves status 130")
provider_output = "  - future-provider (Authenticated)\n  - other-provider\n  - billed (platform API key)\n"
with mock.patch.object(nm.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, provider_output, "")):
    check(nm._consumers() == [("future-provider", True), ("other-provider", False)],
          "consumer names are dynamic, authenticated parsed, billed APIs excluded")
with mock.patch.object(nm.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "failed\n", "reason\n")), \
        contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
    check(nm._consumers() is None and out.getvalue() == "failed\n" and err.getvalue() == "reason\n",
          "provider listing errors are printed and cancel selection")
for outcome in (OSError("no docker"), subprocess.TimeoutExpired("docker", 10)):
    with mock.patch.object(nm.subprocess, "run", side_effect=outcome):
        check(not nm._orchestrator_running(), "unavailable Docker disables container actions")


def menu_session(replies, entries=None, running=True, consumers=None):
    ui = MenuUI()
    with mock.patch.dict(sys.modules, {"questionary": ui}), mock.patch.object(nm, "_ask", side_effect=replies), \
            mock.patch.object(nm, "_orchestrator_running", return_value=running), \
            mock.patch.object(np, "plugin_overview", return_value=[entry] if entries is None else entries) as overview, \
            mock.patch.object(nm, "_consumers", return_value=consumers), mock.patch.object(nm, "_run") as action:
        code = nm.main()
    return code, ui, action, overview


code, ui, action, overview = menu_session(["/usage", "exit"])
check(code == 0 and action.call_args == mock.call(["/usage"]) and overview.call_count == 2, "state refreshes after actions")
code, ui, action, _ = menu_session(["exit"], running=False)
choices = ui.prompts[0][2]["choices"]
check(all(c["disabled"] == nm.NOT_RUNNING for c in choices if c.get("value") in
          ("/provider", "login", "logout", "/usage", "/stats", "/arch", "/boost"))
      and not next(c for c in choices if c.get("value") == entry)["disabled"], "stopped container disables only provider/project actions")
for replies in (["logout", "future-provider", False, "exit"], ["/boost", False, "exit"],
                ["login", None, "exit"], [None]):
    code, ui, action, _ = menu_session(replies, consumers=[("future-provider", True)])
    check(code == 0 and not action.called and all(p[2]["default"] is False for p in ui.prompts if p[0] == "confirm"),
          "cancellation and default-false confirmations never act")
for replies, expected in ((["login", "other-provider", "exit"], ["/provider", "login", "other-provider"]),
                           (["logout", "future-provider", True, "exit"], ["/provider", "logout", "future-provider"]),
                           (["/boost", True, "exit"], ["/boost"]), (["/stats", "exit"], ["/stats"]),
                           (["/arch", "exit"], ["/arch"]), (["/provider", "exit"], ["/provider"])):
    code, ui, action, _ = menu_session(replies, consumers=[("future-provider", True), ("other-provider", False)])
    check(code == 0 and action.call_args == mock.call(expected), "provider/project action preserves direct CLI arguments")
    if replies[0] == "logout":
        check(ui.prompts[1][2]["choices"] == ["future-provider"], "logout offers only authenticated consumers")
with contextlib.redirect_stdout(io.StringIO()) as out:
    code, _, action, _ = menu_session(["logout", "exit"], consumers=[])
check("No consumer provider is logged in." in out.getvalue() and not action.called, "empty logout explains state")
code, ui, _, _ = menu_session(["exit"], entries=[])
check(any("No plugins installed" in c["title"] and c["disabled"] for c in ui.prompts[0][2]["choices"]),
      "empty plugin list offers installation guidance")
with mock.patch.dict(sys.modules, {"questionary": MenuUI()}), mock.patch.object(nm, "_orchestrator_running", return_value=False), \
        mock.patch.object(np, "plugin_overview", side_effect=np.PluginError("broken registry")), \
        mock.patch.object(nm, "_ask", return_value="exit"):
    check(nm.main() == 0, "broken registry does not prevent menu exit")
for exception in (type("NoConsoleScreenBufferError", (Exception,), {})(), ValueError("unrelated")):
    with mock.patch.dict(sys.modules, {"questionary": MenuUI()}), \
            mock.patch.object(nm, "_orchestrator_running", side_effect=exception), \
            contextlib.redirect_stderr(io.StringIO()) as err:
        try:
            code = nm.main()
            check(code == 1 and "winpty nesti" in err.getvalue(), "Windows console failure gives guidance")
        except ValueError:
            check(type(exception) is ValueError, "unrelated menu exceptions propagate")

installer = (REPO / "install.sh").read_text()
install_function = installer[installer.index("install_menu() {"):installer.index('LAUNCHER="$HOME/.local/bin/nesti"')]
install_root = BASE / "installer"
install_root.mkdir()
host_python = install_root / "host-python"
host_python.write_text('#!/bin/sh\n[ "$1" = -c ] && exit ${OLD_PYTHON:-0}\nmkdir .venv\nexit 1\n')
host_python.chmod(0o755)
script = 'set -Eeuo pipefail\nPYTHON=("%s")\n%s\necho plain-cli-survives\n' % (host_python, install_function)
for old in ("1", "0"):
    result = subprocess.run(["bash", "-c", script], cwd=install_root, env=dict(os.environ, OLD_PYTHON=old),
                            capture_output=True, text=True)
    check(result.returncode == 0 and "plain-cli-survives" in result.stdout and "Warning:" in result.stderr
          and not (install_root / ".venv").exists(), "failed new venv setup is optional and cleans only its partial directory")
(install_root / ".venv" / "Scripts").mkdir(parents=True)
sentinel = install_root / ".venv" / "keep"
sentinel.write_text("existing environment")
windows_python = install_root / ".venv" / "Scripts" / "python.exe"
windows_python.write_text('#!/bin/sh\n[ "$1" = -c ] && exit 0\necho pip-offline >&2\nexit 1\n')
windows_python.chmod(0o755)
result = subprocess.run(["bash", "-c", script], cwd=install_root, capture_output=True, text=True)
check(result.returncode == 0 and "pip-offline" in result.stderr and sentinel.read_text() == "existing environment",
      "existing Windows-path venv survives a pip failure and plain CLI setup continues")

print("\n%s" % ("All checks passed." if not _failures else "%d check(s) FAILED." % _failures))
_TMP.cleanup()
sys.exit(1 if _failures else 0)
