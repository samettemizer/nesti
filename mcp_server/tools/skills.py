"""mcp_server/tools/skills.py – skill documentation tools exposed over MCP.

Unlike ``tool_skill_fetch`` in graph/tools.py (which returns Skill dataclass
instances for in-process consumption by prompt_builder), these tools return
plain JSON-serialisable dicts, as required at the MCP transport boundary.
"""

from mcp_server.server import app
from skill_loader import load_skills, format_skills_for_prompt


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
