"""
stats/server.py – ``nesti-stats``: serves the usage statistics page live.

``GET /`` renders the page from the events recorded at request time, so a
browser refresh always shows current data; every other path is 404.
Run: ``python -m stats.server`` (0.0.0.0:8790, published on 127.0.0.1 only).
"""

import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from stats import view

logger = logging.getLogger(__name__)

HOST = "0.0.0.0"


class StatsHandler(BaseHTTPRequestHandler):
    """``GET /`` → freshly rendered page; anything else → 404; a render failure → 500."""

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if urlsplit(self.path).path != "/":
            self.send_error(404)
            return
        try:
            body = view.render().encode("utf-8")
        except Exception as exc:
            logger.exception("Stats page render failed: %s", exc)
            self.send_error(500)
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError as exc:
            logger.info("Stats client went away: %s", exc)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 (base signature)
        logger.info("%s %s", self.address_string(), format % args)


def main() -> None:
    """Serve the stats page until the process is stopped."""
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s")
    server = ThreadingHTTPServer((HOST, view.PORT), StatsHandler)
    logger.info("Stats page served on %s:%d", HOST, view.PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
