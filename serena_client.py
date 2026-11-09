"""
Serena MCP client: the read-only research loop that runs before each plan.

nesti-serena (docker-compose.yml) serves Serena's semantic code index of
NESTI_PROJECT_PATH over streamable HTTP. Before node_plan writes the plan, the
planner may query it for up to _MAX_TURNS turns; Nesti executes only READ_TOOLS
and hands the results to the plan prompt's Code Intelligence section. Each run
first writes layout.json's architecture summary as ARCHITECTURE_MEMORY.
research() never raises: a disabled flag, a project without a backend yet or an
unreachable Serena yields "".
"""

import asyncio
import json
import logging
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import McpError
from mcp.types import TextContent

import project_boost
import project_layout

logger = logging.getLogger(__name__)

SERENA_URL = "http://nesti-serena:9121/mcp"
ARCHITECTURE_MEMORY = "nesti/architecture"
# The only tools Nesti ever calls for the planner; Serena sees the user's checkout,
# so nothing that edits may reach it.
READ_TOOLS = frozenset({
    "find_symbol", "get_symbols_overview", "find_referencing_symbols",
    "search_for_pattern", "list_memories", "read_memory",
})
_MAX_TURNS = 4
_MAX_ACTIONS = 8
_MAX_RESULT_CHARS = 6_000
_MAX_FINDINGS_CHARS = 16_000

_RESEARCH_SYSTEM = """\
You gather facts for the implementation plan of a GitLab issue by querying Serena, a
read-only semantic code index of the project repository. Paths are relative to the
repository root, so they start with the backend or frontend folder named under
Project architecture.

Reply with exactly one JSON object and nothing else:
- {"actions": [{"tool": "<name>", "args": {...}}, ...]} runs up to 8 queries; you get the results back.
- {"done": true} when you know enough, or when the issue needs no existing code.

Tools (arguments are examples):
- find_symbol {"name_path_pattern": "OrderController/index", "relative_path": "app/Http", "substring_matching": true, "include_body": false, "depth": 1}
- get_symbols_overview {"relative_path": "app/Models/Order.php"}
- find_referencing_symbols {"name_path": "Order/items", "relative_path": "app/Models/Order.php"}
- search_for_pattern {"substring_pattern": "Route::apiResource", "relative_path": "routes", "context_lines_after": 2}
- list_memories {}
- read_memory {"memory_name": "nesti/architecture"}

Query only what the plan needs: the symbols the change touches, their callers and the
existing conventions it must follow. Prefer narrow queries; results longer than 6000
characters are cut. You have at most 4 turns."""


def enabled() -> bool:
    """Read NESTI_SERENA_ENABLE (default true)."""
    raw = os.environ.get("NESTI_SERENA_ENABLE", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


async def _call_tools(calls: list[tuple[str, dict]]) -> list[str]:
    async with streamable_http_client(SERENA_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            results = []
            for name, args in calls:
                try:
                    result = await session.call_tool(name, args)
                except McpError as exc:
                    results.append(f"error: {exc}")
                    continue
                text = "\n".join(c.text for c in result.content if isinstance(c, TextContent))
                results.append(f"error: {text}" if result.isError else text)
            return results


def call_tools(calls: list[tuple[str, dict]]) -> list[str]:
    """Run *calls* (tool name, arguments) in one MCP session; each result's text. Raises when Serena is unreachable."""
    return asyncio.run(_call_tools(calls))


def research(llm, issue_text: str) -> str:
    """
    Let *llm* query Serena read-only for up to _MAX_TURNS turns; return the findings text or "".

    Logs exactly one ``SERENA:`` line per call and never raises.
    """
    if not enabled():
        logger.info("SERENA: disabled (NESTI_SERENA_ENABLE)")
        return ""
    record = project_layout.load_layout()
    if not record or not (record.get("layout") or {}).get("backend"):
        logger.info("SERENA: skipped (no backend in layout.json yet)")
        return ""
    architecture = project_boost._strip_frontmatter(project_boost._architecture_rule(record))
    try:
        stored = call_tools([
            ("write_memory", {"memory_name": ARCHITECTURE_MEMORY, "content": architecture}),
        ])[0]
    except Exception as exc:
        logger.warning("SERENA: unavailable (%s)", exc)
        return ""
    if stored.startswith("error: "):
        logger.warning("Serena memory %s not written: %s", ARCHITECTURE_MEMORY, stored)

    history = [{
        "role": "user",
        "content": (
            f"## Issue\n{issue_text.strip()}\n\n## Project architecture\n{architecture}\n\n"
            "Reply with the JSON object now."
        ),
    }]
    findings: list[str] = []
    turns = queries = 0
    stop = "done"
    while turns < _MAX_TURNS:
        turns += 1
        try:
            reply = llm.generate_plan(_RESEARCH_SYSTEM, "", messages=history)
        except Exception as exc:
            stop = f"planner failed: {exc}"
            break
        try:
            actions = project_boost._json_object(reply).get("actions")
        except (ValueError, RecursionError):
            actions = None
        if not isinstance(actions, list) or not actions:
            break
        observations: list[str] = []
        queued: list[tuple[str, dict]] = []
        slots: list[tuple[int, str]] = []
        for action in actions[:_MAX_ACTIONS]:
            tool = action.get("tool") if isinstance(action, dict) else None
            args = action.get("args", {}) if isinstance(action, dict) else None
            header = f"### {tool} {json.dumps(args, ensure_ascii=False)}"
            if isinstance(tool, str) and tool in READ_TOOLS and isinstance(args, dict):
                queued.append((tool, args))
                slots.append((len(observations), header))
                observations.append("")
            else:
                observations.append(f"{header}\nrefused: only {', '.join(sorted(READ_TOOLS))} are available")
        try:
            results = call_tools(queued) if queued else []
        except Exception as exc:
            stop = f"Serena failed: {exc}"
            break
        for (index, header), result in zip(slots, results):
            if len(result) > _MAX_RESULT_CHARS:
                result = result[:_MAX_RESULT_CHARS] + "\n… result truncated; narrow the query"
            observations[index] = f"{header}\n{result}"
            findings.append(observations[index])
        queries += len(queued)
        if len(actions) > _MAX_ACTIONS:
            observations.append(f"Only the first {_MAX_ACTIONS} actions were executed.")
        history += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "\n\n".join(observations)},
        ]
    else:
        stop = "turn limit"

    text = "\n\n".join(findings)
    if len(text) > _MAX_FINDINGS_CHARS:
        text = text[:_MAX_FINDINGS_CHARS] + "\n… findings truncated"
    logger.info(
        "SERENA: %d queries in %d turn(s), %d chars of findings (%s)", queries, turns, len(text), stop,
    )
    return text
