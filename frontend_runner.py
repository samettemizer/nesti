"""
frontend_runner.py – runs Vitest and Playwright tests in isolated Docker containers.

Works identically to docker_runner.py but targets the frontend sandbox images:

    run_vitest()     → nesti-sandbox-node  (Vitest + Vue Test Utils, no browser)
    run_playwright() → nesti-sandbox-e2e   (headless Chromium via Playwright)

Both return ``(success, output)``, matching ``DockerRunner.run_tests()``.

Container lifecycle
───────────────────
The detach → ``wait(timeout=…)`` → ``logs()`` → ``finally: remove(force=True, v=True)``
sequence is copied deliberately from DockerRunner rather than using the
shorter blocking ``containers.run(remove=True)`` form:

  • ``containers.run()`` does not accept a run-duration timeout — the kwarg is
    forwarded to container creation and rejected.  A hung ``vite preview`` or a
    browser that never reaches its URL would then block the orchestrator
    forever.  Playwright makes that a realistic failure mode, not a theoretical
    one, which is why the timeout has to be enforceable here.
  • The ``finally`` block still guarantees no sandbox container survives the
    call, which is the property Absolute Rule 8 protects.  ``v=True`` also
    deletes the anonymous volume mounted at ``<workdir>/node_modules``: npm
    installs there, never into the host workspace, so host mount options
    (``noexec`` breaks esbuild's postinstall) and stale host packages cannot
    affect a run.

The command comes from each image's CMD, so the install/build/test recipe
lives in exactly one place: the Dockerfile.
"""

import logging
import os
import secrets

import docker
import requests

logger = logging.getLogger(__name__)


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
        return self._run(self.node_image, workspace_path, "Vitest")

    def run_playwright(self, workspace_path: str) -> tuple[bool, str]:
        """
        Mount *workspace_path* and run Playwright E2E tests.

        The image CMD installs dependencies, builds the SPA, and lets
        Playwright's ``webServer`` config serve it before the specs run.

        Returns
        -------
        (success, output)
            success – True if the Playwright run exited with code 0.
            output  – Combined stdout + stderr from the container.
        """
        logger.info("Running Playwright in Docker sandbox (image: %s) …", self.e2e_image)
        return self._run(self.e2e_image, workspace_path, "Playwright")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(self, image: str, workspace_path: str, layer: str) -> tuple[bool, str]:
        """Run *image* against *workspace_path*; never raises. Returns ``(passed, output)``."""
        volumes = {
            os.path.abspath(workspace_path): {"bind": self.workdir, "mode": "rw"},
        }
        name = f"nesti-fe-{secrets.token_hex(6)}"
        container = None
        try:
            container = self.client.containers.run(
                image=image,
                name=name,
                # No command: each sandbox image's CMD owns its recipe.
                volumes=volumes,
                working_dir=self.workdir,
                mounts=[docker.types.Mount(f"{self.workdir}/node_modules", None, type="volume")],
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
                return True, output
            logger.warning("%s tests FAILED (exit code %d):\n%s", layer, exit_code, output)
            return False, output
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
            return False, f"{partial}\n{msg}" if partial else msg
        except docker.errors.ImageNotFound:
            msg = f"Docker image '{image}' not found. Build it first."
            logger.error(msg)
            return False, msg
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected Docker error while running %s: %s", layer, exc)
            return False, str(exc)
        finally:
            # By name: containers.run can raise after creating the container.
            try:
                self.client.containers.get(name).remove(force=True, v=True)
            except Exception:  # pylint: disable=broad-except
                pass
