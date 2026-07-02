"""
Docker runner – executes generated code inside an isolated sandbox container.

Responsibilities:
- Write generated files into a temporary workspace directory.
- Mount that workspace into a Docker container.
- Run Composer install and PHPUnit tests inside the container.
- Return stdout/stderr and a boolean success flag.

The AI developer never runs code on the host machine directly.
"""

import logging
import os
import re
from itertools import count
from pathlib import Path

import docker

logger = logging.getLogger(__name__)


class DockerRunner:
    def __init__(self):
        self.image = os.environ.get("DOCKER_SANDBOX_IMAGE", "hello-world-sandbox")
        self.workdir = os.environ.get("DOCKER_SANDBOX_WORKDIR", "/app")
        self.timeout = int(os.environ.get("DOCKER_SANDBOX_TIMEOUT", "120"))
        self.client = docker.from_env()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_tests(self, workspace_path: str) -> tuple[bool, str]:
        """
        Mount *workspace_path* into a container and run PHPUnit.

        Returns
        -------
        (success, output)
            success – True if the test suite exited with code 0.
            output  – Combined stdout + stderr from the container.
        """
        logger.info("Running tests in Docker sandbox (image: %s) …", self.image)
        try:
            result = self.client.containers.run(
                image=self.image,
                command="bash -c 'composer install --no-interaction --prefer-dist && ./vendor/bin/phpunit --testdox'",
                volumes={
                    os.path.abspath(workspace_path): {
                        "bind": self.workdir,
                        "mode": "rw",
                    }
                },
                working_dir=self.workdir,
                remove=True,
                stdout=True,
                stderr=True,
                timeout=self.timeout
            )
            output = result.decode("utf-8", errors="replace")
            logger.info("Tests passed.")
            return True, output
        except docker.errors.ContainerError as exc:
            output = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else str(exc)
            logger.warning("Tests FAILED:\n%s", output)
            return False, output
        except docker.errors.ImageNotFound:
            msg = f"Docker image '{self.image}' not found. Build it first."
            logger.error(msg)
            return False, msg
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected Docker error: %s", exc)
            return False, str(exc)

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
