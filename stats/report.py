"""
stats/report.py – the recorded usage events condensed into one JSON summary
(the ``stats_summary`` MCP tool). Same filters, pricing and error signatures as
the ``nesti /stats`` page; an unpriced cost is ``None``, never a guessed 0.
"""

import logging
import re
import time

import stats
from stats import view

logger = logging.getLogger(__name__)

_SIGNATURE = re.compile(r"[0-9a-f]{8,}|\d+", re.IGNORECASE)
TOP_ERRORS = 10
TOP_RUNS = 20


def _cost(llm: list[dict], table: dict[str, list[float]]) -> float | None:
    """API-equivalent USD of the priced requests; None when none of them is priced."""
    priced = [e for e in llm if e.get("model") in table]
    if not priced:
        return None
    return sum(n * p for e in priced for n, p in zip(e.get("tok") or [0, 0, 0, 0], table[e["model"]]))


def _items(llm: list[dict], key: str, table: dict[str, list[float]], **extra: str) -> list[dict]:
    """requests/failed/tokens/cost per distinct *key*, sorted by requests then tokens, descending."""
    groups: dict[str, list[dict]] = {}
    for e in llm:
        groups.setdefault(e.get(key) or "", []).append(e)
    items = []
    for name, group in groups.items():
        item = {key: name, **{field: group[-1].get(source, "") for field, source in extra.items()},
                "requests": len(group), "failed": sum(not e.get("ok") for e in group),
                "tokens": sum(sum(e.get("tok") or []) for e in group), "cost_usd": _cost(group, table)}
        items.append(item)
    return sorted(items, key=lambda i: (i["requests"], i["tokens"]), reverse=True)


def _summary(since_hours: float, project: str) -> dict:
    now = time.time()
    since = now - since_hours * 3600 if since_hours > 0 else None
    events = [e for e in stats.load()
              if (since is None or e.get("t", 0) >= since) and (not project or e.get("project") == project)]
    llm = [e for e in events if e.get("kind") == "llm"]
    tools = [e for e in events if e.get("kind") == "tool"]
    table = view.prices({e.get("model", "") for e in llm}) if llm else {}

    tok = [sum((e.get("tok") or [0, 0, 0, 0])[i] for e in llm) for i in range(4)]
    ok = [e for e in llm if e.get("ok")]
    cached_input = tok[0] + tok[1] + tok[2]

    tool_groups: dict[tuple, list[dict]] = {}
    for e in tools:
        tool_groups.setdefault((e.get("tool"), e.get("model")), []).append(e)
    tool_items = sorted(({"tool": t, "model": m, "calls": len(g), "errors": sum(not e.get("ok") for e in g)}
                         for (t, m), g in tool_groups.items()), key=lambda i: i["calls"], reverse=True)

    signatures: dict[str, list[dict]] = {}
    for e in llm:
        if not e.get("ok") and e.get("error"):
            signatures.setdefault(_SIGNATURE.sub("#", e["error"])[:300], []).append(e)
    errors = sorted(({"signature": s, "count": len(g), "last_seen": max(e["t"] for e in g),
                      "models": sorted({e.get("model", "") for e in g})} for s, g in signatures.items()),
                    key=lambda i: i["count"], reverse=True)[:TOP_ERRORS]

    run_groups: dict[str, list[dict]] = {}
    for e in events:
        if e.get("run"):
            run_groups.setdefault(e["run"], []).append(e)
    runs = []
    for run, group in run_groups.items():
        run_llm = [e for e in group if e.get("kind") == "llm"]
        start = min(e["t"] for e in group)
        runs.append({"run": run, "issue": group[0].get("issue"), "title": group[0].get("title", ""),
                     "project": group[0].get("project", ""), "started": start,
                     "duration": round(max(e["t"] + (e.get("dur") or 0) for e in group) - start, 3),
                     "llm_requests": len(run_llm), "tool_runs": len(group) - len(run_llm),
                     "tokens": sum(sum(e.get("tok") or []) for e in run_llm), "cost_usd": _cost(run_llm, table)})
    runs.sort(key=lambda r: r["started"], reverse=True)

    return {
        "window": {"since": since, "until": now, "project": project},
        "totals": {
            "requests": len(llm), "failed": len(llm) - len(ok),
            "tokens": dict(zip(("uncached", "cache_read", "cache_write", "output"), tok)),
            "cache_rate": tok[1] / cached_input if cached_input else None,
            "avg_duration": sum(e.get("dur") or 0 for e in ok) / len(ok) if ok else None,
            "issue_runs": len(run_groups), "tool_runs": len(tools),
            "cost_usd": _cost(llm, table) if llm else 0.0,
            "unpriced_requests": sum(e.get("model") not in table for e in llm),
        },
        "models": _items(llm, "model", table),
        "providers": _items(llm, "provider", table, billing="billing"),
        "projects": _items(llm, "project", table),
        "tools": tool_items,
        "errors": errors,
        "runs": runs[:TOP_RUNS],
    }


def summary(since_hours: float = 168, project: str = "") -> dict:
    """Usage summary of the last *since_hours* (<= 0: all) for *project* ("" = all).

    ``{"success": True, "result": {...}}``; without Redis the totals are zero.
    ``{"success": False, "error": str}`` only on a genuine exception.
    """
    try:
        return {"success": True, "result": _summary(since_hours, project)}
    except Exception as exc:
        logger.warning("Usage summary failed: %s", exc)
        return {"success": False, "error": str(exc)}
