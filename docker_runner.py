"""
Docker runner – executes generated code inside an isolated sandbox container.

Responsibilities:
- Write generated files into a temporary workspace directory.
- Mount that workspace into a Docker container.
- Run one of four container recipes — Laravel/PHPUnit tests, OpenAPI (Scramble)
  export, greenfield bootstrap, or Scramble install — inside the container.
- Return stdout/stderr and a boolean success flag.

The AI developer never runs code on the host machine directly.
"""

import logging
import os
import re
from pathlib import Path

import docker
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sandbox command recipes.  Each is a list[str] (["bash", "-lc", <script>]) so
# docker-py passes it straight through: a str command is shlex-split, a list is
# not, so only bash ever parses the script body and the embedded quoting/command
# substitutions cannot be mangled on the way in.
# ---------------------------------------------------------------------------
# Ownership handling, shared by every recipe.
#
# NESTI_OWNER is captured *before* anything writes into /app, because
# `cp -a /tmp/skel/. /app/` applies the source directory's own root ownership
# to /app itself — a later `stat -c %u:%g /app` would then return 0:0 and the
# restoring chown would be a silent no-op, leaving the whole workspace
# root-owned and unwritable by the orchestrator.
#
# The restore runs from an EXIT trap rather than as the last statement: with
# `set -e` a red test suite aborts the script, and a workspace left root-owned
# would make the *next* retry fail to write its files — an infrastructure
# failure the model could never fix by rewriting its code.
_CAPTURE_OWNER = 'NESTI_OWNER="$(stat -c %u:%g /app)";'
_TRAP_OWNER = 'trap \'chown -R "$NESTI_OWNER" /app || true\' EXIT;'

_TEST_COMMAND = [
    "bash",
    "-lc",
    " ".join([
        "set -e;",
        _CAPTURE_OWNER,
        _TRAP_OWNER,
        "composer install --no-interaction --prefer-dist --no-progress;",
        "if [ -f artisan ]; then",
        "[ -f .env ] || cp .env.example .env;",
        "php artisan key:generate --force;",
        "php artisan config:clear;",
        # Recreate the database from scratch. The workspace is mounted
        # read-write, so attempt N's sqlite file survives into attempt N+1;
        # if the coder renames or edits its migration between attempts, the
        # already-applied table collides with the "pending" new migration
        # ("table already exists") and every later attempt fails on state the
        # model cannot see. The file is a gitignored test artifact.
        "rm -f database/database.sqlite;",
        "touch database/database.sqlite;",
        "php artisan migrate --force;",
        "php artisan test;",
        "else",
        "./vendor/bin/phpunit --testdox;",
        "fi",
    ]),
]

_OPENAPI_COMMAND = [
    "bash",
    "-lc",
    " ".join([
        "set -e;",
        _CAPTURE_OWNER,
        _TRAP_OWNER,
        "composer install --no-interaction --prefer-dist --no-progress;",
        "[ -f .env ] || cp .env.example .env;",
        "php artisan key:generate --force;",
        "php artisan config:clear;",
        "php artisan scramble:analyze || echo \"NESTI: scramble:analyze reported issues (advisory)\";",
        "php artisan scramble:export --path=openapi.json;",
        "php artisan route:list --json > storage/app/nesti-routes.json",
    ]),
]

_BOOTSTRAP_COMMAND_TEMPLATE = [
    "bash",
    "-lc",
    " ".join([
        "set -e;",
        _CAPTURE_OWNER,
        _TRAP_OWNER,
        "composer create-project --no-interaction --prefer-dist \"laravel/laravel:{version}\" /tmp/skel;",
        "rm -rf /tmp/skel/.git;",
        "cp -a /tmp/skel/. /app/;",
        "cd /app;",
        "[ -f .env ] || cp .env.example .env;",
        "php artisan key:generate --force;",
        "touch database/database.sqlite;",
        "php artisan install:api --no-interaction;",
        "composer require --no-interaction dedoc/scramble;",
        "php artisan vendor:publish --provider=\"Dedoc\\\\Scramble\\\\ScrambleServiceProvider\" --tag=\"scramble-config\"",
    ]),
]

_SCRAMBLE_INSTALL_COMMAND = [
    "bash",
    "-lc",
    " ".join([
        "set -e;",
        _CAPTURE_OWNER,
        _TRAP_OWNER,
        "composer require --no-interaction dedoc/scramble;",
        "php artisan vendor:publish --provider=\"Dedoc\\\\Scramble\\\\ScrambleServiceProvider\" --tag=\"scramble-config\"",
    ]),
]


