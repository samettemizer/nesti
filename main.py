"""
main.py – entry point for the AI Developer orchestrator.

Usage:
    python main.py            # process one issue and exit
    python main.py --loop     # keep polling until interrupted

When memory is enabled, refresh the skill index before importing the engine;
an indexing failure exits without polling GitLab.
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

# Load .env before importing anything that reads environment variables
load_dotenv()

import requests  # noqa: E402

logger = logging.getLogger(__name__)
_QDRANT_STARTUP_TIMEOUT = 60


def _setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


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
