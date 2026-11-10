"""
Starter kit for a Laravel API without a SPA: role-schema detection, overlay
selection and the PHP text edits that wire the starter files into an app.

``graph.tools.tool_starter_kit`` drives it; this module never imports ``graph``.
Every edit is a plain text edit that keeps the file's formatting and is
idempotent; the ``*_with_*`` functions are pure so a caller can validate an
edit before writing anything.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES = Path(__file__).resolve().parent / "templates" / "starter"
BACKEND_TEMPLATES = _TEMPLATES / "backend"
SPA_TEMPLATES = _TEMPLATES / "spa"

_SANCTUM_TRAITS = {"HasApiTokens": "Laravel\\Sanctum\\HasApiTokens"}
MODEL_TRAITS = {
    "none": dict(_SANCTUM_TRAITS),
    "custom": dict(_SANCTUM_TRAITS),
    "spatie": {**_SANCTUM_TRAITS, "HasRoles": "Spatie\\Permission\\Traits\\HasRoles"},
}

# Seed data: kept when the app already has it; every other overlay file is a contract file.
DATA_FILES = (
    "database/seeders/RolePermissionSeeder.php",
    "database/seeders/UserSeeder.php",
    "tests/Feature/DatabaseSeederTest.php",
)

_ROUTES_STUB = "routes.stub"
_ROUTE_FACADE = "use Illuminate\\Support\\Facades\\Route;"
_CLASS_USER = re.compile(r"^(?:final\s+|abstract\s+)?class\s+User\b[^{]*\{", re.MULTILINE)
_CLASS_TRAITS = re.compile(r"^([ \t]+)use ([A-Z][\w\\, ]*);", re.MULTILINE)
_RUN_METHOD = re.compile(r"public\s+function\s+run\(\)(?:\s*:\s*void)?\s*\{")

_MINIMAL_SEEDER = """<?php

namespace Database\\Seeders;

