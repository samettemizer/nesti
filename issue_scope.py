"""
issue_scope.py – decides whether a GitLab issue is backend, frontend or fullstack work.

Why a scope exists
──────────────────
Every issue used to receive the same fullstack prompts: turning a green button
orange came with the database policy, the Scramble rules and Laravel topic
docs; a new /api endpoint came with the PrimeVue rules and Vitest/Playwright
instructions.  The scope narrows what the prompts carry — role, rules,
standards, plan structure, reference docs and retrieved chunks — to the side of
the application the issue actually changes.

Two sources, in order
─────────────────────
1. The issue text, classified here deterministically and offline (no LLM call)
   before the planner runs:
     • an explicit statement wins — a ``Scope: frontend`` line, "frontend-only
       change", "no backend changes";
     • otherwise strong signals decide (file paths, framework names, Laravel
       artefacts, UI vocabulary): frontend only → frontend, backend only →
       backend, both → fullstack;
     • without a strong signal, weak ones (API wording, page/form wording)
       decide the same way;
     • no signal at all → fullstack.
   A signal preceded closely by a negation ("do NOT change the database
   schema") is ignored.  Every uncertain case lands on fullstack, the prompt
   Nesti used for every issue before, so a misclassification costs narrowing —
   never a capability.
2. The planner, which also sees the repository inventory, declares the scope
   of the plan it wrote on its first line (``SCOPE: backend``).  That
   declaration is final for the coding phase: the coder implements the plan,
   so its prompt must match the plan.  Without the line, the issue-text scope
   stays.

The scope shapes prompts only.  Which test layers run is decided from the files
the coder actually wrote (graph/tools.py::tool_detect_stack), so a wrong scope
can never skip a layer the change touched.  When a layer outside the scope goes
red, node_on_layer_failure ``widen``s the scope so the retry prompt carries the
standards of the layer that failed.

The same module decides whether the issue asks for documentation work
(``documentation_request``): README.md, CHANGELOG.md and docs/ stay out of a
change unless it does.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SCOPES: tuple[str, ...] = ("backend", "frontend", "fullstack")

# A match whose preceding 40 characters end in a negation clause is ignored:
# "Do NOT change the database schema" names the database to rule it out.
_NEGATION_WINDOW = 40
_NEGATION_RE = re.compile(r"(?:\bno|\bnot|\bwithout|n't|\bnever|\bnor)\b[^.;:\n]{0,24}$")

_SIDE = r"(back[- ]?end|front[- ]?end|full[- ]?stack)"

# Only the first lines of a plan may carry its scope declaration; a "scope"
# mentioned deep inside the plan text is prose, not the declaration.  The
# pattern tolerates the markdown models wrap around it ("**SCOPE:** frontend").
_DECLARATION_LINES = 5
_DECLARED_SCOPE_RE = re.compile(rf"^[\W_]*scope[\W_]*[:=–—-][\W_]*{_SIDE}\b", re.IGNORECASE)

# Explicit statements in the issue.  The flag marks the form that names the
# side which does NOT change ("no backend changes"), so it selects the other.
_EXPLICIT_RES: tuple[tuple[re.Pattern[str], bool], ...] = (
    (re.compile(rf"(?im)^[^\w\n]*scope\s*[:=]\s*[^\w\n]*{_SIDE}\b"), False),
    (re.compile(rf"(?i)\b{_SIDE}[- ]only (?:change|issue|task|work|fix)\b"), False),
    (re.compile(r"(?i)\bno (back[- ]?end|front[- ]?end) (?:changes?|work|code)\b"), True),
)

# Documentation requests.  URLs are removed first: the PrimeVue skill links
# Nesti issues carry end in ".md" and are not a request to edit a Markdown file.
# "API/OpenAPI documentation" is Scramble's job, not a documentation file.
_URL_RE = re.compile(r"https?://\S+")
_DOCS_REQUEST_RE = re.compile(
    r"\breadme\b|\bchange ?log\b|\bcontributing\b|(?<![\w/])docs/"
    r"|\b[\w./-]+\.(?:md|markdown|rst|adoc)\b"
    r"|(?<!api )(?<!openapi )(?<!scramble )(?<!swagger )\b(?:documentation|docs)\b"
    r"|(?:^|[.:;\n-]\s*|\band\s+)document\b(?!s|ed|ation)"
)


def _signals(*pairs: tuple[str, str]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Compile ``(label, pattern)`` pairs; patterns run on lowercased text."""
    return tuple((label, re.compile(pattern)) for label, pattern in pairs)


