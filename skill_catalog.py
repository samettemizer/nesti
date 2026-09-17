"""
skill_catalog.py – deterministic, offline skill selection from a vendored corpus.

This module is the offline counterpart to :mod:`skill_loader`. Where
``skill_loader`` fetches documentation from URLs found in the issue text
at runtime, ``skill_catalog`` selects pre-vendored documentation from a local
corpus using only keyword matching — no network access and no LLM call. The
corpus (the ``skills/`` directory and its ``registry.json`` manifest) is
generated ahead of time by ``scripts/fetch_skills.py`` and committed to the repo.

Selection is keyword-driven and fully deterministic:

* PrimeVue components are matched by word-boundary alias search and ranked by the
  earliest match offset in the issue text.
* Laravel topics are matched by counting distinct triggers and ranked by hit
  count (descending).

Both kinds are returned as :class:`skill_loader.Skill` instances so the existing
``skill_loader.format_skills_for_prompt`` helper consumes them unchanged.
"""

import json
import logging
import re
from pathlib import Path

from skill_loader import Skill

logger = logging.getLogger(__name__)

CATALOG_DIR = Path(__file__).parent / "skills"
_REGISTRY_PATH = CATALOG_DIR / "registry.json"
_DOC_CHAR_CAP = 7_000  # per document, before the prompt-level budget
_TRUNCATION_MARKER = "\n\n[\u2026 document truncated by Nesti skill catalog \u2026]"

# Populated lazily by load_registry(); an empty dict means "load attempted and
# failed" and keeps the warning to a single emission per process.
_REGISTRY_CACHE: dict | None = None
# Word-boundary matchers compiled once per alias/trigger and shared across calls.
_ALIAS_RE_CACHE: dict[str, re.Pattern[str]] = {}


