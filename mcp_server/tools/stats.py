"""mcp_server/tools/stats.py – usage statistics tool exposed over MCP.

The same recorded events ``nesti /stats`` renders (stats/report.py), as JSON.
"""

from mcp_server.server import app
from stats.report import summary


@app.tool()
def stats_summary(since_hours: float = 168, project: str = "") -> dict:
    """
    Summarise Nesti's recorded LLM requests and pipeline tool runs over the
    last since_hours (<= 0: everything recorded) for one GitLab project path
    ("" = all projects). result has window, totals (requests, failed, tokens
    {uncached, cache_read, cache_write, output}, cache_rate, avg_duration,
    issue_runs, tool_runs, cost_usd, unpriced_requests), models, providers,
    projects, tools, errors (top 10 signatures) and runs (newest 20).
    cost_usd is the API-equivalent estimate at OpenRouter's public prices and
    is None when nothing could be priced — unknown, never free.
    """
    return summary(since_hours, project)
