"""Fetch and vendor the PrimeVue + Laravel skill corpus into ``skills/``.

Produces (paths relative to the output directory, default ``skills/``)::

    primevue/<slug>.md         one markdown file per PrimeVue component
    primevue/pages/<slug>.md    the ``installation`` and ``vite`` guide pages
    laravel/<topic>.md          one markdown file per Laravel documentation topic
    registry.json               machine-readable index consumed by ``skill_catalog.py``

The corpus is tracked in git (never ``.gitignore``d). Run once and commit::

    python scripts/fetch_skills.py [--out skills] [--laravel-branch 13.x] [--only primevue|laravel]

Only the standard library and ``requests`` are used — no new dependency.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ── Polite fetching ──────────────────────────────────────────────────────────
_USER_AGENT = "nesti-skill-fetcher/1.0"
HEADERS = {"User-Agent": _USER_AGENT}
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.05
_RETRY_BACKOFF = 0.5
_MIN_SLUGS = 85
_MIN_COMPONENT_BYTES = 200
_FALLBACK_LARAVEL_BRANCH = "12.x"

# ── PrimeVue ─────────────────────────────────────────────────────────────────
_PRIMEVUE_VERSION = "5.0.1"
PRIMEVUE_INDEX_URL = "https://primevue.dev/components/"
PRIMEVUE_COMPONENT_PATTERN = "https://primevue.dev/llms/components/{slug}.md"
PRIMEVUE_PAGE_PATTERN = "https://primevue.dev/llms/pages/{slug}.md"
PRIMEVUE_PAGES = ["installation", "vite"]
# Documented but absent from the components index — appended after discovery.
_EXTRA_SLUGS = ["chart"]

# PrimeVue 3/4 names developers still type in issues -> current v5 slug.
# Empty lists are dropped, so they contribute nothing.
EXTRA_ALIASES = {
    "organizationchart": ["orgchart", "org chart"],
    "select": ["dropdown"],
    "drawer": ["sidebar panel"],
    "toast": ["notification"],
    "datepicker": ["calendar"],
    "inputpassword": ["password field"],
    "toggleswitch": [],
}

# ── Laravel ──────────────────────────────────────────────────────────────────
LARAVEL_SOURCE_PATTERN = "https://raw.githubusercontent.com/laravel/docs/{branch}/{topic}.md"
# Ordered ``(topic, triggers)``. The triggers are the entire selection mechanism
# for backend docs in ``skill_catalog.py`` and must stay exactly as written.
LARAVEL_TOPICS = [
    ("migrations", ["migration", "migrate", "schema", "column", "new table", "index", "foreign key"]),
    ("seeding", ["seed", "seeder", "sample data", "demo data"]),
    ("eloquent-factories", ["factory", "faker", "fake data", "test data"]),
    ("eloquent", ["model", "eloquent", "soft delete", "casts", "query scope"]),
    ("eloquent-relationships", ["relationship", "hasmany", "belongsto", "belongstomany", "hasone", "pivot"]),
    ("eloquent-resources", ["api resource", "jsonresource", "resource collection", "transform response"]),
    ("eloquent-mutators", ["accessor", "mutator", "attribute cast", "appends"]),
    ("validation", ["validate", "validation", "rules", "formrequest", "form request"]),
    ("controllers", ["controller", "crud", "resource controller"]),
    ("routing", ["route", "endpoint", "api route", "route model binding"]),
    ("requests", ["request input", "query parameter", "uploaded file"]),
    ("responses", ["response", "json response", "status code", "redirect"]),
    ("middleware", ["middleware", "throttle", "rate limit"]),
    ("authentication", ["login", "authenticate", "auth guard", "session auth"]),
    ("authorization", ["policy", "gate", "permission", "authorize", "role"]),
    ("sanctum", ["sanctum", "api token", "bearer token", "spa authentication"]),
    ("testing", ["phpunit", "pest", "test suite", "assertion"]),
    ("database-testing", ["refreshdatabase", "database test", "assertdatabasehas"]),
    ("http-tests", ["getjson", "postjson", "feature test", "http test"]),
    ("artisan", ["artisan", "console command", "scheduler"]),
    ("vite", ["vite", "asset bundle", "compile assets"]),
    ("structure", ["directory structure", "where to put"]),
    ("blade", ["blade", "view template", "layout"]),
    ("database", ["sqlite", "mysql", "transaction", "connection"]),
]


def camel_split(name: str) -> str:
    """Insert spaces at lowercase->uppercase boundaries (``DataTable`` -> ``Data Table``)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)


def _fetch(session: requests.Session, url: str) -> requests.Response:
    """GET ``url`` with the polite UA and a 30s timeout, retrying once on a transient network error."""
    for attempt in range(2):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            time.sleep(REQUEST_DELAY)
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            if attempt == 0:
                logger.warning(
                    "network error for %s, retrying once after %.2fs: %s", url, _RETRY_BACKOFF, exc
                )
                time.sleep(_RETRY_BACKOFF)
                continue
            raise


