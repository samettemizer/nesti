"""
main.py – entry point for the AI Developer orchestrator.

Usage:
    python main.py            # process one issue and exit
    python main.py --loop     # keep polling until interrupted

When memory is enabled, refresh the skill index before importing the engine;
an indexing failure exits without polling GitLab. Then resolve the project
layout (NESTI_PROJECT_PATH) and, while ``<project>/.omp`` is missing, run
Laravel Boost discovery once (`nesti /boost` refreshes it later).
"""

import argparse
import logging
import os
import re
import sys
import time

from dotenv import load_dotenv

# Load .env before importing anything that reads environment variables
load_dotenv()

import requests  # noqa: E402

logger = logging.getLogger(__name__)
_QDRANT_STARTUP_TIMEOUT = 60


class _RedactingFormatter(logging.Formatter):
    """Keep HTTP/Git diagnostics without exposing URL credentials, including tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        text = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[REDACTED]@", text)
        return re.sub(r"/bot\d+:[^/\s\"']+", "/bot[REDACTED]", text)


def _setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_RedactingFormatter(
        "%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logging.basicConfig(level=level, handlers=[handler])


def _wait_for_qdrant() -> None:
    """Allow a fresh Qdrant service up to one minute to become ready."""
    from vector_store import get_document_memory

    url = f"{get_document_memory().url.rstrip('/')}/readyz"
    api_key = os.environ.get("QDRANT_API_KEY")
    headers = {"api-key": api_key} if api_key else {}
    deadline = time.monotonic() + _QDRANT_STARTUP_TIMEOUT
    logger.info("Waiting for Qdrant readiness before indexing skills.")
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            if requests.get(url, headers=headers, timeout=min(5, remaining)).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    raise RuntimeError(f"Qdrant was not ready within {_QDRANT_STARTUP_TIMEOUT} seconds.")


def _prepare_project(loop: bool, poll_interval: int) -> None:
    """Resolve the project layout, then run Boost once while ``<project>/.omp`` is missing."""
    from project_layout import ensure_layout, project_root

    while True:
        try:
            root = project_root()
            record = ensure_layout(root)
            break
        except Exception as exc:
            logger.exception("Project layout unavailable; GitLab polling disabled: %s", exc)
            if not loop:
                sys.exit(1)
            time.sleep(poll_interval)

    if (root / ".omp").exists():
        logger.info(".omp present at %s; startup Boost skipped (run `nesti /boost` to refresh).", root)
    elif record["mode"] == "greenfield":
        logger.info("Greenfield project: .omp is created after the first scaffold is merged and pulled.")
    else:
        from telegram_notifier import notify as telegram_notify

        try:
            from llm_client import LLMClient
            from project_boost import run_boost

            run_boost(root, record, LLMClient())
        except Exception as exc:
            logger.exception("Startup Boost failed; polling continues without .omp: %s", exc)
            telegram_notify(f"⚠️ Nesti startup Boost failed: {exc}")


def main() -> None:
    """Refresh enabled memory, then process issues once or in a polling loop."""
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="AI Developer – autonomous PHP developer powered by Claude Sonnet."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep polling GitLab Issues for new work instead of exiting after one.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.environ.get("POLL_INTERVAL_SECONDS", "60")),
        metavar="SECONDS",
        help="Seconds to wait between polls when --loop is active (default: 60).",
    )
    args = parser.parse_args()

    from embedding import get_embedder

    if get_embedder().enabled:
        try:
            _wait_for_qdrant()
            from scripts.index_skills import main as index_skills

            if index_skills([]) != 0:
                raise RuntimeError("Skill indexing failed; refusing to poll GitLab.")
        except Exception as exc:
            logger.exception("Startup indexing failed: %s", exc)
            sys.exit(1)
    else:
        logger.info("Vector memory disabled; skipping skill indexing.")

    _prepare_project(args.loop, args.poll_interval)

    from task_engine import TaskEngine

    engine = TaskEngine()

    if args.loop:
        logger.info("AI Developer started in loop mode (poll interval: %ds).", args.poll_interval)
        while True:
            try:
                engine.run_once()
            except KeyboardInterrupt:
                logger.info("Interrupted by user. Shutting down.")
                break
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Unhandled error in loop: %s", exc)
            logger.info("Waiting %d seconds before next poll …", args.poll_interval)
            time.sleep(args.poll_interval)
    else:
        logger.info("AI Developer started in single-run mode.")
        result = engine.run_once()
        sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
