"""
main.py – entry point for the AI Developer orchestrator.

Usage:
    python main.py            # process one issue and exit
    python main.py --loop     # keep polling until interrupted
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

# Load .env before importing anything that reads environment variables
load_dotenv()

from task_engine import TaskEngine  # noqa: E402  (after load_dotenv)


def _setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="AI Developer – autonomous PHP developer powered by Claude Sonnet."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep polling Redmine for new issues instead of exiting after one.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.environ.get("POLL_INTERVAL_SECONDS", "60")),
        metavar="SECONDS",
        help="Seconds to wait between polls when --loop is active (default: 60).",
    )
    args = parser.parse_args()

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
