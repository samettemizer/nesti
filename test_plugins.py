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

    def __call__(self, argv, cwd=None, env=None, timeout=None, stream=False):
        argv = list(argv)
        self.calls.append({"argv": argv, "cwd": cwd, "env": dict(env or {})})
        if argv[:2] == ["docker", "compose"]:
            if "config" in argv:
                return 0, json.dumps({
                    "services": {"receiver": {"image": "hookbox:test", "networks": {"default": None, "nesti-plugins": None},
                                              "volumes": [{"type": "volume", "source": "data", "target": "/data"}]}},
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
        if argv[0] == "sh":
            return (1 if "prepare" in self.fail else 0), ""
        raise AssertionError("unexpected argv %r" % argv)

    def argvs(self, word):
        return [c for c in self.calls if word in c["argv"]]


FAKE = FakeDocker()


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(sys, "stdin", io.StringIO()):
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
    check([np.absolute_local(u) for u in ("git@host:o/r", "host:repo", "C:/x", "https://h/o/r")]
          == ["git@host:o/r", "host:repo", "C:/x", "https://h/o/r"], "POSIX: scp-like, SSH alias, C:/x and URLs stay as typed")
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
            "ext::sh -c touch% /tmp/pwned", "-uhttps://github.com/a/b", "http://github.com/a/b", "user:pw@host:a/b"):
    code, _, err = run("install", "--ref", "v1", "--", url)
    check(code == 1, "URL refused: %s" % url)
check(not os.listdir(PATHS.tmp), "refused/failed installs leave no scratch directories")
code, _, _ = run("install", str(PONY))
check(code == 2, "--ref is required (usage error)")
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
      and "service receiver: hookbox:test" in out and "mount: volume data -> /data" in out and "network nesti-plugins (external)" in out,
      "trust summary shows repository, SHA, prepare, services, volumes/mounts, networks")
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
code, _, err = run("update", "hookbox", "--ref", "v2")
check(code == 1 and "--trust" in err and registry()["packages"]["hookbox"]["sha"] == hook1 and runtime() == before
      and not Path(PATHS.package("hookbox", hook2)).exists(), "new SHA needs renewed trust; old revision untouched")
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

print("\n%s" % ("All checks passed." if not _failures else "%d check(s) FAILED." % _failures))
_TMP.cleanup()
sys.exit(1 if _failures else 0)
