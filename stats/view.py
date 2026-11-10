"""
``nesti /stats``: the recorded usage events as one self-contained page
(plotly.js embedded, no CDN), rendered live by ``stats.server`` on every
request and priced at OpenRouter's public per-token rates.
"""

import functools
import json
import logging
import os
import socket
import time
import webbrowser
from pathlib import Path

import stats

logger = logging.getLogger(__name__)

_TEMPLATE = Path(__file__).with_name("page.html")
PORT = 8790
URL = f"http://127.0.0.1:{PORT}/"
# nesti-stats on the compose network (from the orchestrator), localhost for a direct host run
_SERVER_HOSTS = ("nesti-stats", "127.0.0.1")
PRICE_TTL = 3600  # seconds the OpenRouter catalog is reused before it is fetched again

_catalog_cache: tuple[float, dict[str, list[float]]] | None = None


def _key(model: str) -> str:
    """Vendor prefix dropped, dots as dashes: anthropic/claude-sonnet-4.6 == claude-sonnet-4-6."""
    return model.lower().rsplit("/", 1)[-1].replace(".", "-")


def _catalog() -> dict[str, list[float]]:
    """``_key`` → price row from OpenRouter's catalog, cached for PRICE_TTL; {} (not cached) when unreachable."""
    global _catalog_cache
    if _catalog_cache and time.time() - _catalog_cache[0] < PRICE_TTL:
        return _catalog_cache[1]
    from scripts.oauth import list_provider_models
    try:
        catalog = list_provider_models("openrouter")
    except Exception as exc:
        logger.warning("Price catalog unavailable (%s); every request is shown unpriced.", exc)
        return {}
    table: dict[str, list[float]] = {}
    for entry in catalog:
        if ":" in entry["id"]:  # ":free"/":thinking" route variants would shadow the base price
            continue
        rates = entry.get("pricing") or {}
        try:
            prompt, completion = float(rates["prompt"]), float(rates["completion"])
            row = [prompt, float(rates.get("input_cache_read") or prompt),
                   float(rates.get("input_cache_write") or prompt), completion]
        except (KeyError, TypeError, ValueError):
            continue
        if min(row) >= 0:  # negative marks a variable-priced route
            table.setdefault(_key(entry["id"]), row)
    _catalog_cache = (time.time(), table)
    return table


def prices(models: set[str]) -> dict[str, list[float]]:
    """USD per token ``[input, cache read, cache write, output]`` for every priceable model in *models*.

    Read from OpenRouter's public catalog; a missing cache rate falls back to the
    input rate. Unknown models are omitted (shown unpriced); {} when the catalog is unreachable.
    """
    table = _catalog()
    return {model: table[_key(model)] for model in models if _key(model) in table}


@functools.cache
def _shell() -> str:
    import plotly.offline

    return _TEMPLATE.read_text(encoding="utf-8").replace("/*PLOTLY*/", plotly.offline.get_plotlyjs())


def render() -> str:
    """The stats page with every event recorded right now (``generated`` = now)."""
    # only the long-lived nesti-stats server renders: retry a Redis outage per page instead of degrading for its lifetime
    if stats._redis is False:
        stats._redis = None
    events = stats.load()
    data = {"events": events, "generated": time.time(),
            "prices": prices({e["model"] for e in events if e.get("kind") == "llm"})}
    # "<" escaped: an issue title or provider error can never close the <script>
    return _shell().replace("/*DATA*/", json.dumps(data).replace("<", "\\u003c"))


def _server_up() -> bool:
    for host in _SERVER_HOSTS:
        try:
            with socket.create_connection((host, PORT), timeout=2):
                return True
        except OSError:
            continue
    return False


def cli_stats(args: list[str]) -> int:
    """``nesti /stats``: print the live stats page address; 1 when the stats server is not running."""
    if args:
        print("Usage: nesti /stats")
        return 2
    events = stats.load()
    llm = sum(e.get("kind") == "llm" for e in events)
    print(f"Recorded: {llm} LLM requests, {len(events) - llm} tool runs.")
    if not _server_up():
        print(f"Stats server unreachable on port {PORT} — start it with: docker-compose up -d nesti-stats")
        return 1
    print(f"Stats page: {URL}")
    if not os.path.exists("/.dockerenv"):
        webbrowser.open_new(URL)
    return 0
