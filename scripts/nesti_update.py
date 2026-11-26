#!/usr/bin/env python3
"""Host-side ``nesti update``: bring this Nesti checkout to the latest GitHub release.

Runs on the host through ``scripts/nesti`` with Python 3.6+ and the standard library only.

  nesti update          fast-forward the current branch to the newest release tag, then rebuild,
                        restart and refresh .venv the way install.sh does
  nesti update --check  compare the installed version with the latest release; changes nothing

Internal subcommands (scripts/nesti and this script call them; not shown in --help):
  notice <command>   print the release notice from the cache; start a background refresh when stale
  refresh            store the latest release in the cache, silently
  apply <old> <new>  post-update steps, run from the newly merged copy of this file

Installed version: the newest stable vX.Y.Z tag that is an ancestor of HEAD. Latest version: the
newest non-draft, non-prerelease GitHub Release. The notice cache is state/update-check.json:
  {"version": 1, "checked_at": <unix seconds>, "latest": "vX.Y.Z" | null}
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

REPOSITORY = "samettemizer/nesti"
API_URL = "https://api.github.com/repos/%s/releases/latest" % REPOSITORY
SOURCE_URL = "https://github.com/%s.git" % REPOSITORY
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_VERSION = 1
CACHE_TTL = 24 * 3600
CHECK_TIMEOUT = 15
REFRESH_TIMEOUT = 5
READY_ATTEMPTS = 60
READY_INTERVAL = 2
EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_AVAILABLE = 0, 1, 2, 3
ORCHESTRATOR = "nesti-orchestrator"
VERSION_RE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
UNKNOWN_VERSION = ("cannot determine the installed version: no vX.Y.Z release tag is an ancestor of HEAD "
                   "(run 'git fetch --tags' in %s, or reinstall Nesti with 'git clone')")
EPILOG = """exit status:
  0  up to date (--check), or updated / already current
  1  error or refusal (network, unknown installed version, local changes, Docker)
  2  invalid arguments
  3  update available (--check only)

A newer release is also announced when you run nesti on a terminal; set
NESTI_NO_UPDATE_CHECK=1 to turn that off."""


class UpdateError(Exception):
    """An update step failed or was refused; the message is shown to the operator."""


def parse_version(tag) -> Optional[Tuple[int, int, int]]:
    """(major, minor, patch) for a stable vX.Y.Z tag, else None (rc and other pre tags included)."""
    match = VERSION_RE.fullmatch(tag) if isinstance(tag, str) else None
    return tuple(int(part) for part in match.groups()) if match else None


def update_status(installed: Optional[str], latest: Optional[str]) -> str:
    """'available', 'current' (also when no release exists) or 'unknown' (installed version unknown)."""
    if latest is None:
        return "current"
    if installed is None:
        return "unknown"
    return "available" if parse_version(latest) > parse_version(installed) else "current"


def _git(root: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", root] + list(args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True,
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    if check and proc.returncode:
        raise UpdateError("git %s failed: %s" % (args[0], proc.stderr.strip()))
    return proc


def installed_version(root: str) -> Optional[str]:
    """Newest stable vX.Y.Z tag reachable from HEAD, or None."""
    try:
        proc = _git(root, "tag", "--merged", "HEAD", "--list", "v*", check=False)
    except OSError:
        return None
    if proc.returncode:
        return None
    return max((tag for tag in proc.stdout.split() if parse_version(tag)), key=parse_version, default=None)


def parse_release(data) -> Optional[str]:
    """tag_name of a published stable release object, else None."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = data.get("tag_name")
    return tag if parse_version(tag) else None


def fetch_latest(timeout: float) -> Optional[str]:
    """Tag of the latest GitHub Release; None when none is published. Raises UpdateError."""
    import urllib.error
    import urllib.request  # imported here: the notice path stays fast
    request = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "nesti-update"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise UpdateError("GitHub answered HTTP %d for %s" % (exc.code, API_URL))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise UpdateError("cannot read the latest release from GitHub (%s)" % getattr(exc, "reason", exc))
    return parse_release(data)


