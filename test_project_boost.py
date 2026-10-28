"""Offline Boost orchestration, evidence, ownership and crash-recovery regressions."""
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

import project_boost as boost
from project_architecture import collect_architecture, collect_inventory, load_project_rules


# Rendered checklist shape, not a substitute for the live official-package smoke.
_RANGES = [(1, 4), (5, 10), (11, 12), (13, 20), (21, 27), (28, 32),
           (33, 37), (38, 42), (43, 46), (47, 49)]


def _checklist(packages=None):
    packages = packages or {}
    omitted = ({30} if "livewire/livewire" not in packages else set())
    omitted |= ({31} if not {"livewire/flux", "livewire/flux-pro"}.intersection(packages) else set())
    return "\n".join(f"## {group}. Group\n\n" + "\n".join(
        f"{number}. Dimension" for number in range(start, end + 1) if number not in omitted)
        for group, (start, end) in zip("ABCDEFGHIJ", _RANGES))


class Model:
    def __init__(self, files, pattern=True, application_root=""):
        self.files = files
        self.pattern = pattern
        self.application_root = application_root
        self.groups = []
        self.contexts = []

    def generate_plan(self, system, user, messages=None):
        payload = json.loads(user)
        if "approved_official_rules" in payload:
            return json.dumps({"rules": [
                {"source_rule": item["source_rule"], "description": item["title"],
                 "globs": [item["glob"]], "body": item["note"]}
                for item in payload["approved_official_rules"]]})
        self.groups.append(payload["group"])
        self.contexts.append(payload["context"])
        verdicts = [{"dimension": dimension, "verdict": "no_signal",
                     "reason": "Insufficient examples for a nondefault convention", "evidence": []}
                    for dimension in payload["required_dimensions"]]
        if self.pattern and payload["group"] == "E":
            item = next(item for item in verdicts if item["dimension"] == "26")
            item.update(verdict="pattern", reason="Three domain-scoped implementations",
                        glob=f"{self.application_root}app/Domains/Foo/**", title="Domain organization",
                        note=f"Keep Foo repositories and their contracts in {self.application_root}app/Domains/Foo.",
                        evidence=[{"path": path, "start_line": 1, "end_line": 1,
                                   "quote": self.files[path]["content"].splitlines()[0]}
                                  for path in self.files if path.startswith(f"{self.application_root}app/Domains/Foo/")])
        return json.dumps({"verdicts": verdicts})

    def last_planner_attribution(self):
        return {"provider": "fixture-consumer", "model": "actual-fixture-model", "billing": "subscription"}


class Bridge:
    def __init__(self):
        self.copied = {}
        self.operations = []

    def run_boost_install(self, workspace):
        root = Path(workspace)
        self.copied = {path: item["content"] for path, item in collect_inventory(workspace)["files"].items()}
        # Composer mutations are deliberately confined to the copy.
        (root / "composer.json").write_text('{"require-dev":{"laravel/boost":"2.10.3"}}')
        return True, "installed"

    def run_boost_bridge(self, workspace, operation):
        self.operations.append(operation)
        scratch = Path(workspace) / ".nesti-boost"
        scratch.mkdir(exist_ok=True)
        result = {"package_version": boost.BOOST_VERSION}
        if operation == "prepare":
            result.update(skill="Official workflow fixture", checklist=_checklist(), packages={})
        else:
            entries = json.loads((scratch / "record-input.json").read_text())
            result["records"] = [{"id": item["id"], "source_rule": ".ai/rules/foo.md",
                                  "content": item["note"]} for item in entries]
        (scratch / f"{operation}.json").write_text(json.dumps(result))
        return True, "logs are not JSON"


class BoostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nesti-boost-test-")
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root = base / "project"
        self.root.mkdir()
        self.state = base / "state"
        self.namespace = "a" * 64
        self.receipts = self.state / "projects" / self.namespace
        self.project = {"root": str(self.root), "namespace": self.namespace, "id": 42,
                        "path": "test/project", "application_root": "", "target_branch": "main"}
        for path, content in {
            "artisan": "<?php\n", "composer.json": '{"autoload":{"psr-4":{"Domain\\\\":"app/Domains/"}}}',
            "app/Domains/Foo/RepositoryContract.php": "<?php interface RepositoryContract {}\n",
            "app/Domains/Foo/Repository.php": "<?php class Repository implements RepositoryContract {}\n",
            "app/Domains/Foo/Http/Controllers/Example.php": "<?php class Example { public function __construct(RepositoryContract $repo) {} }\n",
            "resources/custom/main.ts": "createApp(Root).use(PrimeVue).mount('#root');\n",
            "README.md": "Human documentation\n", ".env": "PRODUCTION_SECRET=never-copy\n",
            "bootstrap/cache/config.php": "<?php return ['password'=>'never-copy'];\n",
            "vendor/library.php": "<?php // never-copy\n",
        }.items():
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)
        self.runner = Bridge()
        self.model = Model(collect_inventory(str(self.root))["files"])
        for patcher in (
            patch.dict(os.environ, {"NESTI_STATE_DIR": str(self.state)}),
            patch.object(boost, "inspect_project", return_value=self.project),
            patch("docker_runner.DockerRunner", return_value=self.runner),
            patch("llm_client.LLMClient", return_value=self.model),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_boost(self, force=True):
        return boost.boost_project(str(self.root), force=force)

    def receipt(self):
        return json.loads((self.receipts / "boost-receipt.json").read_text())

    def test_full_sweep_scoped_rule_receipt_and_secret_free_copy(self):
        composer = (self.root / "composer.json").read_bytes()
        result = self.run_boost(force=False)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.model.groups, list("ABCDEFGHIJ") + ["architecture", "Nesti Vue/PrimeVue"])
        self.assertEqual(self.runner.operations, ["prepare", "record"])
        self.assertNotIn(".env", self.runner.copied)
        self.assertNotIn("bootstrap/cache/config.php", self.runner.copied)
        self.assertNotIn("vendor/library.php", self.runner.copied)
        self.assertEqual((self.root / "composer.json").read_bytes(), composer)
        self.assertEqual((self.root / "README.md").read_text(), "Human documentation\n")
        self.assertEqual(len(result["generated"]), 1)
        path = result["generated"][0]
        receipt = self.receipt()
        self.assertEqual(receipt["conventions"][0]["generated_rule"], path)
        self.assertEqual(len(receipt["conventions"][0]["evidence"]), 3)
        self.assertIn("directory:app/Domains/Foo/Http/Controllers", receipt["required_groups"]["architecture"])
        manifest = json.loads((self.root / boost._MANIFEST).read_text())
        self.assertEqual(manifest["generated_rules"][path], boost._digest((self.root / path).read_bytes()))
        self.assertIn("app/Domains/Foo/**", (self.root / path).read_text())
        self.assertTrue(all(item["model"] == "actual-fixture-model" for item in result["attribution"]))
        self.assertEqual(stat.S_IMODE((self.receipts / "boost-receipt.json").stat().st_mode), 0o600)
        self.assertEqual((self.root / path).stat().st_uid, self.root.stat().st_uid)
        self.assertEqual(self.run_boost(force=False)["status"], "skipped")
        self.assertEqual(len(self.model.groups), 12)

    def test_split_project_publishes_at_container_and_executes_only_backend_copy(self):
        containing = self.root
        backend = containing / "api"
        backend.mkdir()
        for path in list(containing.iterdir()):
            if path != backend:
                path.rename(backend / path.name)
        spa = containing / "spa"
        spa.mkdir()
        (spa / "package.json").write_text('{"dependencies":{"vue":"^3","primevue":"^5"}}')
        (spa / "main.ts").write_text("createApp(Root).use(PrimeVue).mount('#app');\n")
        self.project.update(root=str(backend), project_root=str(containing),
                            git_root=str(containing), application_root="api", frontend_root="spa")
        inventory = collect_inventory(str(containing), application_root="api")
        self.model.files = inventory["files"]
        self.model.application_root = "api/"
        composer = (backend / "composer.json").read_bytes()
        original_files = {
            path.relative_to(containing).as_posix(): path.read_bytes()
            for path in containing.rglob("*") if path.is_file()
        }
        install = self.runner.run_boost_install
        workspaces = []

        def isolated_install(workspace):
            workspaces.append(Path(workspace))
            self.assertEqual(Path(workspace).name, "api")
            self.assertNotEqual(Path(workspace), backend)
            self.assertEqual((Path(workspace).parent / "spa/main.ts").read_bytes(), (spa / "main.ts").read_bytes())
            self.assertFalse((Path(workspace) / ".env").exists())
            self.assertFalse((Path(workspace) / "bootstrap/cache/config.php").exists())
            for name in (".claude/skills/boost/SKILL.md", ".ai/rules/boost.md", "boost.json", ".mcp.json"):
                artifact = Path(workspace) / name
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("Disposable Boost artifact")
            return install(workspace)

        with patch.object(self.runner, "run_boost_install", side_effect=isolated_install), \
                patch.object(self.runner, "run_boost_bridge", wraps=self.runner.run_boost_bridge) as bridge:
            result = boost.boost_project(str(backend), force=True)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(all(Path(call.args[0]) == workspaces[0] for call in bridge.call_args_list))
        self.assertTrue((containing / boost._MANIFEST).is_file())
        self.assertFalse((backend / ".omp").exists())
        self.assertEqual((backend / "composer.json").read_bytes(), composer)
        published_files = {
            path.relative_to(containing).as_posix(): path.read_bytes()
            for path in containing.rglob("*") if path.is_file()
        }
        self.assertEqual(
            {name: data for name, data in published_files.items() if not name.startswith(".omp/")},
            original_files,
        )
        self.assertEqual(set(published_files) - set(original_files), {boost._MANIFEST, *result["generated"]})
        self.assertTrue(all(not path.parent.exists() for path in workspaces))
        rule = result["generated"][0]
        self.assertIn("api/app/Domains/Foo/**", (containing / rule).read_text())
        context = self.model.contexts[0]
        self.assertIn("spa/main.ts", {item["path"] for item in context["inventory"]})
        self.assertEqual(context["psr4"][0]["path"], "api/app/Domains")
        receipt = self.receipt()
        self.assertEqual(receipt["source_fingerprint"], inventory["fingerprint"])
        self.assertTrue(all(item["path"].startswith("api/") for item in receipt["conventions"][0]["evidence"]))
        snapshot = collect_architecture(str(backend), self.project)
        self.assertEqual(snapshot["stack"]["primevue"], "^5")
        self.assertTrue(snapshot["conventions"])
        with patch("project_context.project_namespace", return_value=self.namespace):
            rules = load_project_rules(str(containing), paths=["api/app/Domains/Foo/Repository.php"])
            self.assertTrue(rules[0]["selected"])
            (spa / "main.ts").write_text("createApp(Changed).mount('#app');\n")
            self.assertFalse(load_project_rules(str(containing), paths=["api/app/Domains/Foo/Repository.php"])[0]["selected"])
        self.assertTrue(collect_architecture(str(backend), self.project)["semantic_stale"])

    def test_nested_frontend_change_during_discovery_prevents_publication(self):
        backend = self.root / "api"
        backend.mkdir()
        for path in list(self.root.iterdir()):
            if path != backend:
                path.rename(backend / path.name)
        spa = self.root / "spa"
        spa.mkdir()
        (spa / "main.ts").write_text("createApp(Root).mount('#app');\n")
        self.project.update(root=str(backend), project_root=str(self.root),
                            git_root=str(self.root), application_root="api", frontend_root="spa")
        self.model.files = collect_inventory(str(self.root))["files"]
        self.model.application_root = "api/"
        convert = boost._convert

        def changed_source(*args):
            rules = convert(*args)
            (spa / "main.ts").write_text("createApp(Changed).mount('#app');\n")
            return rules

        with patch.object(boost, "_convert", side_effect=changed_source):
            result = self.run_boost()
        self.assertEqual(result["status"], "conflicts")
        self.assertFalse((self.root / ".omp").exists())
        self.assertFalse((backend / ".omp").exists())

    def test_existing_omp_skips_but_manual_refresh_preserves_human_files(self):
        for path in (".omp/rules/human.md", ".omp/agents/custom.md", ".omp/mcp.json", ".ai/rules/human.md"):
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("Human-owned bytes\n")
        self.assertEqual(self.run_boost(force=False)["status"], "skipped")
        self.assertFalse(self.model.groups)
        self.assertEqual(self.run_boost()["status"], "completed")
        for path in (".omp/rules/human.md", ".omp/agents/custom.md", ".omp/mcp.json", ".ai/rules/human.md"):
            self.assertEqual((self.root / path).read_text(), "Human-owned bytes\n")

    def test_refresh_preserves_mode_and_removes_only_obsolete_owned_rules(self):
        path = self.run_boost()["generated"][0]
        (self.root / path).chmod(0o640)
        self.run_boost()
        self.assertEqual(stat.S_IMODE((self.root / path).stat().st_mode), 0o640)
        self.model.pattern = False
        result = self.run_boost()
        self.assertEqual(result["removed"], [path])
        self.assertFalse((self.root / path).exists())
        self.assertEqual(self.receipt()["conventions"], [])

    def test_edited_or_unowned_rules_are_never_overwritten(self):
        path = self.run_boost()["generated"][0]
        (self.root / path).write_text("Human edit")
        previous = (self.root / boost._MANIFEST).read_bytes()
        self.assertEqual(self.run_boost()["status"], "conflicts")
        self.assertEqual((self.root / path).read_text(), "Human edit")
        self.assertEqual((self.root / boost._MANIFEST).read_bytes(), previous)
        (self.root / boost._MANIFEST).unlink()
        self.assertEqual(self.run_boost()["status"], "conflicts")
        self.assertEqual((self.root / path).read_text(), "Human edit")

    def test_symlink_or_file_omp_is_not_initialized(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (self.root / ".omp").symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.run_boost(force=False)["status"], "conflicts")
        self.assertEqual(list(outside.iterdir()), [])
        (self.root / ".omp").unlink()
        (self.root / ".omp").write_text("not a directory")
        with self.assertRaisesRegex(ValueError, "not a directory"):
            self.run_boost(force=False)
        self.assertFalse(self.model.groups)

    def test_failed_discovery_preserves_previous_generation_and_diagnostic_receipt(self):
        path = self.run_boost()["generated"][0]
        previous = (self.root / path).read_bytes()
        for failure in (RuntimeError("providers exhausted"), "not JSON", '{"verdicts":[]}'):
            with self.subTest(failure=str(failure)):
                with patch.object(self.model, "generate_plan", **(
                    {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
                )):
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.run_boost()
                self.assertEqual((self.root / path).read_bytes(), previous)
                self.assertEqual(self.receipt()["status"], "completed")
                self.assertEqual(json.loads((self.receipts / "boost-attempt.json").read_text())["status"], "incomplete")

    def test_install_failure_never_initializes_target(self):
        with patch.object(self.runner, "run_boost_install", return_value=(False, "incompatible dependencies")):
            with self.assertRaisesRegex(RuntimeError, "incompatible dependencies"):
                self.run_boost(force=False)
        self.assertFalse((self.root / ".omp").exists())
        self.assertFalse(self.model.groups)

    def test_crash_recovery_completes_manifest_last(self):
        original = boost._atomic
        order = []

        def interrupt(path, data, owner, mode=0o600, **kwargs):
            order.append(path.name)
            if path.name == "architecture.json":
                raise OSError("simulated publication interruption")
            return original(path, data, owner, mode, **kwargs)

        with patch.object(boost, "_atomic", side_effect=interrupt):
            with self.assertRaisesRegex(OSError, "interruption"):
                self.run_boost()
        self.assertFalse((self.root / boost._MANIFEST).exists())
        self.assertTrue((self.receipts / "boost-journal.json").exists())
        self.assertEqual(self.run_boost(force=False)["status"], "skipped")
        self.assertEqual(self.receipt()["status"], "completed")
        self.assertFalse((self.receipts / "boost-journal.json").exists())
        self.assertTrue((self.root / boost._MANIFEST).exists())

    def test_interrupted_generation_rolls_back_if_source_changed(self):
        original = boost._atomic

        def interrupt(path, data, owner, mode=0o600, **kwargs):
            if path.name == "architecture.json":
                raise OSError("interrupted")
            return original(path, data, owner, mode, **kwargs)

        with patch.object(boost, "_atomic", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.run_boost()
        (self.root / "artisan").write_text("<?php // changed\n")
        self.assertFalse(boost._recover(self.root, self.receipts))
        self.assertFalse((self.root / ".omp").exists())
        self.assertFalse((self.receipts / "boost-receipt.json").exists())

    def test_interrupted_generation_cannot_overwrite_a_user_edit(self):
        original = boost._atomic

        def interrupt(path, data, owner, mode=0o600, **kwargs):
            if path.name == "architecture.json":
                raise OSError("interrupted")
            return original(path, data, owner, mode, **kwargs)

        with patch.object(boost, "_atomic", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.run_boost()
        file = next((self.root / ".omp/rules").glob("nesti-boost-*.md"))
        file.write_text("Human edit during interruption")
        self.assertEqual(self.run_boost(force=False)["status"], "conflicts")
        self.assertEqual(file.read_text(), "Human edit during interruption")
        self.assertFalse((self.root / boost._MANIFEST).exists())

    def test_source_change_before_publication_aborts_without_success(self):
        original = boost._publish

        def change_source(*args):
            (self.root / "artisan").write_text("<?php // concurrent change\n")
            return original(*args)

        with patch.object(boost, "_publish", side_effect=change_source):
            self.assertEqual(self.run_boost()["status"], "conflicts")
        self.assertFalse((self.root / ".omp").exists())

    def test_source_change_during_publication_restores_previous_receipt_and_rules(self):
        path = self.run_boost()["generated"][0]
        previous_rule = (self.root / path).read_bytes()
        previous_receipt = (self.receipts / "boost-receipt.json").read_bytes()
        previous_manifest = (self.root / boost._MANIFEST).read_bytes()
        self.model.pattern = False
        original = boost._atomic
        changed = False

        def change_source(destination, data, owner, mode=0o600, **kwargs):
            nonlocal changed
            result = original(destination, data, owner, mode, **kwargs)
            if destination.name == "architecture.json" and not changed:
                changed = True
                (self.root / "artisan").write_text("<?php // concurrent source change\n")
            return result

        with patch.object(boost, "_atomic", side_effect=change_source):
            self.assertEqual(self.run_boost()["status"], "conflicts")
        self.assertEqual((self.root / path).read_bytes(), previous_rule)
        self.assertEqual((self.receipts / "boost-receipt.json").read_bytes(), previous_receipt)
        self.assertEqual((self.root / boost._MANIFEST).read_bytes(), previous_manifest)
        self.assertFalse((self.receipts / "boost-journal.json").exists())


class EvidenceTests(unittest.TestCase):
    def test_all_applicable_dimensions_and_conditional_package_dimensions(self):
        for packages, count in (({}, 47), ({"livewire/livewire": "4", "livewire/flux": "2"}, 49)):
            groups = boost._groups(_checklist(packages), {}, packages)
            self.assertEqual(sum(len(items) for _, items in groups[:10]), count)
            self.assertEqual(groups[-1][1], boost._FRONTEND)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            boost._groups(_checklist(), {}, {"livewire/livewire": "4"})

    def test_evidence_boundary_and_budget(self):
        files = {"app/Example.php": {"content": "x" * 30000, "hash": "a" * 64, "kind": "source"}}
        result = boost._exchange([{"op": "read", "path": "app/Example.php", "start_line": 1, "end_line": 1}], files)
        self.assertEqual(len(result[0]["content"]), 24000)
        self.assertEqual(result[0]["omitted_characters"], 6000)
        for request in ({"op": "read", "path": "../secret", "start_line": 1, "end_line": 1},
                        {"op": "read", "path": ".env", "start_line": 1, "end_line": 1},
                        {"op": "bash", "path": "app"}):
            with self.assertRaises(ValueError):
                boost._exchange([request], files)
        for cite in ({"path": "app/Example.php", "start_line": 1, "end_line": 1, "quote": "invented"},
                     {"path": "app/Example.php", "start_line": 0, "end_line": 1, "quote": "x"}):
            with self.assertRaises(ValueError):
                boost._evidence([cite], files)

    def test_read_range_can_reach_eof_without_weakening_citations(self):
        files = {"app/Example.php": {"content": "<?php\nfinal class Example {}\n", "hash": "a" * 64, "kind": "source"}}
        result = boost._exchange([
            {"op": "read", "path": "app/Example.php", "start_line": 1, "end_line": 200},
            {"op": "read", "path": "app/Example.php", "start_line": 3, "end_line": 200},
        ], files)
        self.assertEqual(result[0]["content"], "<?php\nfinal class Example {}")
        self.assertEqual(result[0]["end_line"], 2)
        self.assertEqual(result[0]["total_lines"], 2)
        self.assertTrue(result[0]["eof"])
        self.assertEqual(result[1]["content"], "")
        with self.assertRaises(ValueError):
            boost._evidence([{"path": "app/Example.php", "start_line": 1, "end_line": 200,
                              "quote": "<?php\nfinal class Example {}"}], files)

    def test_two_examples_cannot_become_a_pattern_and_conflicts_are_not_candidates(self):
        files = {f"app/{index}.php": {"content": "<?php", "hash": "a" * 64, "kind": "source"} for index in range(2)}
        evidence = [{"path": path, "start_line": 1, "end_line": 1, "quote": "<?php"} for path in files]
        entry = {"dimension": "1", "verdict": "pattern", "reason": "observed", "evidence": evidence,
                 "glob": "app/**", "title": "Pattern", "note": "Follow observed form."}
        with self.assertRaisesRegex(ValueError, "three distinct"):
            boost._verdicts([entry], ["1"], files)
        entry["verdict"] = "conflict"
        self.assertNotIn("note", boost._verdicts([entry], ["1"], files)[0])
        entry["verdict"] = "already_recorded"
        with self.assertRaisesRegex(ValueError, "human rule"):
            boost._verdicts([entry], ["1"], files)

    def test_globstar_covers_direct_children_and_requires_three_scoped_examples(self):
        paths = ["ui/components/Orders.vue", "ui/components/Invoices.vue",
                 "ui/components/nested/Payments.vue", "ui/main.js"]
        files = {path: {"content": "source", "hash": "a" * 64, "kind": "source"} for path in paths}
        evidence = [{"path": path, "start_line": 1, "end_line": 1, "quote": "source"} for path in paths]
        entry = {"dimension": "28", "verdict": "pattern", "reason": "observed",
                 "evidence": evidence, "glob": "ui/components/**/*.vue",
                 "title": "Vue location", "note": "Place components under ui/components."}
        self.assertEqual(boost._verdicts([entry], ["28"], files)[0]["glob"], entry["glob"])
        entry["evidence"] = evidence[1:]
        with self.assertRaisesRegex(ValueError, "three distinct"):
            boost._verdicts([entry], ["28"], files)

    def test_exchange_exhaustion_is_not_a_completed_discovery(self):
        model = SimpleNamespace(generate_plan=lambda *a, **k: '{"request":[{"op":"list","path":""}]}',
                                last_planner_attribution=lambda: {"model": "fixture"})
        receipt = {"calls": [], "project": {}}
        with self.assertRaisesRegex(ValueError, "eight exchanges"):
            boost._discover(model, {"skill": "workflow", "checklist": _checklist(), "packages": {}},
                            {"files": {}, "psr4": [], "warnings": []}, receipt, {})
        self.assertEqual(len(receipt["calls"]), 8)

    def test_conversion_rejects_invented_source_glob_or_convention(self):
        candidate = {"id": "a" * 24, "dimension": "26", "glob": "app/Domains/**",
                     "title": "Domain layout", "note": "Keep domain classes together."}
        records = [{"id": candidate["id"], "source_rule": ".ai/rules/domains.md", "content": candidate["note"]}]
        converted = {"source_rule": records[0]["source_rule"], "description": "Domain layout",
                     "globs": [candidate["glob"]], "body": candidate["note"]}
        for change in ({"source_rule": ".ai/rules/invented.md"}, {"globs": ["../outside/**"]},
                       {"body": "Adopt a new architecture."}, {"description": ""}):
            model = SimpleNamespace(
                generate_plan=lambda *a, **k: json.dumps({"rules": [{**converted, **change}]}),
                last_planner_attribution=lambda: {"model": "fixture"},
            )
            with self.assertRaises(ValueError):
                boost._convert(model, records, [candidate], {"calls": []})


class SandboxTests(unittest.TestCase):
    def test_boost_install_and_offline_bridge_preserve_lifecycle(self):
        from docker_runner import DockerRunner
        runner = DockerRunner.__new__(DockerRunner)
        runner.client = Mock()
        runner.image, runner.workdir = "nesti-sandbox-php", "/app"
        runner.timeout, runner.bootstrap_timeout = 30, 60
        container = runner.client.containers.run.return_value
        container.wait.return_value = {"StatusCode": 0}
        container.logs.return_value = b"ok"
        self.assertTrue(runner.run_boost_install("/tmp/fixture")[0])
        install = runner.client.containers.run.call_args.kwargs
        self.assertFalse(install["network_disabled"])
        self.assertIn("laravel/boost:2.10.3", install["command"][-1])
        self.assertIn("--no-scripts --no-plugins", install["command"][-1])
        container.wait.assert_called_with(timeout=60)
        self.assertTrue(runner.run_boost_bridge("/tmp/fixture", "prepare")[0])
        self.assertTrue(runner.client.containers.run.call_args.kwargs["network_disabled"])
        container.wait.assert_called_with(timeout=30)
        container.wait.side_effect = requests.exceptions.ReadTimeout()
        self.assertFalse(runner.run_boost_bridge("/tmp/fixture", "record")[0])
        self.assertEqual(container.remove.call_count, 3)
        container.remove.assert_called_with(force=True)
        with self.assertRaises(ValueError):
            runner.run_boost_bridge("/tmp/fixture", "prepare; touch unsafe")


if __name__ == "__main__":
    unittest.main()
