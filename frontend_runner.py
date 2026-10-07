"""
frontend_runner.py – runs Vitest and Playwright tests in isolated Docker containers.

Works identically to docker_runner.py but targets the frontend sandbox images:

    run_vitest()     → nesti-sandbox-node  (Vitest + Vue Test Utils, no browser)
    run_playwright() → nesti-sandbox-e2e   (headless Chromium via Playwright)

``run_vitest`` returns ``(success, output)``, matching
``DockerRunner.run_tests()``.  ``run_playwright`` returns
``{"passed", "output", "fixture_request"}``: the E2E sandbox prepares a Laravel
application's declared fixtures (``e2e/nesti-fixtures.json``) before the
browser starts, and a verified missing-seeder report is the one outcome that
is not an ordinary test failure.

Container lifecycle
───────────────────
The detach → ``wait(timeout=…)`` → ``logs()`` → ``finally: remove(force=True)``
sequence is copied deliberately from DockerRunner rather than using the
shorter blocking ``containers.run(remove=True)`` form:

  • ``containers.run()`` does not accept a run-duration timeout — the kwarg is
    forwarded to container creation and rejected.  A hung ``vite preview`` or a
    browser that never reaches its URL would then block the orchestrator
    forever.  Playwright makes that a realistic failure mode, not a theoretical
    one, which is why the timeout has to be enforceable here.
  • The ``finally`` block still guarantees no sandbox container survives the
    call, which is the property Absolute Rule 8 protects.

The command comes from each image's CMD, so the install/build/test recipe
lives in exactly one place: the Dockerfile.

Fixture report transport
────────────────────────
For Playwright the runner mounts a fresh host directory at ``/nesti-results``
— outside the generated repository — and reads the helper's bounded report
from it afterwards (see e2e_fixtures.py).  Only exit code 78 together with a
valid report naming a declared requirement yields ``fixture_request``; a
Laravel run that exits 0 must have left a ``ready`` report.  Every other
combination — a timeout, a failed suite, a stdout marker, a stale or
mismatched report — is an ordinary failure carrying the original logs.
"""

import logging
import os
import tempfile
from pathlib import Path

import docker
import requests

from e2e_fixtures import (
    EXIT_MISSING_SEEDER,
    REPORT_FILENAME,
    RESULTS_MOUNT,
    STATUS_MISSING_SEEDER,
    STATUS_READY,
    load_requirements,
    read_fixture_report,
)

logger = logging.getLogger(__name__)

_E2E_REBUILD_HINT = (
    "Rebuild the E2E sandbox image so it carries the fixture helper: "
    "docker build -t nesti-sandbox-e2e -f Dockerfile.sandbox.e2e ."
)
_HELPER_PATH = "/opt/nesti/e2e_fixtures.php"