def load_registry() -> dict:
    """Load and cache ``skills/registry.json``; return ``{}`` on any error.

    The result is cached in a module global, so a missing or malformed registry
    is logged exactly once per process and later calls are allocation-free.
    """
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    try:
        with open(_REGISTRY_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("registry root is not a JSON object")
        _REGISTRY_CACHE = data
    except Exception as exc:
        logger.warning("Skill catalog registry unavailable (%s): %s", _REGISTRY_PATH, exc)
        _REGISTRY_CACHE = {}
    return _REGISTRY_CACHE


def catalog_status() -> dict:
    """Report corpus availability and coarse counts for diagnostics/health checks."""
    registry = load_registry()
    primevue = registry.get("primevue") if isinstance(registry, dict) else None
    laravel = registry.get("laravel") if isinstance(registry, dict) else None
    primevue = primevue if isinstance(primevue, dict) else {}
    laravel = laravel if isinstance(laravel, dict) else {}
    components = primevue.get("components")
    topics = laravel.get("topics")
    return {
        "available": bool(registry),
        "components": len(components) if isinstance(components, list) else 0,
        "topics": len(topics) if isinstance(topics, list) else 0,
        "primevue_version": str(primevue.get("version", "")),
        "laravel_branch": str(laravel.get("branch", "")),
    }


def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Return a cached word-boundary matcher for ``alias`` (compiled once)."""
    pattern = _ALIAS_RE_CACHE.get(alias)
    if pattern is None:
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])")
        _ALIAS_RE_CACHE[alias] = pattern
    return pattern


def _earliest_alias_offset(aliases: object, haystack: str) -> int | None:
    """Smallest start offset among matching aliases, or ``None`` if none match."""
    if not isinstance(aliases, list):
        return None
    best: int | None = None
    for alias in aliases:
        if not alias or not isinstance(alias, str):
            continue
        match = _alias_pattern(alias).search(haystack)
        if match is not None and (best is None or match.start() < best):
            best = match.start()
    return best


def _distinct_trigger_hits(triggers: object, haystack: str) -> int:
    """Count distinct triggers that match ``haystack``."""
    if not isinstance(triggers, list):
        return 0
    matched: set[str] = set()
    for trigger in triggers:
        if not trigger or not isinstance(trigger, str) or trigger in matched:
            continue
        if _alias_pattern(trigger).search(haystack) is not None:
            matched.add(trigger)
    return len(matched)


def _build_url(pattern: str, **kwargs: str) -> str:
    """Format ``pattern`` with ``kwargs``; fall back to the raw pattern on error.

    A registry ``source_pattern`` change can never raise out of selection.
    """
    if not pattern:
        return ""
    try:
        return pattern.format(**kwargs)
    except Exception:
        return pattern


def _load_document(path: object) -> str | None:
    """Read a corpus document and trim it to the per-document cap.

    Cuts at the last ``"\\n## "`` heading boundary strictly before the cap so a
    fenced code block is never split; hard-cuts when no boundary exists. Returns
    ``None`` when the file path is missing or unreadable.
    """
    if not path or not isinstance(path, str):
        return None
    file_path = CATALOG_DIR / path
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Skill catalog document unreadable (%s): %s", file_path, exc)
        return None
    if len(content) <= _DOC_CHAR_CAP:
        return content
    boundary = content.rfind("\n## ", 0, _DOC_CHAR_CAP)
    trimmed = content[:boundary] if boundary != -1 else content[:_DOC_CHAR_CAP]
    return trimmed + _TRUNCATION_MARKER


def select_skills(
    text: str,
    max_component_docs: int = 3,
    max_topic_docs: int = 2,
) -> list[Skill]:
    """Select vendored skill docs relevant to ``text`` (deterministic, offline).

    Component docs (PrimeVue) come first, ranked by earliest alias match offset;
    topic docs (Laravel) follow, ranked by distinct-trigger hit count. Never
    raises: an empty text, an unavailable registry, or a missing document logs a
    warning where appropriate and yields fewer skills (possibly ``[]``).
    """
    try:
        if not text or not text.strip():
            return []
        registry = load_registry()
        if not registry:
            return []
        haystack = text.lower()

        primevue = registry.get("primevue")
        laravel = registry.get("laravel")
        primevue = primevue if isinstance(primevue, dict) else {}
        laravel = laravel if isinstance(laravel, dict) else {}

        component_pattern = primevue.get("source_pattern", "")
        topic_pattern = laravel.get("source_pattern", "")
        components = primevue.get("components") or []
        topics = laravel.get("topics") or []

        # ── Components: earliest alias offset ascending, then registry order ──
        component_hits: list[tuple[int, int, dict]] = []
        for order, component in enumerate(components):
            if not isinstance(component, dict):
                continue
            offset = _earliest_alias_offset(component.get("aliases"), haystack)
            if offset is not None:
                component_hits.append((offset, order, component))
        component_hits.sort(key=lambda hit: (hit[0], hit[1]))

        # ── Topics: distinct-trigger count descending, then registry order ──
        topic_hits: list[tuple[int, int, dict]] = []
        for order, topic in enumerate(topics):
            if not isinstance(topic, dict):
                continue
            hits = _distinct_trigger_hits(topic.get("triggers"), haystack)
            if hits >= 1:
                topic_hits.append((hits, order, topic))
        topic_hits.sort(key=lambda hit: (-hit[0], hit[1]))

        skills: list[Skill] = []
        for _, _, component in component_hits[:max_component_docs]:
            content = _load_document(component.get("path"))
            if content is None:
                continue
            url = _build_url(component_pattern, slug=str(component.get("slug", "")))
            skills.append(Skill(url=url, title=str(component.get("name", "")), content=content))

        for _, _, topic in topic_hits[:max_topic_docs]:
            content = _load_document(topic.get("path"))
            if content is None:
                continue
            url = _build_url(
                topic_pattern,
                branch=str(topic.get("branch", "")),
                topic=str(topic.get("topic", "")),
            )
            skills.append(Skill(url=url, title=str(topic.get("title", "")), content=content))

        return skills
    except Exception as exc:
        logger.warning("select_skills failed: %s", exc)
        return []
