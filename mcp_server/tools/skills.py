"""mcp_server/tools/skills.py – skill documentation tools exposed over MCP.

Unlike ``tool_skill_fetch`` in graph/tools.py (which returns Skill dataclass
instances for in-process consumption by prompt_builder), these tools return
plain JSON-serialisable dicts, as required at the MCP transport boundary.
"""

from mcp_server.server import app
from skill_loader import load_skills, format_skills_for_prompt
from graph.tools import (
    tool_skill_catalog_select,
    tool_skill_catalog_status,
)


@app.tool()
def skill_fetch_from_issue(issue: dict) -> dict:
    """
    Extract all URLs from the issue subject and description, fetch their content,
    and return formatted skill documentation ready for use in a prompt.
    """
    skills = load_skills(issue)
    formatted = format_skills_for_prompt(skills)
    return {
        "success": True,
        "result": {
            "skill_count": len(skills),
            "titles": [s.title for s in skills],
            "formatted": formatted,
        }
    }


@app.tool()
def skill_fetch_url(url: str) -> dict:
    """
    Fetch a single skill documentation URL and return its content.
    Returns title and content (capped at 12 000 chars).
    """
    from skill_loader import _fetch_skill
    skill, err = _fetch_skill(url)
    if err:
        return {"success": False, "error": err}
    return {
        "success": True,
        "result": {"title": skill.title, "content": skill.content}
    }


@app.tool()
def skill_catalog_select(
    text: str, max_component_docs: int = 3, max_topic_docs: int = 2
) -> dict:
    """
    Select vendored PrimeVue / Laravel docs matching text from the offline
    corpus. Picks up to max_component_docs component docs and max_topic_docs
    topic docs by alias/trigger matching.
    Returns count: int, docs: [{title, url, chars}], and formatted: str
    (prompt-ready). Skill dataclasses never cross the transport boundary.
    """
    result = tool_skill_catalog_select(
        text,
        max_component_docs=max_component_docs,
        max_topic_docs=max_topic_docs,
    )
    if not result.get("success"):
        return result
    skills = result["result"]
    return {
        "success": True,
        "result": {
            "count": len(skills),
            "docs": [
                {"title": s.title, "url": s.url, "chars": len(s.content)}
                for s in skills
            ],
            "formatted": format_skills_for_prompt(skills),
        },
    }


@app.tool()
def skill_catalog_status() -> dict:
    """
    Report whether the vendored skill corpus is present and how large it is.
    Returns available: bool, components: int, topics: int, primevue_version:
    str, and laravel_branch: str.
    """
    return tool_skill_catalog_status()