# Each label is reported once, however often its pattern matches.
_FRONTEND_STRONG = _signals(
    (".vue file", r"\.vue\b"),
    ("resources/js", r"\bresources/(?:js|css)/"),
    ("e2e/", r"(?<![\w/])e2e/"),
    ("PrimeVue", r"\bprimevue\b"),
    ("Vue", r"(?<![.\w-])vue(?:\.js|3)?\b"),
    ("Vitest", r"\bvitest\b"),
    ("Playwright", r"\bplaywright\b"),
    ("Tailwind", r"\btailwind\b"),
    ("CSS", r"\b(?:s?css|sass)\b"),
    ("JavaScript", r"\b(?:javascript|typescript)\b"),
    ("frontend", r"\bfront[- ]?end\b"),
    ("UI", r"\b(?:ui|ux)\b|\buser interface\b"),
    ("component", r"\bcomponents?\b"),
    ("button", r"\bbuttons?\b"),
    ("colour", r"\bcolou?r(?:s|ed)?\b"),
    ("style", r"(?<!code )\b(?:styles?|styling|stylesheets?)\b"),
    ("font", r"\bfonts?\b"),
    ("layout", r"\blayouts?\b"),
    ("responsive", r"\bresponsive\b"),
    ("theme", r"\b(?:themes?|dark mode|light mode)\b"),
    ("icon", r"\bicons?\b"),
    ("UI widget", r"\b(?:modal|dialog|popup|tooltip|toast|navbar|sidebar|dropdown|"
                  r"breadcrumbs?|datatable|data table|tabs)\b"),
    ("click", r"\bclick(?:s|ed|ing)?\b"),
    ("hover", r"\bhover(?:s|ed|ing)?\b"),
    ("display", r"\b(?:display(?:s|ed|ing)?|render(?:s|ed|ing)?)\b"),
    ("screen", r"\b(?:screens?|mobile|viewport)\b"),
    ("Blade", r"\bblade\b"),
    ("browser", r"\bbrowsers?\b"),
)

_BACKEND_STRONG = _signals(
    (".php file", r"(?<!\.blade)\.php\b"),
    ("app/ path", r"(?<![\w/])(?:app|database|config)/"),
    ("PHP static call", r"\b[a-z_]\w*::[a-z_]\w*\("),
    ("migration", r"\bmigrations?\b"),
    ("Eloquent", r"\beloquent\b"),
    ("model", r"(?<!v-)\bmodels?\b"),
    ("factory", r"\bfactor(?:y|ies)\b"),
    ("seeder", r"\bseed(?:er|ers|ing)?\b"),
    ("controller", r"\bcontrollers?\b"),
    ("FormRequest", r"\bform ?requests?\b|\b(?:store|update|create|delete|destroy)\w*request\b"),
    ("API Resource", r"\b(?:api|json) ?resources?\b|\b\w+resource\b"),
    ("middleware", r"\b(?:middleware|polic(?:y|ies)|sanctum|passport)\b"),
    ("queue", r"\b(?:queues?|queued|observers?|scheduler|cron|artisan)\b"),
    ("database", r"\b(?:database|db|schema|sql|sqlite|mysql|postgres(?:ql)?)\b"),
    ("key", r"\b(?:foreign|primary) keys?\b"),
    ("PHPUnit", r"\b(?:phpunit|pest)\b|\bfeature tests?\b"),
    ("OpenAPI", r"\b(?:openapi|scramble|swagger)\b"),
    ("backend", r"\bback[- ]?end\b"),
    ("PHP", r"\bphp\b"),
    # A request to build an endpoint, as opposed to a component that calls one.
    ("new endpoint", r"\b(?:add|adds|create|creates|new|expose|exposes|implement|implements|"
                     r"introduce|introduces|provide|provides)\b[^.\n]{0,60}"
                     r"(?:\bendpoints?\b|/api/|\bapi routes?\b)"),
    ("API contract", r"/api/[^\s`]*`?\s+(?:returns?|responds?|must return|should return)\b"),
)

# Weak signals only decide when no strong one matched: "fetching GET /api/tasks"
# is what a frontend component does, so on its own an API mention means backend,
# but next to a PrimeVue DataTable it means nothing.
_BACKEND_WEAK = _signals(
    ("/api/ path", r"/api/"),
    ("endpoint", r"\b(?:endpoints?|apis?)\b"),
    ("JSON", r"\bjson\b"),
    ("status code", r"\bstatus codes?\b|\bhttp [1-5]\d\d\b"),
)

_FRONTEND_WEAK = _signals(
    ("page", r"\b(?:pages?|views?|forms?|labels?|placeholders?)\b"),
)


