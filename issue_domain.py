"""
issue_domain.py – which domain of a domain-split Laravel backend an issue changes.

A backend whose code lives in ``app/<Root>/<Domain>/…`` vertical slices (see
``project_layout._scan_backend``) must receive each change in the owning
domain.  ``detect`` decides deterministically: a domain stated in the issue,
else the domain owning the routes the issue names.  ``classify`` then lets the
planner LLM (passed in; this module never calls a provider itself) pick, and
its answer counts only when exactly one domain is plausible.

Question protocol: when nothing decides, Nesti posts one note
"Talebiniz hangi domain için?" listing the domains, carrying a hidden
``NESTI_DOMAIN_QUESTION_V1`` marker with the options, and pauses the issue.
``reconcile`` resumes it once a human reply names exactly one option, and asks
again once per unmatched reply.

Trust rule: only notes authored by Nesti's own GitLab user count as questions,
and only notes by anyone else, newer than the latest question, count as
answers.  A pause without a Nesti question is never lifted here.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import project_layout

logger = logging.getLogger(__name__)

QUESTION_MARKER = "NESTI_DOMAIN_QUESTION_V1"
QUESTION = "Talebiniz hangi domain için?"
_URL_RE = re.compile(r"https?://\S+")
_TOKENS = re.compile(r"""
  (?P<comment>//[^\n]*|\#(?!\[)[^\n]*|/\*.*?\*/)
| (?:Route::|->)\s*(?P<method>prefix|get|post|put|patch|delete|options|any|match|resource|apiResource)\s*\(\s*(?:\[[^\]]*\]\s*,\s*)?(?P<q>['"])(?P<uri>[^'"]*)(?P=q)
| (?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
| (?P<group>->\s*group\s*\(\s*(?:static\s+)?function\b[^{;]*\{)
| (?P<open>\{)
| (?P<close>\})
| (?P<end>;)
""", re.S | re.X)
_USE_RE = re.compile(r"^\s*use\s+\\?([\w\\]+?)(?:\s+as\s+(\w+))?\s*;", re.M)
_ACTION_RE = re.compile(r"\\?([A-Za-z_][\w\\]*)::class")
_ROUTE_PATH_RE = re.compile(r"(?<![\w.:/\\-])/[\w{}:.-]+(?:/[\w{}:.-]+)*")
_FILE_SUFFIX_RE = re.compile(r"\.(?:php|vue|js|ts|json|md|css|html|xml|ya?ml)$", re.I)
_CLASSIFY_SYSTEM = (
    "You decide which backend domain of a Laravel application a GitLab issue changes. The backend "
    "splits its code into the domains the user lists. Answer with ONE JSON object and nothing else: "
    '{"domains": ["<name>", ...], "reason": "<one sentence>"}. List every domain the requested backend '
    "change could plausibly belong to, with names exactly as listed: several when it fits more than one, "
    "none when no listed domain fits. Never pick a single domain you are unsure of."
)


# ---------------------------------------------------------------------------
# Route parsing
# ---------------------------------------------------------------------------

def _join(*parts: str) -> str:
    return "/".join(p.strip("/") for p in parts if p.strip("/"))


def _route_owners(text: str, root: str, names: list[str]) -> list[tuple[str, set[str]]]:
    """Every route URI of one route file with the domains owning its action."""
    # shortcut: array-style Route::group(['prefix' => …]) and named arguments are not followed; extend the tokenizer when a project uses them.
    uses = {alias or fq.rsplit("\\", 1)[-1]: fq for fq, alias in _USE_RE.findall(text)}
    domain_re = re.compile(rf"App\\{re.escape(root)}\\(\w+)\\")

    def domain_of(fq: str) -> str | None:
        match = domain_re.match(fq.lstrip("\\"))
        return match.group(1) if match and match.group(1) in names else None

    file_owners = {d for d in map(domain_of, uses.values()) if d}
    file_owners |= {d for d in domain_re.findall(text) if d in names}

    routes: list[tuple[str, set[str]]] = []
    stack, chain = [""], ""
    for m in _TOKENS.finditer(text):
        kind = m.lastgroup
        if m.group("method"):
            uri = m.group("uri")
            if m.group("method") == "prefix":
                chain = _join(chain, uri)
                continue
            stop = text.find(";", m.end())
            action = _ACTION_RE.search(text, m.end(), stop if stop >= 0 else len(text))
            fq = None
            if action:
                name = action.group(1)
                fq = name if "\\" in name else uses.get(name)
            owners = {d for d in [domain_of(fq)] if d} if fq else set(file_owners)
            routes.append((_join(stack[-1], chain, uri), owners))
        elif kind == "group":
            stack.append(_join(stack[-1], chain))
            chain = ""
        elif kind == "open":
            stack.append(stack[-1])
        elif kind == "close":
            if len(stack) > 1:
                stack.pop()
        elif kind == "end":
            chain = ""
    return routes


def _segments(path: str) -> list[str]:
    return ["{}" if s[:1] in "{:" else s for s in path.lower().strip("/").split("/") if s]


def _route_owner(path: str, routes: list) -> tuple[set[str], bool]:
    """(domains owning *path*, whether it matches a route outside every domain)."""
    segs = _segments(path)
    parsed = [(_segments(uri), set(owners)) for uri, owners in routes]
    # drop strips a leading api/ or v1/ the route files do not carry.
    for drop in range(min(2, len(segs) - 1) + 1):
        wanted = segs[drop:]
        best, owners, unowned = 0, set(), False
        for route_segs, route_owners in parsed:
            shared = 0
            for a, b in zip(wanted, route_segs):
                if a != b:
                    break
                shared += 1
            if shared and shared >= best:
                if shared > best:
                    best, owners, unowned = shared, set(), False
                owners |= route_owners
                unowned = unowned or not route_owners
        if best:
            return owners, unowned
    return set(), True


def _name_pattern(name: str) -> str:
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", name) or [name]
    return r"(?<![^\W_])" + r"[\s_-]*".join(map(re.escape, parts)) + r"(?![^\W_])"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainDecision:
    """The deterministic domain decision for one issue."""

    domain: str | None   # decided domain
    ask: bool            # evidence conflicts or points outside every domain: ask now
    basis: str           # reason, for the DOMAIN: log line


def domain_catalog(backend: Path) -> dict | None:
    """The domains of *backend* with their routes and classes; None without a domain architecture."""
    scan = project_layout._scan_backend(backend)
    root = scan["domain_root"]
    if not root:
        return None
    names = [d["name"] for d in scan["domains"]]
    base = backend.resolve()
    routes: list[tuple[str, set[str]]] = []
    files: dict[str, list[tuple[str, set[str]]]] = {}
    for path in sorted((backend / "routes").rglob("*.php")):
        try:
            if not path.is_file() or not path.resolve().is_relative_to(base):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = _route_owners(text, root, names)
        files[path.relative_to(backend).as_posix()] = parsed
        routes += parsed
    domains = []
    for name in names:
        folder = backend / "app" / root / name
        domains.append({
            "name": name,
            "route_files": sorted(f for f, parsed in files.items()
                                  if any(owners == {name} for _, owners in parsed)),
            "uris": sorted(uri for uri, owners in routes if name in owners)[:20],
            "classes": sorted(f.stem for f in project_layout._walk_files(folder)
                              if f.suffix == ".php")[:20],
        })
    return {"root": root, "layers": scan["common_layers"], "domains": domains,
            "routes": [[uri, sorted(owners)] for uri, owners in routes]}


def route_paths(text: str) -> list[str]:
    """Route-like paths named in *text* (URLs and file names excluded), in order."""
    found: list[str] = []
    for hit in _ROUTE_PATH_RE.findall(_URL_RE.sub(" ", text)):
        hit = hit.rstrip(".:")
        if hit and not _FILE_SUFFIX_RE.search(hit) and hit not in found:
            found.append(hit)
    return found


def detect(subject: str, description: str, catalog: dict) -> DomainDecision:
    """Decide the domain from an explicit mention, else from the routes the issue names."""
    text = _URL_RE.sub(" ", f"{subject}\n{description}")
    root = re.escape(catalog["root"])
    names = [d["name"] for d in catalog["domains"]]
    stated = []
    for name in names:
        n, p = re.escape(name), _name_pattern(name)
        pattern = rf"app/{root}/{n}(?!\w)|App\\{root}\\{n}(?!\w)|\bdomain\s*[:=]\s*{p}|{p}\s+domain\b"
        if re.search(pattern, text, re.I):
            stated.append(name)
    if len(stated) == 1:
        return DomainDecision(stated[0], False, "stated in the issue")
    if stated:
        return DomainDecision(None, True, f"the issue names several domains: {', '.join(stated)}")

    paths = route_paths(text)
    owners: set[str] = set()
    for path in paths:
        found, unowned = _route_owner(path, catalog["routes"])
        if unowned:
            return DomainDecision(None, True, f"route {path} belongs to no domain")
        owners |= found
    if len(owners) == 1:
        return DomainDecision(next(iter(owners)), False, "route " + ", ".join(paths))
    if owners:
        ordered = [n for n in names if n in owners]
        return DomainDecision(None, True, f"routes span several domains: {', '.join(ordered)}")
    return DomainDecision(None, False, "no route or domain named in the issue")


def classify(subject: str, description: str, catalog: dict, llm) -> tuple[list[str], str]:
    """The domains the planner LLM finds plausible for the issue, with its reason."""
    names = [d["name"] for d in catalog["domains"]]
    lines = [f"Domains under app/{catalog['root']}/:"]
    for d in catalog["domains"]:
        lines.append(f"- {d['name']}: routes {', '.join(d['uris'][:12]) or 'none'}; "
                     f"classes {', '.join(d['classes'][:12]) or 'none'}")
    unowned = [uri for uri, owners in catalog["routes"] if not owners][:20]
    lines.append(f"Routes outside every domain: {', '.join(unowned) or 'none'}")
    user = "\n".join(lines) + f"\n\nGitLab issue: {subject}\n{description}"
    try:
        reply = llm.generate_plan(_CLASSIFY_SYSTEM, user)
    except Exception as exc:  # pylint: disable=broad-except
        return [], f"classification failed: {exc}"
    match = re.search(r"\{.*\}", reply or "", re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    raw = data.get("domains")
    wanted = {x.casefold() for x in (raw if isinstance(raw, list) else []) if isinstance(x, str)}
    return [n for n in names if n.casefold() in wanted], str(data.get("reason") or "")[:200]


def selection(catalog: dict, name: str) -> dict:
    """The IssueState ``domain`` value for *name* ("" = not chosen)."""
    route_files = next((d["route_files"] for d in catalog["domains"] if d["name"] == name), [])
    return {"root": catalog["root"], "layers": catalog["layers"],
            "names": [d["name"] for d in catalog["domains"]],
            "name": name, "route_files": route_files if name else []}


def format_question(options: list[str], retry: bool = False) -> str:
    """The GitLab question note listing *options*, with the hidden marker."""
    lines = [QUESTION, ""]
    lines += [f"{i}. `{name}`" for i, name in enumerate(options, 1)]
    lines += ["", "Yanıt olarak seçeneklerden birinin adını veya numarasını yazın."]
    if retry:
        lines.append("_Önceki yanıt hiçbir seçenekle eşleşmedi._")
    lines += ["", f"<!-- {QUESTION_MARKER} {json.dumps(options, ensure_ascii=False)} -->"]
    return "\n".join(lines)


def question_options(body: str) -> list[str] | None:
    """The options of a Nesti domain question note, else None."""
    try:
        match = re.search(rf"<!-- {QUESTION_MARKER} (\[.*?\]) -->", body or "", re.S)
        options = json.loads(match.group(1)) if match else None
    except Exception:  # pylint: disable=broad-except
        return None
    if isinstance(options, list) and options and all(isinstance(o, str) and o for o in options):
        return options
    return None


def parse_answer(body: str, options: list[str]) -> str | None:
    """The single option a human reply names (by number or name), else None."""
    text = re.sub(r"<!--.*?-->", " ", body or "", flags=re.S)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    text = text.replace("`", " ").replace("*", " ")
    number = re.fullmatch(r"\s*(\d+)\s*[.)]?\s*", text)
    if number and 1 <= int(number.group(1)) <= len(options):
        return options[int(number.group(1)) - 1]
    named = [o for o in options if re.search(_name_pattern(o), text, re.I)]
    return named[0] if len(named) == 1 else None


def answer(notes: list[dict], user_id: int, options: list[str]) -> str | None:
    """The domain the newest human reply to Nesti's latest question names, else None."""
    questions = [n for n in notes
                 if n.get("author_id") == user_id and question_options(n.get("body") or "") is not None]
    if not questions:
        return None
    question_id = max(n["id"] for n in questions)
    replies = sorted((n for n in notes if n.get("author_id") != user_id and n["id"] > question_id),
                     key=lambda n: n["id"], reverse=True)
    for note in replies:
        chosen = parse_answer(note.get("body") or "", options)
        if chosen:
            return chosen
    return None


def ask(client, iid: int, options: list[str]) -> None:
    """Post the domain question on *iid* and pause it. Raises RuntimeError."""
    client.post_note(iid, format_question(options))
    if not client.pause_issue(iid):
        raise RuntimeError(f"issue #{iid} was not paused after the domain question")


def reconcile(client) -> dict:
    """Resume answered domain questions, re-ask unmatched replies, report the waiting ones."""
    summary: dict = {"resumed": [], "asked": [], "waiting": [], "errors": []}
    issues = client.list_issues(state="opened", labels=[client.issue_label, client.pause_label])
    if not issues:
        return summary
    user_id = client.current_user_id()
    for issue in issues:
        iid = issue["iid"]
        try:
            notes = client.list_notes(iid)
            mine = [n for n in notes if n.get("author_id") == user_id]
            latest = max(mine, key=lambda n: n["id"]) if mine else None
            options = question_options(latest.get("body") or "") if latest else None
            if latest is None or options is None:
                continue
            if not any(n.get("author_id") != user_id and n["id"] > latest["id"] for n in notes):
                summary["waiting"].append(iid)
            elif answer(notes, user_id, options):
                # shortcut: a manual pause added between this resume and the claim is lifted again while the question is still Nesti's latest note; mark the question answered if that ever matters.
                if not client.resume_issue(iid):
                    raise RuntimeError("resume was not verified")
                summary["resumed"].append(iid)
            else:
                client.post_note(iid, format_question(options, retry=True))
                summary["asked"].append(iid)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Domain question reconcile failed for issue #%s: %s", iid, exc)
            summary["errors"].append({"issue_id": iid, "error": str(exc)})
    return summary
