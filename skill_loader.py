"""
skill_loader.py – fetches skill documentation referenced by URL in Redmine issues.

Workflow:
  1. Extract all HTTP/HTTPS URLs from the issue subject and description.
  2. Fetch each URL (cap: MAX_CHARS_PER_SKILL characters per file).
  3. Return a list of Skill objects; report individual fetch failures to Telegram
     without stopping the orchestrator.

format_skills_for_prompt() allocates budget sequentially (first URL = highest
priority) and produces ready-to-inject blocks for the prompt builder.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests

from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)

MAX_CHARS_PER_SKILL: int = 12_000
MAX_CHARS_TOTAL: int = 15_000
_REQUEST_TIMEOUT: int = 15  # seconds
_URL_RE = re.compile(r"https?://[^\s\)\]\"\'>]+")
_ACCEPTED_CONTENT_TYPES = ("text/", "application/json", "application/xml")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Skill:
    url: str
    content: str
    title: str = ""
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.error is None and bool(self.content and self.content.strip())


# ── URL extraction ─────────────────────────────────────────────────────────────

def extract_urls(text: str) -> list[str]:
    """
    Return deduplicated HTTP/HTTPS URLs found in *text*, stripped of trailing
    punctuation.  Public so it can be unit-tested independently.
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in _URL_RE.findall(text):
        url = raw.rstrip(".,;:!?)")
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


# ── Title inference ────────────────────────────────────────────────────────────

def _infer_title(url: str, content: str) -> str:
    """Try to extract a title from the first Markdown h1 heading; fall back to URL path."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    segment = url.rstrip("/").split("/")[-1]
    return segment.replace(".md", "").replace("-", " ").replace("_", " ").title()


# ── Fetching ───────────────────────────────────────────────────────────────────

def _fetch_skill(url: str) -> tuple[Optional[Skill], Optional[str]]:
    """
    Fetch *url* and return (Skill, None) on success or (None, error_msg) on failure.

    Checks Content-Type to avoid treating binary or HTML responses as skill text.
    Content is capped at MAX_CHARS_PER_SKILL characters.
    """
    try:
        resp = requests.get(
            url,
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": "AI-Developer-Orchestrator/1.0"},
            allow_redirects=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if content_type and not any(ct in content_type for ct in _ACCEPTED_CONTENT_TYPES):
            return None, f"Unsupported Content-Type: {content_type!r}"

        content = resp.text[:MAX_CHARS_PER_SKILL]
        if len(resp.text) > MAX_CHARS_PER_SKILL:
            content += f"\n\n[… content truncated at {MAX_CHARS_PER_SKILL} chars …]"

        title = _infer_title(url, content)
        return Skill(url=url, content=content, title=title), None

    except Exception as exc:  # pylint: disable=broad-except
        return None, str(exc)


# ── Public API ─────────────────────────────────────────────────────────────────

def load_skills(issue: dict) -> list[Skill]:
    """
    Extract URLs from the issue subject AND description, fetch each one, and
    return successfully loaded Skill objects.

    Failed fetches are logged and reported to Telegram but do not raise;
    the caller always receives a (possibly empty) list.
    """
    subject = issue.get("subject", "") or ""
    description = issue.get("description", "") or ""
    urls = extract_urls(f"{subject}\n{description}")

    if not urls:
        logger.info("No skill URLs found in issue #%s.", issue.get("id", "?"))
        return []

    issue_id = issue.get("id", "?")
    logger.info(
        "Found %d skill URL(s) in issue #%s: %s",
        len(urls),
        issue_id,
        urls,
    )

    skills: list[Skill] = []
    for url in urls:
        skill, err = _fetch_skill(url)
        if err:
            logger.warning("Failed to fetch skill URL %s: %s", url, err)
            telegram_notify(
                f"⚠️ Skill fetch failed for issue <b>#{issue_id}</b>\n"
                f"URL: <code>{url}</code>\n"
                f"Error: <code>{err}</code>"
            )
            continue

        if skill and skill.is_valid:
            skills.append(skill)
            logger.info(
                "Loaded skill '%s' from %s (%d chars).",
                skill.title,
                url,
                len(skill.content),
            )
        else:
            logger.warning("Skill URL returned empty content: %s", url)

    return skills


def format_skills_for_prompt(skills: list[Skill], char_budget: int = MAX_CHARS_TOTAL) -> str:
    """
    Format loaded skills into a prompt-injectable string within *char_budget* characters.

    Skills are included in order (first URL = highest priority).
    Once the budget is exhausted remaining skills are skipped with a warning.
    Each block carries the source URL so the LLM knows where the information came from.
    """
    if not skills:
        return ""

    blocks: list[str] = []
    remaining = char_budget

    for skill in skills:
        header = f"### Skill: {skill.title or skill.url}\nSource: {skill.url}\n\n"
        separator = "\n\n---\n"
        overhead = len(header) + len(separator)

        if remaining <= overhead:
            logger.warning(
                "Skill character budget exhausted – skipping %s and any remaining skills.",
                skill.url,
            )
            break

        content = skill.content
        available = remaining - overhead
        if len(content) > available:
            content = content[:available] + "\n[… truncated to fit context budget …]"

        block = f"{header}{content}{separator}"
        blocks.append(block)
        remaining -= len(block)

    return "\n".join(blocks)