# --- Notice cache --------------------------------------------------------------

def cache_path(root: str) -> str:
    return os.path.join(root, "state", "update-check.json")


def read_cache(root: str) -> Optional[Dict]:
    try:
        with open(cache_path(root), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
        return None
    checked, latest = data.get("checked_at"), data.get("latest")
    if isinstance(checked, bool) or not isinstance(checked, (int, float)):
        return None
    if latest is not None and not parse_version(latest):
        return None
    return {"checked_at": float(checked), "latest": latest}


def cache_is_stale(cache: Optional[Dict], now: float) -> bool:
    return cache is None or not 0 <= now - cache["checked_at"] < CACHE_TTL


def write_cache(root: str, latest: Optional[str], now: float) -> None:
    path = cache_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".update-check-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"version": CACHE_VERSION, "checked_at": now, "latest": latest}, handle)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def refresh(root: str) -> None:
    """Store the latest release; a failed lookup keeps the previous answer until the next day."""
    cache = read_cache(root)
    latest = cache["latest"] if cache else None
    try:
        latest = fetch_latest(REFRESH_TIMEOUT)
    except UpdateError:
        pass
    write_cache(root, latest, time.time())


def _spawn_refresh(root: str) -> None:
    """Start `refresh` detached from the terminal; the caller never waits for it."""
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "refresh"], cwd=root, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)


def should_notify(command: str, environ, stderr_tty: bool) -> bool:
    if not stderr_tty or command in ("mcp", "update"):
        return False
    return environ.get("NESTI_NO_UPDATE_CHECK", "") in ("", "0")


def render_notice(installed: str, latest: str, color: bool, fancy: bool) -> str:
    """A bordered box (green unless NO_COLOR) naming both versions and the update command."""
    lines = ["Nesti release %s is out." % latest, "You are running %s." % installed, "Update with:  nesti update"]
    width = max(len(line) for line in lines) + 4
    tl, tr, bl, br, h, v = "╭╮╰╯─│" if fancy else "++++-|"
    green, bold, reset = ("\x1b[32m", "\x1b[1m", "\x1b[0m") if color else ("", "", "")
    out = [green + tl + h * width + tr + reset]
    for line in lines:
        body = "  " + line + " " * (width - 2 - len(line))
        if color:
            body = body.replace("nesti update", bold + "nesti update" + reset)
        out.append(green + v + reset + body + green + v + reset)
    out.append(green + bl + h * width + br + reset)
    return "\n".join(out) + "\n"


def notice(root: str, command: str, environ, stderr_tty: bool, stream, now: Optional[float] = None) -> None:
    if not should_notify(command, environ, stderr_tty):
        return
    now = time.time() if now is None else now
    cache = read_cache(root)
    if cache_is_stale(cache, now):
        _spawn_refresh(root)
    latest = cache["latest"] if cache else None
    installed = installed_version(root) if latest else None
    if installed and update_status(installed, latest) == "available":
        try:
            "╭╮╰╯─│".encode(getattr(stream, "encoding", None) or "ascii")
            fancy = True
        except (LookupError, UnicodeEncodeError):
            fancy = False
        stream.write(render_notice(installed, latest, not environ.get("NO_COLOR"), fancy))
        stream.flush()


# --- Update ----------------------------------------------------------------------

def _say(message: str) -> None:
    print(message, flush=True)


def _run(argv: List[str], cwd: str, env: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
    """Run a Docker or pip command quietly: (exit status, combined output)."""
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)
    except OSError as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout


def _tail(output: str, lines: int = 30) -> str:
    return "\n".join(output.rstrip().splitlines()[-lines:])


def compose_command(root: str) -> List[str]:
    """install.sh's choice: docker-compose, else docker compose; refuses when Docker is not usable."""
    if _run(["docker", "info"], root)[0]:
        raise UpdateError("'docker info' failed: start Docker (or add your user to the docker group), "
                          "then run 'nesti update' again. Nothing was changed.")
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if _run(["docker", "compose", "version"], root)[0] == 0:
        return ["docker", "compose"]
    raise UpdateError("neither 'docker-compose' nor 'docker compose' is available; install Docker Compose, "
                      "then run 'nesti update' again. Nothing was changed.")


