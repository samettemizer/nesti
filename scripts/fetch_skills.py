"""Fetch and vendor the PrimeVue + Laravel skill corpus into ``skills/``.

Produces (paths relative to the output directory, default ``skills/``)::

    primevue/<slug>.md          one markdown file per PrimeVue component
    primevue/pages/<slug>.md    the official PrimeVue guide pages
    laravel/<topic>.md          one markdown file per Laravel documentation topic
    practices/<slug>.md         curated cross-cutting engineering practice docs
    registry.json               machine-readable index consumed by ``skill_catalog.py``

The corpus is tracked in git (never ``.gitignore``d). Run once and commit::

    python scripts/fetch_skills.py [--out skills] [--laravel-branch 13.x]
                                   [--only primevue|laravel|practices]
                                   [--practices-src DIR]

``primevue`` and ``laravel`` come over the network. ``practices`` are flattened
out of a local skill library with ``--practices-src`` and are otherwise
re-scanned from ``skills/practices/``, so every run rewrites the whole registry
without ever dropping a section.

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
# Official guide pages, in fetch order. A slug may contain a ``/``
# (``theming/styled``); the parent directory is created on demand.
PRIMEVUE_PAGES = [
    "installation",
    "vite",
    "configuration",
    "plugin",
    "autoimport",
    "passthrough",
    "theming/styled",
    "theming/unstyled",
    "tailwind",
    "icons",
    "customicons",
    "guides/accessibility",
    "guides/animations",
    "guides/rtl",
    "migration/v5",
]
# Documented but absent from the components index — appended after discovery.
_EXTRA_SLUGS = ["chart"]

# PrimeVue 3/4 names developers still type in issues -> current v5 slug, plus
# every component v5 deprecated (pages/migration/v5.md, "Deprecations") ->
# its replacement. The deprecated docs are deliberately never vendored: the
# components index omits them and the coder must not learn a doomed API.
# Empty lists are dropped, so they contribute nothing.
EXTRA_ALIASES = {
    "organizationchart": ["orgchart", "org chart"],
    "select": ["dropdown", "multiselect", "multi select"],
    "drawer": ["sidebar panel"],
    "toast": ["notification"],
    "datepicker": ["calendar"],
    "inputpassword": ["password field"],
    "toggleswitch": [],
    "gallery": ["galleria"],
    "inputcolor": ["colorpicker", "color picker"],
    "compare": ["imagecompare", "image compare"],
    "scrollarea": ["scrollpanel", "scroll panel"],
    "mask": ["inputmask", "input mask"],
    "menu": ["panelmenu", "panel menu"],
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
    # ── Appended after the original 24 ───────────────────────────────────────
    # The rest of the official Laravel documentation a Nesti issue can
    # plausibly need. Position matters only for ties, and a tie always goes to
    # the older topic above, so appending can never demote a proven selection.
    ("queries", ["query builder", "db::table", "join", "subquery", "where clause", "aggregate"]),
    ("pagination", ["paginate", "pagination", "per page", "page size", "cursor paginator"]),
    ("eloquent-collections", ["eloquent collection", "lazy collection", "collection of models"]),
    ("eloquent-serialization", ["serialization", "toarray", "tojson", "hidden attribute", "visible attribute"]),
    ("collections", ["collection pipeline", "higher order message", "collect helper", "map filter reduce"]),
    ("errors", ["error handling", "exception handler", "custom exception", "report exception", "render exception"]),
    ("filesystem", ["file storage", "storage disk", "store uploaded file", "public disk", "s3"]),
    ("cache", ["cache", "cache store", "remember forever", "cache tag"]),
    ("queues", ["queue", "queued job", "dispatch job", "failed job", "job batch"]),
    ("events", ["event listener", "event dispatch", "model observer", "event subscriber"]),
    ("notifications", ["notification", "notifiable", "mail notification", "database notification"]),
    ("mail", ["mailable", "send email", "markdown mail", "mail template"]),
    ("localization", ["localization", "translation", "locale", "language file", "i18n"]),
    ("session", ["session data", "flash message", "session driver"]),
    ("csrf", ["csrf", "xsrf", "csrf token"]),
    ("passwords", ["password reset", "forgot password", "reset link"]),
    ("verification", ["email verification", "verify email", "mustverifyemail"]),
    ("hashing", ["hashing", "bcrypt", "argon2", "hash password"]),
    ("encryption", ["encryption", "encrypt", "decrypt", "encrypted cast"]),
    ("rate-limiting", ["rate limiter", "ratelimiter", "too many requests", "throttle requests"]),
    ("http-client", ["http client", "external api", "outbound request", "guzzle", "http::fake"]),
    ("scheduling", ["task scheduling", "cron", "scheduled task", "recurring job"]),
    ("container", ["service container", "dependency injection", "bind interface", "singleton"]),
    ("providers", ["service provider", "register binding", "boot method"]),
    ("facades", ["facade", "real-time facade"]),
    ("contracts", ["laravel contract", "contract interface"]),
    ("configuration", ["configuration file", "config value", "environment variable", "app config"]),
    ("views", ["view composer", "render view", "share view data"]),
    ("frontend", ["inertia", "livewire", "single page application", "vue integration"]),
    ("strings", ["string helper", "str::", "slug helper", "pluralize"]),
    ("helpers", ["helper function", "arr::", "data_get", "value helper"]),
    ("mocking", ["mocking", "mock", "spy", "bus::fake", "queue::fake", "event::fake"]),
    ("console-tests", ["console test", "expectsquestion", "artisan test", "command test"]),
    ("urls", ["url generation", "signed url", "named route url", "asset url"]),
    ("broadcasting", ["broadcasting", "websocket", "laravel echo", "real-time update", "pusher"]),
    ("redis", ["redis"]),
    ("logging", ["logging", "log channel", "log::", "monolog"]),
    ("scout", ["laravel scout", "full-text search", "searchable model", "meilisearch", "algolia"]),
    ("socialite", ["socialite", "oauth login", "social login", "google login"]),
    ("images", ["image manipulation", "resize image", "thumbnail", "image upload"]),
    ("precognition", ["precognition", "live validation"]),
    ("ai-sdk", ["laravel ai", "ai sdk", "embedding", "vector store", "reranking", "llm agent"]),
]

# ── Practices ────────────────────────────────────────────────────────────────
# Cross-cutting engineering documents vendored from a local skill library with
# ``--practices-src``. The list is a whitelist on purpose: only skills that
# shape the code Nesti writes are allowed in — PHP/Laravel, Vue/PrimeVue and
# the four test layers. ``files`` are flattened into one document, the first
# one supplying the ``# `` title and every later one becoming a
# ``## Reference:`` section.
PRACTICE_SOURCES = [
    {
        "slug": "tdd",
        "title": "Test-Driven Development",
        "dir": "tdd",
        "files": ["SKILL.md", "tests.md", "mocking.md"],
        "url": "nesti://skills/practices/tdd.md",
        "triggers": [
            "tdd", "test driven", "red green refactor", "test first",
            "regression test", "failing test", "test coverage",
        ],
    },
    {
        "slug": "senior-security",
        "title": "Application Security Engineering",
        "dir": "senior-security",
        "files": [
            "SKILL.md",
            "references/threat-modeling-guide.md",
            "references/security-architecture-patterns.md",
            "references/cryptography-implementation.md",
        ],
        "url": "https://github.com/alirezarezvani/claude-skills/tree/main/engineering-team/senior-security",
        "triggers": [
            "security review", "threat model", "vulnerability", "owasp",
            "sql injection", "xss", "secure coding", "attack surface",
            "mass assignment", "sensitive data",
        ],
    },
    {
        "slug": "frontend-design",
        "title": "Frontend Visual Design",
        "dir": "frontend-design",
        "files": ["SKILL.md"],
        "url": "nesti://skills/practices/frontend-design.md",
        "license": "Apache-2.0 (practices/licenses/frontend-design.txt)",
        "license_file": "LICENSE.txt",
        "triggers": [
            "visual design", "ui design", "typography", "color palette",
            "design system", "look and feel", "redesign", "visual hierarchy",
        ],
    },
    {
        "slug": "minimalist-ui",
        "title": "Minimalist UI Direction",
        "dir": "minimalist-ui",
        "files": ["SKILL.md"],
        "url": "nesti://skills/practices/minimalist-ui.md",
        "triggers": [
            "minimalist", "minimal ui", "clean interface", "editorial design",
            "monochrome", "flat design",
        ],
    },
]
_FRONT_MATTER_FENCE = "---"
_PRACTICE_LICENSE_DIR = "practices/licenses"
_MAX_HEADING_LEVEL = 6


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
    """Fetch every official PrimeVue guide page; return ``(pages, failures)``."""
    pages: list[dict] = []
    failures: list[str] = []
    for slug in PRIMEVUE_PAGES:
        response = _fetch(session, PRIMEVUE_PAGE_PATTERN.format(slug=slug))
        if response.status_code != 200:
            logger.error("guide page %s returned HTTP %s", slug, response.status_code)
            failures.append(f"primevue page {slug} (HTTP {response.status_code})")
            continue
        rel = f"primevue/pages/{slug}.md"
        destination = out_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        title = _first_heading(response.text) or slug.replace("/", " ").replace("-", " ").title()
        pages.append(
            {"slug": slug, "title": title, "path": rel, "chars": len(response.content)}
        )
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


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split a leading ``---`` block into a flat ``key: value`` map plus the body.

    Deliberately not a YAML parser: continuation lines of an upstream block
    scalar (``description: >``) are indented and therefore skipped. Only the
    keys this script writes itself are ever read back.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONT_MATTER_FENCE:
        return {}, text
    for index in range(1, len(lines)):
        if lines[index].strip() != _FRONT_MATTER_FENCE:
            continue
        meta: dict[str, str] = {}
        for line in lines[1:index]:
            key, separator, value = line.partition(":")
            if separator and not key[:1].isspace():
                meta[key.strip()] = value.strip().strip('"')
        return meta, "\n".join(lines[index + 1:]).lstrip("\n")
    return {}, text


def _demote_headings(text: str) -> str:
    """Push every ATX heading one level deeper, leaving fenced code untouched."""
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level < _MAX_HEADING_LEVEL and line[level:level + 1] in (" ", ""):
                line = "#" + line
        out.append(line)
    return "\n".join(out)


def _reference_title(name: str) -> str:
    """``references/rag_evaluation_framework.md`` -> ``Rag Evaluation Framework``."""
    return Path(name).stem.replace("_", " ").replace("-", " ").title()


def _render_practice(entry: dict, src_dir: Path) -> str:
    """Flatten one source skill into a single document with Nesti front matter."""
    root = src_dir / entry["dir"]
    parts: list[str] = []
    for position, name in enumerate(entry["files"]):
        _, body = _split_front_matter((root / name).read_text(encoding="utf-8"))
        body = body.strip()
        if not body:
            continue
        if position == 0:
            parts.append(body if body.startswith("# ") else f"# {entry['title']}\n\n{body}")
            continue
        # The chunker splits on "\n## ", so every appended file has to open one
        # section of its own — its demoted title when it has one, a synthesised
        # "Reference:" heading when it does not.
        demoted = _demote_headings(body)
        if demoted.startswith("## "):
            parts.append(demoted)
        else:
            parts.append(f"## Reference: {_reference_title(name)}\n\n{demoted}")
    front = [
        _FRONT_MATTER_FENCE,
        f"title: {entry['title']}",
        f"slug: {entry['slug']}",
        f"source: {entry['url']}",
        f"triggers: {', '.join(entry['triggers'])}",
    ]
    if entry.get("license"):
        front.append(f"license: {entry['license']}")
    front += ["vendored_by: scripts/fetch_skills.py", _FRONT_MATTER_FENCE, ""]
    return "\n".join(front) + "\n" + "\n\n---\n\n".join(parts) + "\n"


def vendor_practices(src_dir: Path, out_dir: Path) -> list[str]:
    """Write every ``PRACTICE_SOURCES`` entry into ``practices/``; return failures."""
    failures: list[str] = []
    (out_dir / "practices").mkdir(parents=True, exist_ok=True)
    for entry in PRACTICE_SOURCES:
        try:
            document = _render_practice(entry, src_dir)
            rel = f"practices/{entry['slug']}.md"
            (out_dir / rel).write_text(document, encoding="utf-8")
            license_file = entry.get("license_file")
            if license_file:
                target = out_dir / _PRACTICE_LICENSE_DIR / f"{entry['slug']}.txt"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    (src_dir / entry["dir"] / license_file).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
        except OSError as exc:
            logger.error("practice %s could not be vendored: %s", entry["slug"], exc)
            failures.append(f"practice {entry['slug']} ({exc})")
            continue
        logger.info(
            "practice %-22s -> %s (%d bytes)", entry["slug"], rel, len(document.encode("utf-8"))
        )
    return failures


def scan_practices(out_dir: Path) -> list[dict]:
    """Rebuild the practice registry rows from the documents already on disk."""
    documents: list[dict] = []
    for path in sorted((out_dir / "practices").glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("practice %s is unreadable: %s", path.name, exc)
            continue
        meta, _ = _split_front_matter(text)
        slug = meta.get("slug") or path.stem
        triggers = _dedupe([part.lower() for part in meta.get("triggers", "").split(",")])
        if not triggers:
            logger.warning("practice %s has no triggers and can never be selected", slug)
        documents.append(
            {
                "slug": slug,
                "title": meta.get("title") or slug.replace("-", " ").title(),
                "url": meta.get("source", ""),
                "triggers": triggers,
                "path": f"practices/{path.name}",
                "chars": len(text.encode("utf-8")),
            }
        )
    return documents


def _load_existing(out_dir: Path) -> dict:
    """Return the current ``registry.json`` (used to preserve the untouched half on ``--only`` runs)."""
    registry_path = out_dir / "registry.json"
    if registry_path.exists():
        try:
            return json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("could not read existing %s: %s", registry_path, exc)
    return {}


def _print_summary(
    primevue_section: dict,
    laravel_section: dict,
    practices_section: dict,
    skipped: list[dict],
) -> None:
    """Print the ``kind`` / ``count`` / ``total KB`` table plus any skipped slugs."""
    components = primevue_section.get("components", [])
    pages = primevue_section.get("pages", [])
    topics = laravel_section.get("topics", [])
    practices = practices_section.get("documents", [])
    rows = [
        ("primevue components", len(components), sum(c["chars"] for c in components)),
        ("primevue pages", len(pages), sum(p["chars"] for p in pages)),
        ("laravel topics", len(topics), sum(t["chars"] for t in topics)),
        ("practice documents", len(practices), sum(p["chars"] for p in practices)),
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
    parser.add_argument(
        "--only", choices=["primevue", "laravel", "practices"], help="refresh only one corpus"
    )
    parser.add_argument(
        "--practices-src",
        help="local skill library to re-vendor practices/ from (offline; omit to keep the "
             "documents already in skills/practices/)",
    )
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

    if args.practices_src:
        failures += vendor_practices(Path(args.practices_src), out_dir)
    # Always rescanned from disk: the section is local, cheap and must survive
    # every --only run, because the registry is rewritten whole below.
    practices_section = {"documents": scan_practices(out_dir)}

    registry = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primevue": primevue_section,
        "laravel": laravel_section,
        "practices": practices_section,
    }
    registry_path = out_dir / "registry.json"
    registry_path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s", registry_path)

    _print_summary(primevue_section, laravel_section, practices_section, skipped)

    if failures:
        logger.error("%d fetch failure(s):", len(failures))
        for item in failures:
            logger.error("  - %s", item)
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