use Illuminate\\Database\\Seeder;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $this->call([%s]);
    }
}
"""


def _creates_table(texts: list[str], table: str) -> bool:
    pattern = re.compile(rf"Schema::create\(\s*['\"]{table}['\"]")
    return any(pattern.search(text) for text in texts)


def role_schema(app_root: Path) -> str:
    """``"spatie"`` (composer package), ``"custom"`` (own roles + permissions tables) or ``"none"``."""
    try:
        composer = json.loads((app_root / "composer.json").read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Unreadable composer.json in %s: %s", app_root, exc)
        composer = {}
    for key in ("require", "require-dev"):
        packages = composer.get(key) if isinstance(composer, dict) else None
        if isinstance(packages, dict) and "spatie/laravel-permission" in packages:
            return "spatie"
    texts = [p.read_text(encoding="utf-8", errors="replace")
             for p in (app_root / "database" / "migrations").glob("**/*.php")]
    if _creates_table(texts, "roles") and _creates_table(texts, "permissions"):
        return "custom"
    return "none"


def backend_overlays(variant: str) -> list[str]:
    """Backend overlay folders for *variant*, in copy order (later overwrite earlier)."""
    return {"spatie": ["common", "spatie"], "custom": ["common", "plain", "custom"]}.get(
        variant, ["common", "plain"])


def seeder_classes(variant: str) -> list[str]:
    """Seeder classes ``DatabaseSeeder`` must call for *variant*."""
    return ["RolePermissionSeeder", "UserSeeder"] if variant == "spatie" else ["UserSeeder"]


def overlay_files(root: Path, overlays: list[str]) -> dict[str, Path]:
    """Relative path → source file across *overlays* under *root* (later wins), without ``routes.stub``."""
    files: dict[str, Path] = {}
    for name in overlays:
        base = root / name
        if not base.is_dir():
            raise FileNotFoundError(f"starter kit template missing: {base}")
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            rel = path.relative_to(base).as_posix()
            if rel != _ROUTES_STUB:
                files[rel] = path
    return files


def routes_stub(root: Path, overlays: list[str]) -> Path | None:
    """The ``routes.stub`` of the last overlay that has one."""
    return next((root / name / _ROUTES_STUB for name in reversed(overlays)
                 if (root / name / _ROUTES_STUB).is_file()), None)


def model_with_traits(text: str, traits: dict[str, str]) -> str:
    """
    *text* (a ``User`` model) importing and using every trait of *traits* (short name → FQCN).

    A missing import goes after the last top-level ``use`` (else after ``namespace``);
    a missing trait is prepended to the class's first ``use A, B;`` statement, or
    gets its own statement right after the opening brace. Raises ValueError
    without ``class User``.
    """
    for short, fqcn in traits.items():
        head = _CLASS_USER.search(text)
        if not head:
            raise ValueError("app/Models/User.php has no class User")
        header = text[:head.start()]
        if not re.search(rf"^use {re.escape(fqcn)};", header, re.MULTILINE):
            imports = list(re.finditer(r"^use [^;\n]+;", header, re.MULTILINE))
            anchor = imports[-1] if imports else re.search(r"^namespace [^;\n]+;", header, re.MULTILINE)
            if not anchor:
                raise ValueError("app/Models/User.php has no namespace")
            line = f"\nuse {fqcn};" if imports else f"\n\nuse {fqcn};"
            text = text[:anchor.end()] + line + text[anchor.end():]
            head = _CLASS_USER.search(text)
        used = _CLASS_TRAITS.search(text, head.end())
        if used:
            if short not in (name.strip() for name in used.group(2).split(",")):
                text = text[:used.start(2)] + f"{short}, " + text[used.start(2):]
        else:
            text = text[:head.end()] + f"\n    use {short};" + text[head.end():]
    return text


def add_model_traits(model: Path, traits: dict[str, str]) -> bool:
    """Apply ``model_with_traits`` to *model*; return whether the file changed."""
    text = model.read_text(encoding="utf-8")
    changed = model_with_traits(text, traits)
    if changed == text:
        return False
    model.write_text(changed, encoding="utf-8")
    return True


def seeder_with_calls(text: str, classes: list[str]) -> str:
    """
    *text* (a ``DatabaseSeeder``) calling every class of *classes*: one
    ``$this->call([...])`` for the missing ones, first in ``run()``.
    Raises ValueError when a call is missing and there is no ``run()``.
    """
    missing = [name for name in classes if not re.search(rf"\b{name}::class", text)]
    if not missing:
        return text
    run = _RUN_METHOD.search(text)
    if not run:
        raise ValueError("database/seeders/DatabaseSeeder.php has no run() method")
    call = ", ".join(f"{name}::class" for name in missing)
    return text[:run.end()] + f"\n        $this->call([{call}]);" + text[run.end():]


def register_seeders(seeder: Path, classes: list[str]) -> bool:
    """Make *seeder* call *classes* (a missing file becomes a minimal DatabaseSeeder); return whether it changed."""
    if not seeder.is_file():
        seeder.parent.mkdir(parents=True, exist_ok=True)
        seeder.write_text(_MINIMAL_SEEDER % ", ".join(f"{n}::class" for n in classes), encoding="utf-8")
        return True
    text = seeder.read_text(encoding="utf-8")
    changed = seeder_with_calls(text, classes)
    if changed == text:
        return False
    seeder.write_text(changed, encoding="utf-8")
    return True


def append_routes(routes: Path, stub: Path) -> None:
    """Append *stub* to *routes* after one blank line, importing the Route facade first when missing."""
    text = routes.read_text(encoding="utf-8")
    if _ROUTE_FACADE not in text:
        opening, _, rest = text.partition("\n")
        text = f"{opening}\n\n{_ROUTE_FACADE}\n{rest}"
    text = text.rstrip("\n") + "\n\n" + stub.read_text(encoding="utf-8").rstrip("\n") + "\n"
    routes.write_text(text, encoding="utf-8")
