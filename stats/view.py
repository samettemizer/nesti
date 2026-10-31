"""
``nesti /stats``: renders the recorded usage events as one self-contained
offline page, state/stats.html (plotly.js embedded, no CDN, no server), priced
at OpenRouter's public per-token rates.
"""

import json
import logging
import os
import time
import webbrowser
from pathlib import Path

import project_layout
import stats

logger = logging.getLogger(__name__)

_TEMPLATE = Path(__file__).with_name("page.html")


def _key(model: str) -> str:
    """Vendor prefix dropped, dots as dashes: anthropic/claude-sonnet-4.6 == claude-sonnet-4-6."""
    return model.lower().rsplit("/", 1)[-1].replace(".", "-")


def prices(models: set[str]) -> dict[str, list[float]]:
    """USD per token ``[input, cache read, cache write, output]`` for every priceable model in *models*.

    Read from OpenRouter's public catalog; a missing cache rate falls back to the
    input rate. Unknown models are omitted (shown unpriced); {} when the catalog is unreachable.
    """
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
    return {model: table[_key(model)] for model in models if _key(model) in table}


def cli_stats(args: list[str]) -> int:
    """``nesti /stats``: render state/stats.html from every recorded event."""
    if args:
        print("Usage: nesti /stats")
        return 2
    import plotly.offline

    events = stats.load()
    data = {"events": events, "generated": time.time(),
            "prices": prices({e["model"] for e in events if e.get("kind") == "llm"})}
    page = (_TEMPLATE.read_text(encoding="utf-8")
            .replace("/*PLOTLY*/", plotly.offline.get_plotlyjs())
            # "<" escaped: an issue title or provider error can never close the <script>
            .replace("/*DATA*/", json.dumps(data).replace("<", "\\u003c")))
    out = project_layout.STATE_DIR / "stats.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    project_layout._adopt(out, project_layout.STATE_DIR)
    llm = sum(e.get("kind") == "llm" for e in events)
    print(f"Recorded: {llm} LLM requests, {len(events) - llm} tool runs.")
    print(f"Stats view: {out}")
    if not os.path.exists("/.dockerenv"):
        webbrowser.open_new(out.as_uri())
    return 0