def _first_heading(text: str) -> str:
    """Return the first ``# `` heading without its marker, or ``''`` when absent."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _dedupe(values: list[str]) -> list[str]:
    """Order-preserving dedupe that also drops blank entries."""
    seen: list[str] = []
    for value in values:
        value = value.strip()
        if value and value not in seen:
            seen.append(value)
    return seen


def _component_name(slug: str, title: str) -> str:
    """Display name: the doc title when it normalises to the slug, else the slug capitalised.

    The invariant ``name.lower().replace(' ', '') == slug`` always holds so alias
    derivation stays anchored to the slug.
    """
    if title and title.lower().replace(" ", "") == slug:
        return title
    return slug.capitalize()


def _component_aliases(slug: str, name: str) -> list[str]:
    """``[slug, name.lower(), camel_split(name).lower()]`` plus the fixed extra-alias map."""
    candidates = [slug, name.lower(), camel_split(name).lower()]
    candidates += EXTRA_ALIASES.get(slug, [])
    return _dedupe(candidates)


def discover_slugs(session: requests.Session) -> list[str]:
    """Scrape component slugs from the PrimeVue components index, sorted, with ``chart`` appended."""
    response = _fetch(session, PRIMEVUE_INDEX_URL)
    if response.status_code != 200:
        logger.error("components index returned HTTP %s", response.status_code)
        sys.exit(1)
    slugs = sorted(set(re.findall(r'href="/([a-z0-9-]+)/"', response.text)))
    logger.info("discovered %d component slugs from the index", len(slugs))
    if len(slugs) < _MIN_SLUGS:
        logger.error(
            "only %d slugs discovered (< %d) — the page shape changed; refusing to vendor a truncated corpus",
            len(slugs), _MIN_SLUGS,
        )
        sys.exit(1)
    for extra in _EXTRA_SLUGS:
        if extra not in slugs:
            slugs.append(extra)
    return slugs


def fetch_components(
    session: requests.Session, out_dir: Path, slugs: list[str]
) -> tuple[list[dict], list[dict]]:
    """Fetch each component doc; return ``(components, skipped)`` registry rows."""
    components: list[dict] = []
    skipped: list[dict] = []
    (out_dir / "primevue").mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        response = _fetch(session, PRIMEVUE_COMPONENT_PATTERN.format(slug=slug))
        size = len(response.content)
        if response.status_code != 200 or size < _MIN_COMPONENT_BYTES:
            logger.info("skip component %s (HTTP %s, %d bytes)", slug, response.status_code, size)
            skipped.append({"slug": slug, "status": response.status_code, "bytes": size})
            continue
        rel = f"primevue/{slug}.md"
        (out_dir / rel).write_bytes(response.content)
        name = _component_name(slug, _first_heading(response.text))
        components.append(
            {
                "name": name,
                "slug": slug,
                "aliases": _component_aliases(slug, name),
                "path": rel,
                "chars": size,
            }
        )
        logger.info("component %-22s -> %s (%d bytes)", slug, rel, size)
    return components, skipped


def fetch_pages(session: requests.Session, out_dir: Path) -> tuple[list[dict], list[str]]:
    """Fetch the ``installation`` and ``vite`` guide pages; return ``(pages, failures)``."""
    pages: list[dict] = []
    failures: list[str] = []
    (out_dir / "primevue" / "pages").mkdir(parents=True, exist_ok=True)
    for slug in PRIMEVUE_PAGES:
        response = _fetch(session, PRIMEVUE_PAGE_PATTERN.format(slug=slug))
        if response.status_code != 200:
            logger.error("guide page %s returned HTTP %s", slug, response.status_code)
            failures.append(f"primevue page {slug} (HTTP {response.status_code})")
            continue
        rel = f"primevue/pages/{slug}.md"
        (out_dir / rel).write_bytes(response.content)
        pages.append({"slug": slug, "path": rel, "chars": len(response.content)})
        logger.info("page %-22s -> %s (%d bytes)", slug, rel, len(response.content))
    return pages, failures


def fetch_laravel(
    session: requests.Session, out_dir: Path, branch: str
) -> tuple[list[dict], list[str]]:
    """Fetch each Laravel topic on ``branch`` (falling back to 12.x on 404); return ``(topics, failures)``."""
    topics: list[dict] = []
    failures: list[str] = []
    (out_dir / "laravel").mkdir(parents=True, exist_ok=True)
    for topic, triggers in LARAVEL_TOPICS:
        response = _fetch(session, LARAVEL_SOURCE_PATTERN.format(branch=branch, topic=topic))
        used = branch
        if response.status_code == 404 and branch != _FALLBACK_LARAVEL_BRANCH:
            logger.info("laravel %s missing on %s, retrying on %s", topic, branch, _FALLBACK_LARAVEL_BRANCH)
            response = _fetch(
                session, LARAVEL_SOURCE_PATTERN.format(branch=_FALLBACK_LARAVEL_BRANCH, topic=topic)
            )
            used = _FALLBACK_LARAVEL_BRANCH
        if response.status_code != 200:
            logger.error("laravel topic %s missing on both branches (HTTP %s)", topic, response.status_code)
            failures.append(f"laravel topic {topic} (HTTP {response.status_code} on both branches)")
            continue
        rel = f"laravel/{topic}.md"
        (out_dir / rel).write_bytes(response.content)
        title = _first_heading(response.text) or topic.replace("-", " ").title()
        topics.append(
            {
                "topic": topic,
                "title": title,
                "triggers": list(triggers),
                "path": rel,
                "chars": len(response.content),
                "branch": used,
            }
        )
        logger.info("laravel %-24s -> %s (%s, %d bytes)", topic, rel, used, len(response.content))
    return topics, failures


def _load_existing(out_dir: Path) -> dict:
    """Return the current ``registry.json`` (used to preserve the untouched half on ``--only`` runs)."""
    registry_path = out_dir / "registry.json"
    if registry_path.exists():
        try:
            return json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("could not read existing %s: %s", registry_path, exc)
    return {}


def _print_summary(primevue_section: dict, laravel_section: dict, skipped: list[dict]) -> None:
    """Print the ``kind`` / ``count`` / ``total KB`` table plus any skipped slugs."""
    components = primevue_section.get("components", [])
    pages = primevue_section.get("pages", [])
    topics = laravel_section.get("topics", [])
    rows = [
        ("primevue components", len(components), sum(c["chars"] for c in components)),
        ("primevue pages", len(pages), sum(p["chars"] for p in pages)),
        ("laravel topics", len(topics), sum(t["chars"] for t in topics)),
    ]
    width = max(len(row[0]) for row in rows + [("kind", 0, 0), ("total", 0, 0)])
    total_count = sum(row[1] for row in rows)
    total_bytes = sum(row[2] for row in rows)
    print()
    print(f"{'kind':<{width}}  {'count':>5}  {'total KB':>9}")
    print(f"{'-' * width}  {'-' * 5}  {'-' * 9}")
    for kind, count, byts in rows:
        print(f"{kind:<{width}}  {count:>5}  {round(byts / 1024, 1):>9}")
    print(f"{'-' * width}  {'-' * 5}  {'-' * 9}")
    print(f"{'total':<{width}}  {total_count:>5}  {round(total_bytes / 1024, 1):>9}")
    print()
    if skipped:
        rendered = ", ".join(f"{s['slug']} (HTTP {s['status']}, {s['bytes']}B)" for s in skipped)
        print(f"skipped {len(skipped)} discovered slug(s): {rendered}")
    else:
        print("skipped 0 discovered slugs")


def main(argv: list[str] | None = None) -> int:
    """Fetch the corpus, write ``registry.json``, print the summary, return the exit code."""
    parser = argparse.ArgumentParser(description="Vendor the PrimeVue + Laravel skill corpus into skills/.")
    parser.add_argument("--out", default="skills", help="output directory (default: skills)")
    parser.add_argument("--laravel-branch", default="13.x", help="Laravel docs branch (default: 13.x)")
    parser.add_argument("--only", choices=["primevue", "laravel"], help="fetch only one corpus")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = _load_existing(out_dir)
    session = requests.Session()

    failures: list[str] = []
    skipped: list[dict] = []

    if args.only in (None, "primevue"):
        slugs = discover_slugs(session)
        components, skipped = fetch_components(session, out_dir, slugs)
        pages, page_failures = fetch_pages(session, out_dir)
        failures += page_failures
        primevue_section = {
            "version": _PRIMEVUE_VERSION,
            "source_pattern": PRIMEVUE_COMPONENT_PATTERN,
            "components": components,
            "pages": pages,
        }
    else:
        primevue_section = existing.get(
            "primevue",
            {
                "version": _PRIMEVUE_VERSION,
                "source_pattern": PRIMEVUE_COMPONENT_PATTERN,
                "components": [],
                "pages": [],
            },
        )

    if args.only in (None, "laravel"):
        topics, laravel_failures = fetch_laravel(session, out_dir, args.laravel_branch)
        failures += laravel_failures
        laravel_section = {
            "branch": args.laravel_branch,
            "source_pattern": LARAVEL_SOURCE_PATTERN,
            "topics": topics,
        }
    else:
        laravel_section = existing.get(
            "laravel",
            {
                "branch": args.laravel_branch,
                "source_pattern": LARAVEL_SOURCE_PATTERN,
                "topics": [],
            },
        )

    registry = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primevue": primevue_section,
        "laravel": laravel_section,
    }
    registry_path = out_dir / "registry.json"
    registry_path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s", registry_path)

    _print_summary(primevue_section, laravel_section, skipped)

    if failures:
        logger.error("%d fetch failure(s):", len(failures))
        for item in failures:
            logger.error("  - %s", item)
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