def _is_ancestor(root: str, older: str, newer: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def check(root: str) -> int:
    latest = fetch_latest(CHECK_TIMEOUT)
    installed = installed_version(root)
    print("Installed: %s" % (installed or "unknown"))
    print("Latest:    %s" % (latest or "no release published"))
    status = update_status(installed, latest)
    if latest is None:
        print("No stable Nesti release is published on GitHub yet; nothing to update.")
        return EXIT_OK
    if status == "unknown":
        raise UpdateError(UNKNOWN_VERSION % root)
    if status == "available":
        print("Update available: run 'nesti update'.")
        return EXIT_AVAILABLE
    print("Nesti is up to date.")
    return EXIT_OK


def update(root: str) -> int:
    if _git(root, "rev-parse", "--is-inside-work-tree", check=False).returncode:
        raise UpdateError("%s is not a git checkout; 'nesti update' needs the 'git clone' install." % root)
    latest = fetch_latest(CHECK_TIMEOUT)
    installed = installed_version(root)
    if latest is None:
        _say("No stable Nesti release is published on GitHub yet; nothing to update.")
        return EXIT_OK
    status = update_status(installed, latest)
    if status == "current":
        _say("Nesti %s is up to date (latest release: %s)." % (installed, latest))
        return EXIT_OK
    if status == "unknown":
        _say("The installed version is unknown (no vX.Y.Z tag is an ancestor of HEAD); "
             "comparing your branch with %s." % latest)

    branch = _git(root, "symbolic-ref", "-q", "--short", "HEAD", check=False)
    if branch.returncode:
        raise UpdateError("HEAD is detached; check out your branch (for example 'git switch develop') "
                          "and run 'nesti update' again. Nothing was changed.")
    branch = branch.stdout.strip()
    dirty = _git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()
    if dirty:
        shown = "\n".join("  " + line for line in dirty[:10]) + ("\n  ..." if len(dirty) > 10 else "")
        raise UpdateError("tracked files have uncommitted changes:\n%s\nCommit or revert these changes yourself, "
                          "then run 'nesti update' again. Nesti never discards or stashes your work; "
                          "nothing was changed." % shown)
    compose_command(root)

    _say("Updating Nesti %s -> %s" % (installed or "(unknown version)", latest))
    _say("Fetching %s from GitHub ..." % latest)
    fetched = _git(root, "fetch", "--quiet", "--no-tags", SOURCE_URL, "refs/tags/" + latest, check=False)
    if fetched.returncode:
        raise UpdateError("cannot fetch %s from %s: %s" % (latest, SOURCE_URL, fetched.stderr.strip()))
    tag_object = _git(root, "rev-parse", "--verify", "FETCH_HEAD").stdout.strip()
    target = _git(root, "rev-parse", "--verify", "FETCH_HEAD^{commit}").stdout.strip()
    if _is_ancestor(root, target, "HEAD"):
        _say("Branch '%s' already contains %s; nothing to update." % (branch, latest))
        return EXIT_OK
    if not _is_ancestor(root, "HEAD", target):
        raise UpdateError("branch '%s' has commits that are not in %s, so it cannot fast-forward. Nesti never "
                          "merges, rebases or resets your branch; reconcile it yourself (see 'git log %s..HEAD' "
                          "after 'git fetch %s tag %s'), then run 'nesti update' again. Nothing was changed."
                          % (branch, latest, latest, SOURCE_URL, latest))
    merged = _git(root, "merge", "--ff-only", "--quiet", target, check=False)
    if merged.returncode:
        raise UpdateError("git refused the fast-forward to %s:\n%s" % (latest, (merged.stderr or merged.stdout).strip()))
    _say("Fast-forwarded %s to %s." % (branch, latest))
    ref = "refs/tags/" + latest
    existing = _git(root, "rev-parse", "-q", "--verify", ref, check=False).stdout.strip()
    if not existing:
        _git(root, "update-ref", ref, tag_object, "")
    elif existing != tag_object:
        print("Warning: your local tag %s differs from GitHub's; it was left unchanged." % latest, file=sys.stderr)
    # The merged copy of this file runs the install steps, so a release can change its own.
    return subprocess.call([sys.executable, os.path.join(root, "scripts", "nesti_update.py"), "apply",
                            installed or "unknown", latest], cwd=root)


def apply(root: str, old: str, new: str) -> int:
    """Rebuild and restart the containers, wait for the orchestrator, refresh .venv (install.sh steps 6, 7, 9)."""
    compose = compose_command(root)
    retry = "The code is already at %s; after fixing the cause run: %s build && %s up -d" % (
        new, " ".join(compose), " ".join(compose))
    steps = (("Rebuilding containers (this can take a few minutes) ...", compose + ["build"]),
             ("Starting containers ...", compose + ["up", "-d"]))
    env = dict(os.environ, COMPOSE_PARALLEL_LIMIT="1")  # stats and orchestrator share an image tag
    for message, argv in steps:
        _say(message)
        code, output = _run(argv, root, env)
        if code:
            raise UpdateError("'%s' failed (exit %d):\n%s\n%s" % (" ".join(argv), code, _tail(output), retry))
    _say("Waiting for the orchestrator ...")
    for _ in range(READY_ATTEMPTS):
        if _run(["docker", "exec", ORCHESTRATOR, "nesti", "/provider"], root)[0] == 0:
            break
        time.sleep(READY_INTERVAL)
    else:
        print(_run(compose + ["logs", "--tail", "50", ORCHESTRATOR], root)[1], file=sys.stderr)
        raise UpdateError("%s did not answer 'nesti /provider' within %d s.\n%s"
                          % (ORCHESTRATOR, READY_ATTEMPTS * READY_INTERVAL, retry))
    if os.path.isdir(os.path.join(root, ".venv")):
        venv_python = os.path.join(root, ".venv", "Scripts", "python.exe")
        if not os.path.isfile(venv_python):
            venv_python = os.path.join(root, ".venv", "bin", "python")
        _say("Refreshing .venv ...")
        code, output = _run([venv_python, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r",
                             os.path.join(root, "requirements-host.txt")], root)
        if code:
            print("%s\nWarning: refreshing .venv failed; the interactive 'nesti' menu may be outdated, every "
                  "'nesti <command>' still works. Re-run ./install.sh to retry." % _tail(output), file=sys.stderr)
    _say("Nesti is now %s (was %s)." % (new, old))
    return EXIT_OK


def _guarded(action) -> int:
    try:
        return action()
    except (UpdateError, OSError) as exc:
        print("nesti update: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("nesti update: interrupted.", file=sys.stderr)
        return 130


def main(argv: Optional[List[str]] = None, root: str = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["notice"]:
        try:  # scripts/nesti checked that stderr is a terminal; any failure stays silent
            notice(root, argv[1] if len(argv) > 1 else "", os.environ, True, sys.stderr)
        except Exception:
            pass
        return EXIT_OK
    if argv == ["refresh"]:
        try:
            refresh(root)
        except Exception:
            pass
        return EXIT_OK
    if argv[:1] == ["apply"] and len(argv) == 3:
        return _guarded(lambda: apply(root, argv[1], argv[2]))
    import argparse
    parser = argparse.ArgumentParser(
        prog="nesti update", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=EPILOG,
        description="Update Nesti to the latest GitHub release of %s: fast-forward the current branch to the "
                    "release tag, then rebuild and restart the containers and refresh .venv." % REPOSITORY)
    parser.add_argument("--check", action="store_true",
                        help="show the installed and latest versions and whether an update exists; changes nothing")
    if argv[:1] != ["update"]:
        parser.print_usage(sys.stderr)
        return EXIT_USAGE
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return exc.code
    return _guarded(lambda: check(root) if args.check else update(root))


if __name__ == "__main__":
    sys.exit(main())
