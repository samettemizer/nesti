"""Offline tests for project layout resolution, architecture summaries and /boost."""

import base64
import fcntl
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import project_boost
import project_layout
from project_boost import BoostError
from project_layout import LayoutError


class StubLLM:
    """Scripted ``generate_plan`` replies; raises when called past the script."""

    last_planner_label = "stub-provider (model x)"

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.calls = 0

    def generate_plan(self, system: str, user: str, messages=None) -> str:
        self.calls += 1
        if not self.replies:
            raise AssertionError("stub LLM called unexpectedly")
        return self.replies.pop(0)


def _touch(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class _StateCase(unittest.TestCase):
    """Points project_layout's state at a tmp dir, never the repo's state/."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "project"
        self.root.mkdir()
        self._saved = (project_layout.STATE_DIR, project_layout.LAYOUT_FILE)
        project_layout.STATE_DIR = self.tmp / "state"
        project_layout.LAYOUT_FILE = project_layout.STATE_DIR / "layout.json"

    def tearDown(self):
        project_layout.STATE_DIR, project_layout.LAYOUT_FILE = self._saved
        self._tmp.cleanup()

    def make_monorepo(self, root: Path) -> None:
        _touch(root / "backend/artisan")
        _touch(root / "backend/composer.json", json.dumps({"require": {"php": "^8.4"}}))
        _touch(root / "frontend/package.json", json.dumps({"dependencies": {"vue": "^3.5"}}))


class LayoutTests(_StateCase):
    def test_wrong_answer_rejected_after_one_retry(self):
        self.make_monorepo(self.root)
        bad = '{"backend": "frontend"}'
        llm = StubLLM(bad, bad)
        with self.assertRaises(LayoutError):
            project_layout.resolve_layout(self.root, llm)
        self.assertEqual(llm.calls, 2)

    def test_correct_answer_persists_separated(self):
        self.make_monorepo(self.root)
        llm = StubLLM('```json\n{"backend":"backend","frontend":"frontend","reason":"x"}\n```')
        project_layout.resolve_layout(self.root, llm)
        saved = json.loads(project_layout.LAYOUT_FILE.read_text())
        self.assertEqual(saved["mode"], "separated")
        self.assertEqual(saved["resolved_by"], StubLLM.last_planner_label)

    def test_root_artisan_is_deterministic(self):
        _touch(self.root / "artisan")
        record = project_layout.resolve_layout(self.root, StubLLM())
        self.assertEqual(record["mode"], "backend-only")
        self.assertTrue(record["resolved_by"].startswith("deterministic:"))

    def test_root_artisan_with_plugin_vue_is_integrated(self):
        _touch(self.root / "artisan")
        _touch(self.root / "vite.config.js", "import vue from '@vitejs/plugin-vue';")
        self.assertEqual(project_layout.resolve_layout(self.root, StubLLM())["mode"], "integrated")

    def test_empty_dir_is_greenfield(self):
        (self.root / ".git").mkdir()
        self.assertEqual(project_layout.resolve_layout(self.root, StubLLM())["mode"], "greenfield")

    def test_clone_layout_reports_missing_backend_artisan(self):
        self.make_monorepo(self.root)
        project_layout.resolve_layout(
            self.root, StubLLM('{"backend":"backend","frontend":"frontend","reason":"x"}'))
        clone = self.tmp / "clone"
        self.make_monorepo(clone)
        self.assertEqual(project_layout.clone_layout(clone), {"backend": "backend", "frontend": "frontend"})
        (clone / "backend/artisan").unlink()
        with self.assertRaisesRegex(LayoutError, "does not match the repository.*artisan.*nesti /arch"):
            project_layout.clone_layout(clone)


class SummaryTests(_StateCase):
    def test_domain_architecture(self):
        self.make_monorepo(self.root)
        for domain in ("A", "B", "C"):
            for layer in ("Http", "Models", "Repository"):
                _touch(self.root / f"backend/app/Domains/{domain}/{layer}/X.php", "<?php")
        arch = project_layout.scan_architecture(self.root, {"backend": "backend", "frontend": "frontend"})
        first, second = arch["summary"][:2]
        self.assertIn("backend/app/Domains/*", first)
        self.assertIn("3 domains", first)
        self.assertIn("Repository", second)

    def test_default_architecture(self):
        _touch(self.root / "artisan")
        _touch(self.root / "composer.json", "{}")
        _touch(self.root / "app/Http/Controllers/X.php", "<?php")
        _touch(self.root / "app/Models/User.php", "<?php")
        arch = project_layout.scan_architecture(self.root, {"backend": ".", "frontend": None})
        self.assertIn("follows Laravel's default", arch["summary"][0])


def _boost_project(root: Path) -> Path:
    """A separated project whose backend has Boost, its infer-conventions skill and one more skill."""
    backend = root / "backend"
    _touch(backend / "artisan")
    _touch(backend / "composer.json", json.dumps({"require": {"php": "^8.4", "laravel/framework": "^13.0"}}))
    _touch(backend / "vendor/laravel/boost/composer.json", "{}")
    _touch(backend / "vendor/composer/installed.json",
           json.dumps({"packages": [{"name": "laravel/boost", "version": "v2.10.3"}]}))
    skill = backend / ".claude/skills/infer-conventions"
    _touch(skill / "SKILL.md", "---\nname: infer-conventions\n---\n# Infer\n\n"
           "### Step 2: Open-ended pass\nMap every app/ folder.\n\n### Step 3: Confirm\nAsk.\n")
    _touch(skill / "references/checklist.md", "# Checklist\n\n## A. Validation & HTTP input\n\n"
           "1. Validation entry point.\n")
    _touch(backend / ".claude/skills/laravel-best-practices/SKILL.md",
           '---\nname: laravel-best-practices\ndescription: "Laravel practices"\n---\nBody\n')
    _touch(backend / "CLAUDE.md", "<laravel-boost-guidelines>\n=== foundation rules ===\nUse PHP 8.4.\n\n"
           "=== boost rules ===\nUse search-docs.\n</laravel-boost-guidelines>\n\nTeam note: no Friday deploys.\n")
    for name in "ABC":
        _touch(backend / f"app/Http/Controllers/{name}Controller.php", "<?php $request->validate([]);")
        _touch(root / f"frontend/src/stores/{name.lower()}.ts", "export const useX = defineStore('x', () => {});")
    _touch(root / "frontend/package.json", json.dumps({"dependencies": {"vue": "^3.5", "primevue": "^4.4.1"}}))
    return backend


class FakeBoostRunner:
    """Stands in for DockerRunner: applies RecordRule calls like Boost's RuleRepository."""

    def __init__(self):
        self.calls: list[tuple[str, bool]] = []

    def run_boost_script(self, app_path: str, script: str, *, network: bool) -> tuple[bool, str]:
        self.calls.append((script, network))
        out = []
        for b64 in re.findall(r"RecordRule' (\S+);", script):
            rule = json.loads(base64.b64decode(b64))
            area = "-".join(p.lower() for p in rule["glob"].split("/") if "*" not in p)
            path = Path(app_path) / ".ai/rules" / f"{area}.md"
            text = path.read_text() if path.exists() else f"---\npaths:\n  - '{rule['glob']}'\n---\n\n# {area}\n"
            _touch(path, text.rstrip("\n") + f"\n\n## {rule['title']}\n{rule['note']}\n")
            out.append('{"isError":false,"content":[]}@@NESTI@@')
        return True, "\n".join(out)


class ScriptedLLM:
    """``generate_plan`` answered by a function of (system, user, messages)."""

    last_planner_label = "stub-provider (model x)"

    def __init__(self, respond):
        self.respond = respond
        self.calls: list[tuple[str, str, list]] = []

    def generate_plan(self, system: str, user: str, messages=None) -> str:
        self.calls.append((system, user, list(messages or [])))  # the caller keeps appending to its history
        return self.respond(system, user, messages or [])


class BoostToolsTests(_StateCase):
    def setUp(self):
        super().setUp()
        _touch(self.root / ".env", "APP_KEY=secret")
        _touch(self.root / "app/X.php", "<?php needle")
        _touch(self.root / "vendor/pkg/Y.php", "<?php needle")
        _touch(self.tmp / "outside/secret.txt", "needle")
        os.symlink(self.tmp / "outside", self.root / "link")
        self.tools = project_boost._ReadOnlyTools(self.root)

    def test_secret_escape_and_symlink_paths_are_refused(self):
        for path in (".env", "../x", "link/secret.txt"):
            with self.subTest(path):
                self.assertIn("refused", self.tools.run([{"tool": "read", "path": path}]))
        self.assertIn("1: <?php needle", self.tools.run([{"tool": "read", "path": "app/X.php"}]))

    def test_grep_skips_vendor_and_symlinks(self):
        out = self.tools.run([{"tool": "grep", "pattern": "needle"}])
        self.assertIn("app/X.php:1: <?php needle", out)
        self.assertNotIn("vendor/", out)
        self.assertNotIn("link/", out)


class BoostPatternTests(_StateCase):
    def test_pattern_needs_three_existing_files(self):
        for name in "ABC":
            _touch(self.root / f"app/{name}.php", "<?php")
        tools = project_boost._ReadOnlyTools(self.root)
        verdict = {"verdict": "pattern", "globs": ["app/**"], "title": "Title", "note": "Do X."}
        patterns, _, rejected = project_boost._classify(
            [{**verdict, "evidence": ["app/A.php", "app/B.php", "app/missing.php"]}], tools)
        self.assertEqual((len(patterns), len(rejected)), (0, 1))
        patterns, _, rejected = project_boost._classify(
            [{**verdict, "evidence": ["app/A.php", "app/B.php", "app/C.php"]}], tools)
        self.assertEqual((len(patterns), len(rejected)), (1, 0))


class BoostConversionTests(_StateCase):
    UNITS = [project_boost._Unit("U1", "backend-rule", "backend", ["app/**"], "T", "x"),
             project_boost._Unit("U2", "backend-guideline", "backend", [], "g", "y")]
    RECORD = {"layout": {"backend": "backend", "frontend": "frontend"}, "architecture": {"summary": []}}

    @staticmethod
    def reply(units: list[str], globs: tuple[str, ...] = ()) -> str:
        return json.dumps({"rules": [{"name": "rule-one", "description": "A rule description",
                                      "alwaysApply": False, "globs": list(globs), "units": units}],
                           "skills": [], "skipped": []})

    def test_invalid_conversions_raise_after_one_retry(self):
        cases = ((self.reply(["U1", "U2", "U9"]), "unknown unit"),
                 (self.reply(["U1"]), "neither converted nor skipped"),
                 (self.reply(["U1", "U2"], ("app/**",)), "must start with backend/ or frontend/"))
        for bad, reason in cases:
            with self.subTest(reason):
                llm = StubLLM(bad, bad)
                with self.assertRaisesRegex(BoostError, reason):
                    project_boost._convert(llm, self.RECORD, self.UNITS, [])
                self.assertEqual(llm.calls, 2)

    def test_retry_can_correct_the_reply(self):
        llm = StubLLM(self.reply(["U1"]), self.reply(["U1", "U2"], ("backend/app/**",)))
        data = project_boost._convert(llm, self.RECORD, self.UNITS, [])
        self.assertEqual(data["rules"][0]["units"], ["U1", "U2"])


class BoostPublishTests(_StateCase):
    def test_fresh_publish_then_refresh_keeps_user_files(self):
        omp = self.root / ".omp"
        first = {"rules/a.md": b"A1", "rules/b.md": b"B1", "skills/s/SKILL.md": b"S",
                 project_boost.MANIFEST: b'{"boost_version": "v2"}'}
        report = project_boost._publish(self.root, first)
        self.assertEqual(sorted(report["written"]), ["rules/a.md", "rules/b.md", "skills/s/SKILL.md"])
        manifest = json.loads((omp / project_boost.MANIFEST).read_text())
        self.assertEqual((manifest["boost_version"], sorted(manifest["files"])),
                         ("v2", ["rules/a.md", "rules/b.md", "skills/s/SKILL.md"]))
        self.assertFalse((self.root / ".omp.nesti-staging").exists())

        (omp / "rules/a.md").write_bytes(b"A1 plus a user line")
        (omp / "rules/c.md").write_bytes(b"user rule")
        _touch(omp / "agents/mine.md", "mine")
        report = project_boost._publish(self.root, {"rules/a.md": b"A2", "rules/b.md": b"B2", "rules/c.md": b"C2"})
        self.assertEqual(report, {"written": ["rules/b.md"], "removed": ["skills/s/SKILL.md"],
                                  "kept_user_modified": ["rules/a.md"], "conflicts": ["rules/c.md"]})
        self.assertEqual((omp / "rules/a.md").read_bytes(), b"A1 plus a user line")
        self.assertEqual((omp / "rules/b.md").read_bytes(), b"B2")
        self.assertEqual((omp / "rules/c.md").read_bytes(), b"user rule")
        self.assertEqual((omp / "agents/mine.md").read_text(), "mine")
        self.assertFalse((omp / "skills/s").exists())
        self.assertEqual(list(json.loads((omp / project_boost.MANIFEST).read_text())["files"]), ["rules/b.md"])

    def test_symlinked_omp_is_refused(self):
        (self.tmp / "elsewhere").mkdir()
        os.symlink(self.tmp / "elsewhere", self.root / ".omp")
        with self.assertRaises(BoostError):
            project_boost._publish(self.root, {"rules/a.md": b"A"})


class BoostRunTests(_StateCase):
    BACKEND_PATTERN = {
        "dimension": "1. Validation entry point", "verdict": "pattern", "globs": ["app/Http/**"],
        "evidence": ["app/Http/Controllers/AController.php", "app/Http/Controllers/BController.php",
                     "app/Http/Controllers/CController.php:1"],
        "title": "Validate inline", "note": "Validate requests inline with $request->validate()."}
    SPA_PATTERN = {
        "dimension": "12. Pinia store style", "verdict": "pattern", "globs": ["src/stores/**"],
        "evidence": ["src/stores/a.ts", "src/stores/b.ts", "src/stores/c.ts"],
        "title": "Setup stores", "note": "Write Pinia stores as setup stores."}

    def respond(self, system: str, user: str, messages: list) -> str:
        if system.startswith("Convert these Laravel Boost outputs"):
            units = re.findall(r"^### (U\d+) · (\S+)", user, re.M)
            return json.dumps({"rules": [
                {"name": "backend-conventions", "description": "Laravel API conventions and guidelines",
                 "alwaysApply": False, "globs": [], "units": [u for u, k in units if k.startswith("backend")]},
                {"name": "spa-stores", "description": "Pinia store conventions of the SPA",
                 "alwaysApply": False, "globs": [], "units": [u for u, k in units if k == "frontend-rule"]}],
                "skills": [{"name": "laravel-best-practices", "include": True, "reason": "useful"}],
                "skipped": []})
        first = messages[0]["content"]
        if "## Your assignment: A. Validation" in first:
            if len(messages) == 1:
                return '```json\n{"actions":[{"tool":"grep","pattern":"->validate(","path":"app"}]}\n```'
            return json.dumps({"verdicts": [self.BACKEND_PATTERN]})
        if "## Your assignment: M. Routing & state" in first:
            return json.dumps({"verdicts": [self.SPA_PATTERN, {"dimension": "13", "verdict": "conflict"}]})
        return '{"verdicts": []}'

    def test_run_boost_records_backend_rules_and_publishes_omp(self):
        backend = _boost_project(self.root)
        record = project_layout.resolve_layout(
            self.root, StubLLM('{"backend":"backend","frontend":"frontend","reason":"x"}'))
        project_layout.refresh_architecture(record)
        runner, llm = FakeBoostRunner(), ScriptedLLM(self.respond)
        lines: list[str] = []
        with patch.object(project_boost, "DockerRunner", lambda: runner):
            report = project_boost.run_boost(self.root, record, llm, progress=lines.append)

        self.assertEqual(report["backend"]["recorded"], [{"glob": "app/Http/**", "title": "Validate inline"}])
        self.assertEqual([network for _, network in runner.calls], [False])
        self.assertIn("## Validate inline", (backend / ".ai/rules/app-http.md").read_text())
        self.assertEqual(len(report["frontend"]["patterns"]), 1)
        self.assertEqual(len(report["frontend"]["conflicts"]), 1)
        self.assertIn("app/Http/Controllers/AController.php:1:", llm.calls[1][2][-1]["content"])
        self.assertIn("[backend 1/2] A. Validation & HTTP input — 2 turns, 1 pattern, 0 conflicts", lines)

        rules = self.root / ".omp/rules"
        backend_rule = (rules / "backend-conventions.md").read_text()
        self.assertIn('globs: ["backend/app/Http/**"]', backend_rule)
        self.assertIn("=== foundation rules ===", backend_rule)
        self.assertIn("Team note: no Friday deploys.", backend_rule)
        self.assertIn('globs: ["frontend/src/stores/**"]', (rules / "spa-stores.md").read_text())
        architecture = (rules / "project-architecture.md").read_text()
        self.assertIn("alwaysApply: true", architecture)
        self.assertIn("primevue ^4.4.1", architecture)
        self.assertTrue((self.root / ".omp/skills/laravel-best-practices/SKILL.md").is_file())
        manifest = json.loads((self.root / ".omp" / project_boost.MANIFEST).read_text())
        self.assertEqual((manifest["boost_version"], manifest["models"]), ("v2.10.3", [ScriptedLLM.last_planner_label]))
        self.assertIn("rules/spa-stores.md", manifest["files"])


class BoostGuardTests(_StateCase):
    def test_discovery_without_verdicts_is_incomplete_after_the_budget(self):
        llm = ScriptedLLM(lambda *_: "not json")
        verdicts, complete = project_boost._discover(
            llm, "system", "orientation", "A. X", "1. Y", project_boost._ReadOnlyTools(self.root), lambda _: None)
        self.assertEqual((verdicts, complete, len(llm.calls)), ([], False, 9))
        self.assertIn("not valid JSON", llm.calls[1][2][-1]["content"])
        self.assertTrue(llm.calls[-1][2][-1]["content"].startswith("Turn budget exhausted."))

    def test_missing_boost_is_installed_with_network(self):
        _touch(self.root / "backend/artisan")
        runner = FakeBoostRunner()
        with patch.object(project_boost, "DockerRunner", lambda: runner), \
                self.assertRaisesRegex(BoostError, "infer-conventions skill not installed"):
            project_boost._ensure_boost(self.root / "backend")
        (script, network), = runner.calls
        self.assertTrue(network)
        self.assertIn("composer require --dev laravel/boost", script)
        self.assertIn("php artisan boost:install --no-interaction", script)

    def test_second_concurrent_run_is_refused(self):
        project_layout.STATE_DIR.mkdir(parents=True)
        with open(project_layout.STATE_DIR / "boost.lock", "w") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            record = {"layout": {"backend": None, "frontend": None}}
            with self.assertRaisesRegex(BoostError, "another nesti /boost is running"):
                project_boost.run_boost(self.root, record, StubLLM())


if __name__ == "__main__":
    unittest.main()