class DockerRunner:
    def __init__(self):
        self.image = os.environ.get("DOCKER_SANDBOX_PHP_IMAGE", "nesti-sandbox-php")
        self.workdir = os.environ.get("DOCKER_SANDBOX_WORKDIR", "/app")
        self.timeout = int(os.environ.get("DOCKER_SANDBOX_TIMEOUT", "600"))
        self.bootstrap_timeout = int(
            os.environ.get("DOCKER_SANDBOX_BOOTSTRAP_TIMEOUT", "1800")
        )
        self.client = docker.from_env()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_tests(self, workspace_path: str) -> tuple[bool, str]:
        """
        Mount *workspace_path* and run the Laravel/PHPUnit test recipe.

        Returns
        -------
        (success, output)
            success – True if the test suite exited with code 0.
            output  – Combined stdout + stderr from the container.
        """
        return self._run(workspace_path, _TEST_COMMAND, self.timeout, "phpunit")

    def run_openapi_export(self, workspace_path: str) -> tuple[bool, str]:
        """
        Mount *workspace_path* and export the Scramble OpenAPI spec.

        Runs ``scramble:analyze`` (advisory), ``scramble:export`` and a
        ``route:list`` dump, then restores host ownership of the files the
        container created so a retry can rewrite them.

        Returns ``(success, output)`` — success is True on exit code 0.
        """
        return self._run(workspace_path, _OPENAPI_COMMAND, self.timeout, "openapi")

    def run_bootstrap(self, repo_path: str) -> tuple[bool, str]:
        """
        Scaffold a greenfield Laravel app (pinned to ``NESTI_LARAVEL_VERSION``)
        plus the Scramble package into *repo_path*.

        Returns ``(success, output)`` — success is True on exit code 0.
        """
        version = os.environ.get("NESTI_LARAVEL_VERSION", "^13.0")
        prefix, flag, script = _BOOTSTRAP_COMMAND_TEMPLATE
        command = [prefix, flag, script.format(version=version)]
        return self._run(repo_path, command, self.bootstrap_timeout, "bootstrap")

    def run_scramble_install(self, repo_path: str) -> tuple[bool, str]:
        """
        Install and publish the Scramble config into an existing *repo_path*.

        Returns ``(success, output)`` — success is True on exit code 0.
        """
        return self._run(
            repo_path, _SCRAMBLE_INSTALL_COMMAND, self.bootstrap_timeout, "scramble-install"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(
        self,
        workspace_path: str,
        command: list[str],
        timeout: int,
        label: str,
    ) -> tuple[bool, str]:
        """
        Run *command* inside the sandbox image against *workspace_path*.

        Keeps the detach → ``wait(timeout=…)`` → ``logs()`` →
        ``finally: remove(force=True)`` sequence (Absolute Rule 8): never the
        blocking ``containers.run(remove=True)`` form, which cannot enforce a
        run-duration timeout. *label* names the recipe in the log messages so
        the four recipes stay distinguishable. Never raises.
        """
        logger.info("Running %s in Docker sandbox (image: %s) …", label, self.image)
        container = None
        try:
            container = self.client.containers.run(
                image=self.image,
                command=command,
                volumes={
                    os.path.abspath(workspace_path): {
                        "bind": self.workdir,
                        "mode": "rw",
                    }
                },
                working_dir=self.workdir,
                remove=False,
                stdout=True,
                stderr=True,
                detach=True,
            )
            exit_info = container.wait(timeout=timeout)
            output = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            exit_code = exit_info["StatusCode"]
            if exit_code == 0:
                logger.info("%s passed.", label)
                return True, output
            logger.warning("%s FAILED (exit code %d):\n%s", label, exit_code, output)
            return False, output
        except requests.exceptions.ReadTimeout:
            msg = f"{label} container timed out after {timeout}s."
            logger.error(msg)
            return False, msg
        except docker.errors.ImageNotFound:
            msg = f"Docker image '{self.image}' not found. Build it first."
            logger.error(msg)
            return False, msg
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected Docker error while running %s: %s", label, exc)
            return False, str(exc)
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:  # pylint: disable=broad-except
                    pass

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    @staticmethod
    def write_files(llm_output: str, workspace_path: str) -> tuple[bool, list[str]]:
        """
        Parse the LLM output for ``### FILE: <path>`` blocks and write them
        into *workspace_path*.

        Returns the list of relative file paths that were written.
        """
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```(?:\w+)?\n(.*?)```",
            re.DOTALL,
        )
        written: list[str] = []
        for match in pattern.finditer(llm_output):
            rel_path = match.group(1).strip()
            content = match.group(2)
            abs_path = Path(workspace_path) / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            written.append(rel_path)
            logger.debug("Wrote %s", rel_path)

        if not written:
            logger.warning("No FILE blocks found in LLM output.")
            return False, []

        return  True, written