class FrontendRunner:
    """Executes the two frontend test layers inside their sandbox images."""

    def __init__(self) -> None:
        self.client = docker.from_env()
        self.node_image = os.environ.get("DOCKER_SANDBOX_NODE_IMAGE", "nesti-sandbox-node")
        self.e2e_image = os.environ.get("DOCKER_SANDBOX_E2E_IMAGE", "nesti-sandbox-e2e")
        self.workdir = os.environ.get("DOCKER_SANDBOX_WORKDIR", "/app")
        self.timeout = int(os.environ.get("DOCKER_SANDBOX_TIMEOUT", "180"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_vitest(self, workspace_path: str) -> tuple[bool, str]:
        """
        Mount *workspace_path* and run Vitest component tests.

        Returns
        -------
        (success, output)
            success – True if the Vitest run exited with code 0.
            output  – Combined stdout + stderr from the container.
        """
        logger.info("Running Vitest in Docker sandbox (image: %s) …", self.node_image)
        passed, output, _exit_code = self._run(self.node_image, workspace_path, "Vitest")
        return passed, output

    def run_playwright(self, workspace_path: str) -> dict:
        """
        Mount *workspace_path* and run Playwright E2E tests.

        The image CMD installs dependencies, prepares a Laravel application's
        database and declared fixtures, builds the app, and lets Playwright's
        ``webServer`` config serve it before the specs run.

        Returns
        -------
        {"passed": bool, "output": str, "fixture_request": dict | None}
            passed          – True when the browser suite ran and exited 0
                              (for Laravel: after a ``ready`` fixture report).
            output          – Combined stdout + stderr from the container.
            fixture_request – the declared requirement (endpoint, model,
                              seeder, table) whose seeder class and file are
                              both absent; None for every other outcome.
        """
        logger.info("Running Playwright in Docker sandbox (image: %s) …", self.e2e_image)
        is_laravel = (Path(workspace_path) / "artisan").is_file()
        try:
            requirements = load_requirements(workspace_path)
        except (OSError, ValueError) as exc:
            message = f"E2E fixture manifest rejected before the sandbox started: {exc}"
            logger.warning(message)
            return {"passed": False, "output": message, "fixture_request": None}
        if requirements and not is_laravel:
            message = (
                "E2E fixture manifest e2e/nesti-fixtures.json declares fixtures, but the "
                "workspace is not a Laravel application (no artisan): only a Laravel "
                "application can prepare them. Remove the manifest or its fixtures."
            )
            logger.warning(message)
            return {"passed": False, "output": message, "fixture_request": None}

        with tempfile.TemporaryDirectory(
            prefix="nesti-e2e-results-", dir="/tmp", ignore_cleanup_errors=True
        ) as results:
            passed, output, exit_code = self._run(
                self.e2e_image, workspace_path, "Playwright", result_directory=results
            )
            report = (
                read_fixture_report(os.path.join(results, REPORT_FILENAME), exit_code, requirements)
                if is_laravel else None
            )

        if not is_laravel:
            return {"passed": passed, "output": output, "fixture_request": None}
        if exit_code == EXIT_MISSING_SEEDER and report and report["status"] == STATUS_MISSING_SEEDER:
            requirement = report["requirement"]
            logger.warning(
                "Playwright not started: declared fixture GET %s needs %s, whose class and "
                "file are both absent.",
                requirement["endpoint"], requirement["seeder"],
            )
            return {"passed": False, "output": output, "fixture_request": requirement}
        if exit_code == 0 and not (report and report["status"] == STATUS_READY):
            message = (
                "E2E fixture preparation left no valid ready report although the sandbox "
                f"exited 0. {_E2E_REBUILD_HINT}"
            )
            logger.error(message)
            return {"passed": False, "output": f"{output}\n{message}", "fixture_request": None}
        if exit_code == EXIT_MISSING_SEEDER or f"Could not open input file: {_HELPER_PATH}" in output:
            # A 78 without a matching report, or an image without the helper.
            return {
                "passed": False,
                "output": f"{output}\nE2E fixture protocol error. {_E2E_REBUILD_HINT}",
                "fixture_request": None,
            }
        return {"passed": passed, "output": output, "fixture_request": None}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(
        self,
        image: str,
        workspace_path: str,
        layer: str,
        result_directory: str | None = None,
    ) -> tuple[bool, str, int | None]:
        """
        Run *image* against *workspace_path*; never raises.

        Returns ``(passed, output, exit_code)``; *exit_code* is None when the
        container never finished (timeout, missing image, Docker error).
        *result_directory*, when given, is mounted read-write at
        ``/nesti-results`` for the fixture helper's report.
        """
        volumes = {
            os.path.abspath(workspace_path): {"bind": self.workdir, "mode": "rw"},
        }
        if result_directory is not None:
            volumes[os.path.abspath(result_directory)] = {"bind": RESULTS_MOUNT, "mode": "rw"}
        container = None
        try:
            container = self.client.containers.run(
                image=image,
                # No command: each sandbox image's CMD owns its recipe.
                volumes=volumes,
                working_dir=self.workdir,
                remove=False,
                stdout=True,
                stderr=True,
                detach=True,
            )
            exit_info = container.wait(timeout=self.timeout)
            output = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            exit_code = exit_info["StatusCode"]
            if exit_code == 0:
                logger.info("%s tests passed.", layer)
                return True, output, exit_code
            if exit_code == EXIT_MISSING_SEEDER:
                # Preparation stopped before any test ran: not a failed suite.
                logger.warning("%s preparation stopped (exit code %d).", layer, exit_code)
                return False, output, exit_code
            logger.warning("%s tests FAILED (exit code %d):\n%s", layer, exit_code, output)
            return False, output, exit_code
        except requests.exceptions.ReadTimeout:
            msg = f"{layer} container timed out after {self.timeout}s."
            logger.error(msg)
            partial = ""
            if container is not None:
                try:
                    partial = container.logs(stdout=True, stderr=True).decode(
                        "utf-8", errors="replace"
                    )
                except Exception:  # pylint: disable=broad-except
                    partial = ""
            return False, f"{partial}\n{msg}" if partial else msg, None
        except docker.errors.ImageNotFound:
            msg = f"Docker image '{image}' not found. Build it first."
            logger.error(msg)
            return False, msg, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected Docker error while running %s: %s", layer, exc)
            return False, str(exc), None
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:  # pylint: disable=broad-except
                    pass