@dataclass(frozen=True)
class ScopeDecision:
    """The issue-text scope plus the evidence behind it, for the log and the planner."""

    scope: str                      # "backend" | "frontend" | "fullstack"
    basis: str                      # "explicit" | "signals" | "weak signals" | "no signals"
    frontend: tuple[str, ...] = ()  # matched frontend signal labels
    backend: tuple[str, ...] = ()   # matched backend signal labels
    statement: str = ""             # the explicit phrase when basis == "explicit"

    def evidence(self) -> str:
        """One short human-readable reason, e.g. ``frontend signals: button, colour``."""
        if self.basis == "explicit":
            return f'stated in the issue: "{self.statement}"'
        if self.basis == "no signals":
            return "no scope signal in the issue text"
        weak = "weak " if self.basis == "weak signals" else ""
        parts = [
            f"{weak}{side} signals: {', '.join(labels)}"
            for side, labels in (("frontend", self.frontend), ("backend", self.backend))
            if labels
        ]
        return "; ".join(parts)


def _side(word: str) -> str:
    """Normalise "front-end" / "full stack" / "Backend" to a SCOPES value."""
    return re.sub(r"[\s-]", "", word.lower())


def _not_negated(text: str, start: int) -> bool:
    """True unless the words just before *start* negate what follows."""
    return not _NEGATION_RE.search(text[max(0, start - _NEGATION_WINDOW):start])


def _matched(signals: tuple[tuple[str, re.Pattern[str]], ...], text: str) -> tuple[str, ...]:
    """Labels of the signals with at least one non-negated match in *text*."""
    return tuple(
        label
        for label, pattern in signals
        if any(_not_negated(text, match.start()) for match in pattern.finditer(text))
    )


def _from_sides(frontend: tuple[str, ...], backend: tuple[str, ...]) -> str | None:
    """frontend only → frontend, backend only → backend, both → fullstack, none → None."""
    if frontend and backend:
        return "fullstack"
    if frontend:
        return "frontend"
    if backend:
        return "backend"
    return None


def classify_issue(subject: str, description: str) -> ScopeDecision:
    """
    Classify an issue as backend, frontend or fullstack from its wording.

    Deterministic and offline; never raises.  See the module docstring for the
    precedence of explicit statements, strong signals and weak signals.
    """
    text = f"{subject or ''}\n{description or ''}"

    stated: dict[str, str] = {}
    for pattern, names_other_side in _EXPLICIT_RES:
        for match in pattern.finditer(text):
            side = _side(match.group(1))
            if names_other_side:
                side = "frontend" if side == "backend" else "backend"
            statement = " ".join(re.sub(r"[*_`#>]", " ", match.group(0)).split()).strip(" -")
            stated.setdefault(side, statement)
    if stated:
        scope = next(iter(stated)) if len(stated) == 1 else "fullstack"
        return ScopeDecision(scope, "explicit", statement="; ".join(stated.values()))

    lowered = text.lower()
    frontend = _matched(_FRONTEND_STRONG, lowered)
    backend = _matched(_BACKEND_STRONG, lowered)
    scope = _from_sides(frontend, backend)
    if scope:
        return ScopeDecision(scope, "signals", frontend, backend)

    frontend = _matched(_FRONTEND_WEAK, lowered)
    backend = _matched(_BACKEND_WEAK, lowered)
    scope = _from_sides(frontend, backend)
    if scope:
        return ScopeDecision(scope, "weak signals", frontend, backend)
    return ScopeDecision("fullstack", "no signals")


def declared_scope(plan: str) -> str | None:
    """
    The scope a plan declares on one of its first lines, or None.

    Tolerates the markdown a model wraps around the line — ``**SCOPE:**
    frontend``, ``# Scope: Full-stack`` — because a declaration the parser
    misses silently keeps the issue-text scope.
    """
    lines = [line.strip() for line in (plan or "").splitlines() if line.strip()]
    for line in lines[:_DECLARATION_LINES]:
        match = _DECLARED_SCOPE_RE.match(line)
        if match:
            return _side(match.group(1))
    return None


def widen(scope: str, side: str) -> str:
    """
    The narrowest scope that covers both *scope* and *side*.

    Never narrows: a backend scope that has to fix a frontend layer becomes
    fullstack, a fullstack scope stays fullstack, and an empty *side* changes
    nothing.
    """
    if not side or side == scope or scope == "fullstack":
        return scope
    return "fullstack"


def documentation_request(subject: str, description: str) -> str:
    """
    The phrase with which the issue asks for documentation work, or ``""``.

    Documentation files (README.md, CHANGELOG.md, docs/) are out of scope for
    an issue that does not ask for them — a new endpoint is not a request to
    describe it in the README.  A false positive only relaxes that rule to
    "change what the issue names", so the pattern errs on the side of matching;
    a negated mention ("do not touch the README") is not a request.
    """
    text = _URL_RE.sub(" ", f"{subject or ''}\n{description or ''}").lower()
    for match in _DOCS_REQUEST_RE.finditer(text):
        if _not_negated(text, match.start()):
            return match.group(0).strip(" .:;-\n")
    return ""
