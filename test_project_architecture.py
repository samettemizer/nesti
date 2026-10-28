"""Offline project identity, evidence and rule-boundary regressions."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git import Actor, Repo

from project_architecture import (
    _read_bytes, collect_architecture, collect_inventory, format_project_context,
    inventory_listing, load_project_rules,
)
from project_context import configured_project_root, inspect_project, project_namespace


class ProjectFactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nesti-facts-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo" / "backend"
        self.root.mkdir(parents=True)
        self.state = self.base / "state"
        environment = patch.dict(os.environ, {
            "NESTI_PROJECT_PATH": str(self.root), "NESTI_STATE_DIR": str(self.state),
            "GITLAB_URL": "https://gitlab.invalid", "GITLAB_PROJECT_PATH": "Group/App",
            "GITLAB_TARGET_BRANCH": "main", "GITLAB_TOKEN": "fixture-only",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.put("artisan", "<?php // fixture, never executed\n")
        self.put("composer.json", json.dumps({
            "require": {"laravel/framework": "^13.0"},
            "autoload": {"psr-4": {"Domain\\": "src/Domain/", "App\\": "app/"}},
            "autoload-dev": {"psr-4": {"Tests\\": "checks/"}},
        }))
        for name in ("Alpha", "Beta", "Gamma"):
            self.put(f"src/Domain/{name}/Repository.php", f"<?php\nnamespace Domain\\{name};\nclass Repository {{}}\n")
        self.put("app/Domains/Foo/Http/Controllers/Show.php", "<?php\nclass Show {}\n")
        self.put("checks/Feature/DomainTest.php", "<?php\nclass DomainTest {}\n")
        self.project = {"id": 7, "namespace": project_namespace(), "path": "Group/App",
                        "target_branch": "main", "application_root": "backend",
                        "root": str(self.root), "git_root": str(self.root.parent)}

    def put(self, relative: str, content: str | bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)
        return path

    def receipt(self, value: dict) -> Path:
        path = self.state / "projects" / self.project["namespace"] / "boost-receipt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def convention(self) -> dict:
        files = collect_inventory(str(self.root))["files"]
        evidence = [{"path": path, "start_line": 1, "end_line": 3,
                     "quote": item["content"].rstrip("\n"), "hash": item["hash"]}
                    for path, item in files.items() if path.startswith("src/Domain/")]
        return {"dimension": "repositories", "glob": "src/Domain/**/*.php",
                "title": "Domain repositories", "note": "Keep repositories in each domain.",
                "evidence": evidence}

    def managed_rule(self) -> tuple[str, dict]:
        path = ".omp/rules/nesti-boost-example.md"
        rule = self.put(path, "---\ndescription: Domain repositories\nglobs: ['src/Domain/**/*.php']\nalwaysApply: false\n---\nKeep repositories in each domain.\n")
        fingerprint = collect_inventory(str(self.root))["fingerprint"]
        self.put(".omp/nesti-boost.json", json.dumps({
            "schema_version": 1, "status": "completed", "source_fingerprint": fingerprint,
            "snapshot_identity": "a" * 64,
            "generated_rules": {path: hashlib.sha256(rule.read_bytes()).hexdigest()},
        }))
        receipt = {"schema_version": 1, "status": "completed", "source_fingerprint": fingerprint,
                   "snapshot_identity": "a" * 64,
                   "conventions": [{**self.convention(), "generated_rule": path}]}
        self.receipt(receipt)
        return path, receipt

    def test_namespace_normalizes_identity_without_credentials_or_network(self) -> None:
        expected = hashlib.sha256(b'["https://gitlab.invalid","Group/App"]').hexdigest()
        self.assertEqual(project_namespace(), expected)
        with patch.dict(os.environ, {"GITLAB_URL": "https://user:secret@GITLAB.invalid/", "GITLAB_PROJECT_PATH": "Group/App.git/"}):
            self.assertEqual(project_namespace(), expected)
        with patch.dict(os.environ, {"GITLAB_PROJECT_PATH": "group/app"}):
            self.assertNotEqual(project_namespace(), expected)
        with patch.dict(os.environ, {"GITLAB_PROJECT_PATH": ""}):
            self.assertEqual(project_namespace(), "")
        for path in ("../App", "Group//App", "Group/App?token=x", "Group\\App"):
            with self.subTest(path=path), patch.dict(os.environ, {"GITLAB_PROJECT_PATH": path}):
                with self.assertRaises(ValueError):
                    project_namespace()

    def test_configured_root_never_falls_back_and_rejects_symlink_components(self) -> None:
        self.assertEqual(configured_project_root(), self.root)
        link = self.base / "linked"
        link.symlink_to(self.root.parent, target_is_directory=True)
        for value in ("", "relative", str(self.base / "missing"), str(link / "backend"), str(self.root / "composer.json")):
            with self.subTest(value=value), patch.dict(os.environ, {"NESTI_PROJECT_PATH": value}):
                with self.assertRaises(ValueError):
                    configured_project_root()
        (self.root / "artisan").unlink()
        with self.assertRaisesRegex(ValueError, "artisan"):
            configured_project_root()

    def test_identity_verifies_parent_git_root_remote_and_numeric_project(self) -> None:
        repo = Repo.init(self.root.parent)
        repo.create_remote("origin", "git@gitlab.invalid:Group/App.git")
        repo.index.add([str(self.root / "composer.json"), str(self.root / "artisan")])
        author = Actor("Fixture", "fixture@example.invalid")
        commit = repo.index.commit("fixture", author=author, committer=author)
        remote = {"id": 7, "path_with_namespace": "Group/App", "web_url": "https://gitlab.invalid/Group/App", "default_branch": "main"}
        with patch("gitlab_issues_client.GitLabIssuesClient.get_project", return_value=remote) as lookup:
            facts = inspect_project(str(self.root))
            self.assertEqual(facts["application_root"], "backend")
            self.assertEqual(facts["git_root"], str(self.root.parent))
            self.assertEqual(facts["source"]["head"], commit.hexsha)
            self.assertTrue(facts["source"]["dirty"])
            self.assertNotIn("git@", json.dumps(facts))
            lookup.assert_called_once_with()
            repo.git.checkout("--detach", commit.hexsha)
            self.assertIsNone(inspect_project(str(self.root))["source"]["branch"])
            repo.remotes.origin.set_url("https://user:secret@gitlab.invalid/Group/App.git")
            self.assertEqual(inspect_project(str(self.root))["id"], 7)
            repo.remotes.origin.set_url("git@gitlab.invalid:Other/App.git")
            lookup.reset_mock()
            with self.assertRaisesRegex(ValueError, "origin does not match"):
                inspect_project(str(self.root))
            lookup.assert_not_called()
        repo.remotes.origin.set_url("git@gitlab.invalid:Group/App.git")
        for wrong in ({**remote, "id": True}, {**remote, "path_with_namespace": "Other/App"},
                      {**remote, "web_url": "https://other.invalid/Group/App"}):
            with self.subTest(remote=wrong), patch("gitlab_issues_client.GitLabIssuesClient.get_project", return_value=wrong):
                with self.assertRaises(ValueError):
                    inspect_project(str(self.root))

    def test_inventory_covers_custom_psr4_and_reports_external_missing_mappings(self) -> None:
        composer = json.loads((self.root / "composer.json").read_text())
        composer["autoload"]["psr-4"].update({"External\\": "../outside", "Missing\\": "absent/", "Link\\": "linked/"})
        self.put("composer.json", json.dumps(composer))
        (self.root / "linked").symlink_to(self.base, target_is_directory=True)
        inventory = collect_inventory(str(self.root))
        self.assertIn("app/Domains/Foo/Http/Controllers/Show.php", inventory["files"])
        self.assertIn("src/Domain/Alpha/Repository.php", inventory["files"])
        mappings = {item["namespace"]: item for item in inventory["psr4"]}
        self.assertTrue(mappings["Domain\\"]["resolved"])
        self.assertTrue(mappings["Tests\\"]["dev"])
        for name in ("External\\", "Missing\\", "Link\\"):
            self.assertFalse(mappings[name]["resolved"])
        self.assertEqual(len(inventory["unresolved"]), 3)
        self.assertEqual(inventory_listing(self.root), sorted(inventory["files"]))

    def test_inventory_prunes_secrets_dependencies_binary_and_generated_artifacts(self) -> None:
        before = collect_inventory(str(self.root))["fingerprint"]
        omitted = [".env", ".env.example", "config/credentials.json", "auth.json", "config/private-key.php",
                   "vendor/Foo.php", "node_modules/View.vue", "storage/framework/cache.php", "bootstrap/cache/config.php",
                   ".idea/config.xml", ".omp/rules/nesti-boost-hidden.md", ".omp/agents/custom.md", "database/data.sqlite"]
        for path in omitted:
            self.put(path, "secret")
        self.put("binary.php", b"\x00bad")
        self.put("invalid.php", b"\xff")
        self.put("credential-url.json", '{"url":"https://user:password@example.invalid"}')
        self.put("key.php", "-----BEGIN RSA PRIVATE KEY-----")
        self.put("control.js", b"bad\x01")
        (self.root / "escape.php").symlink_to(self.root / "artisan")
        inventory = collect_inventory(str(self.root))
        self.assertEqual(inventory["fingerprint"], before)
        self.assertFalse(set(omitted).intersection(inventory["files"]))
        self.assertTrue(inventory["warnings"])
        self.assertNotIn("password", json.dumps(inventory))
        self.put(".omp/rules/human.md", "---\ndescription: human\n---\nKeep custom paths.\n")
        self.assertNotEqual(collect_inventory(str(self.root))["fingerprint"], before)

    def test_safe_reader_refuses_traversal_and_symlink_at_read_time(self) -> None:
        (self.root / "link").symlink_to(self.root / "src", target_is_directory=True)
        for path in ("../outside.php", "/etc/passwd", "link/Domain/Alpha/Repository.php"):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                _read_bytes(self.root, path)
        with self.assertRaisesRegex(ValueError, "byte limit"):
            _read_bytes(self.root, "composer.json", limit=3)

    def test_snapshot_is_stable_read_only_and_backend_only(self) -> None:
        first = collect_architecture(str(self.root), self.project)
        second = collect_architecture(str(self.root), self.project)
        first.pop("generated_at")
        second.pop("generated_at")
        self.assertEqual(first, second)
        self.assertFalse(self.state.exists())
        self.assertEqual(first["stack"], {"laravel": "^13.0", "vue": None, "primevue": None})
        self.assertIn("backend/src/Domain/Alpha", first["directories"])
        self.assertEqual(first["conventions"], [])
        self.assertTrue(all(edge["kind"] == "contains" for edge in first["edges"]))
        self.assertIn("structural view", " ".join(first["warnings"]))
        self.assertNotIn("content", first["files"][0])
        self.put("src/Domain/Alpha/Repository.php", "<?php // dirty update\n")
        changed = collect_architecture(str(self.root), self.project)
        self.assertNotEqual(first["source"]["fingerprint"], changed["source"]["fingerprint"])
        self.assertEqual(first["nodes"], changed["nodes"])

    def test_split_snapshot_uses_containing_root_coordinates_and_nested_pruning(self) -> None:
        containing = self.root.parent
        spa = containing / "spa"
        spa.mkdir()
        (spa / "package.json").write_text('{"dependencies":{"vue":"^3","primevue":"^5"}}')
        (spa / "package-lock.json").write_text('{"packages":{"node_modules/vue":{"version":"3.5.0"}}}')
        (spa / "main.ts").write_text("createApp(Root).use(PrimeVue).mount('#app');\n")
        project = {**self.project, "project_root": str(containing), "git_root": str(containing.parent),
                   "application_root": "repo/backend", "frontend_root": "repo/spa"}
        with patch.dict(os.environ, {"NESTI_PROJECT_PATH": str(containing)}):
            snapshot = collect_architecture(str(self.root), project)
        self.assertEqual(snapshot["stack"], {"laravel": "^13.0", "vue": "3.5.0", "primevue": "^5"})
        self.assertIn("backend/src/Domain/Alpha", snapshot["directories"])
        self.assertIn("spa", snapshot["directories"])
        self.assertNotIn("repo/backend/backend", snapshot["directories"])
        mappings = {item["namespace"]: item for item in snapshot["psr4"]}
        self.assertEqual(mappings["Domain\\"]["path"], "backend/src/Domain")
        self.assertTrue(mappings["Domain\\"]["resolved"])
        self.assertTrue(any(item["path"] == "spa/main.ts" for item in snapshot["frontend"]))
        inventory = collect_inventory(str(containing), application_root="backend")
        for path in (".env", "storage/framework/cache.php", "bootstrap/cache/config.php",
                     ".omp/rules/nesti-boost-hidden.md", ".omp/agents/custom.md",
                     ".omp/nesti-boost.json", ".ai/nesti-boost-skills/metadata.json",
                     "vendor/config.php", "config/credentials.json"):
            self.put(path, "secret")
        (spa / "node_modules").mkdir()
        (spa / "node_modules/ignored.js").write_text("secret")
        (spa / "linked.php").symlink_to(self.root / "artisan")
        after = collect_inventory(str(containing), application_root="backend")
        self.assertEqual(after["fingerprint"], inventory["fingerprint"])
        self.assertNotIn("secret", json.dumps(after))
        self.assertFalse(self.state.exists())
        for application in ("../backend", "/backend", "backend\\outside"):
            with self.subTest(application=application), self.assertRaises(ValueError):
                collect_inventory(str(containing), application_root=application)

    def test_frontend_records_custom_entries_registrations_aliases_and_tests(self) -> None:
        self.put("package.json", json.dumps({"dependencies": {"vue": "^3", "primevue": "^5"}}))
        self.put("package-lock.json", json.dumps({"packages": {"node_modules/vue": {"version": "3.5.0"}, "node_modules/primevue": {"version": "5.0.0"}}}))
        self.put("ui/start.ts", "import Root from './Screen.vue';\nconst app = createApp(Root);\napp.use(PrimeVue, {theme: {preset: Aura}});\napp.component('custom-screen', Root);\napp.mount('#app');\nimport(moduleName);\n")
        self.put("ui/Screen.vue", "<template><RouterView /></template>\n")
        self.put("ui/state.ts", "export const useStore = defineStore('store', {});\n")
        self.put("ui/net.ts", "export const load = () => fetch('/api/items');\n")
        self.put("ui/useItems.ts", "export function useItems() {}\n")
        self.put("ui/checks/custom.spec.ts", "test('shows items', () => {});\n")
        self.put("vite.config.ts", "export default {resolve: {alias: {'@ui': '/ui'}}};\n")
        self.put("views/root.blade.php", "@vite('ui/start.ts')\n<div id='app'><custom-screen></custom-screen></div>\n")
        snapshot = collect_architecture(str(self.root), self.project)
        self.assertEqual(snapshot["stack"]["primevue"], "5.0.0")
        kinds = {item["kind"] for item in snapshot["frontend"]}
        self.assertTrue({"entry_mount", "root_component", "plugin_theme", "component_registration", "store", "router", "api_client", "alias", "composable", "test", "blade_entry"} <= kinds)
        self.assertTrue(any("Dynamic frontend" in item for item in snapshot["unresolved"]))
        self.assertTrue(all(item["quote"] and item["hash"] for item in snapshot["frontend"]))

    def test_semantic_claims_need_current_exact_evidence(self) -> None:
        snapshot = collect_architecture(str(self.root), self.project)
        convention = self.convention()
        edge = {"from": snapshot["nodes"][0]["id"], "to": snapshot["nodes"][1]["id"],
                "kind": "module", "evidence": convention["evidence"][:1]}
        receipt = {"schema_version": 1, "status": "completed", "source_fingerprint": snapshot["source"]["fingerprint"],
                   "snapshot_identity": "a" * 64,
                   "conventions": [convention], "edges": [edge]}
        self.receipt(receipt)
        self.put(".omp/nesti-boost.json", json.dumps({
            "schema_version": 1, "status": "completed", "snapshot_identity": "a" * 64,
            "source_fingerprint": receipt["source_fingerprint"], "generated_rules": {},
        }))
        fresh = collect_architecture(str(self.root), self.project)
        self.assertTrue(fresh["conventions"][0]["inferred"])
        self.assertTrue(any(item["kind"] == "inferred" for item in fresh["edges"]))
        receipt["conventions"][0]["evidence"][0]["quote"] = "invented"
        self.receipt(receipt)
        invalid = collect_architecture(str(self.root), self.project)
        self.assertEqual(invalid["conventions"], [])
        self.assertTrue(invalid["semantic_stale"])
        self.put("src/Domain/Alpha/Repository.php", "<?php changed\n")
        stale = collect_architecture(str(self.root), self.project)
        self.assertEqual(stale["conventions"], [])
        self.assertTrue(all(item["kind"] == "contains" for item in stale["edges"]))
        self.assertEqual(stale["nodes"], fresh["nodes"])

    def test_rules_parse_yaml_select_paths_and_preserve_complete_bodies(self) -> None:
        body = "\nKeep exact whitespace.  \n  Indented instruction.\n"
        self.put(".omp/rules/custom.mdc", "---\ndescription: >\n  Domain repository conventions\nglobs:\n  - 'src/**/*.{php,vue}'\nalwaysApply: false\n---\n" + body)
        self.put(".omp/rules/always.md", "---\ndescription: General safety\nalwaysApply: true\n---\nNever destroy data.\n")
        self.put(".omp/rules/disabled.md", "---\ndescription: Disabled\nenabled: false\n---\nIgnored.\n")
        self.put(".omp/rules/broken.md", "---\ndescription: Broken\nalwaysApply: 'yes'\n---\nIgnored.\n")
        rules = {item["path"]: item for item in load_project_rules(str(self.root), paths=["src/Domain/Alpha/Repository.php"])}
        self.assertEqual(rules[".omp/rules/custom.mdc"]["body"], body)
        self.assertTrue(rules[".omp/rules/custom.mdc"]["selected"])
        self.assertTrue(rules[".omp/rules/always.md"]["selected"])
        self.assertNotIn(".omp/rules/disabled.md", rules)
        self.assertTrue(rules[".omp/rules/broken.md"]["omission"])
        by_text = load_project_rules(str(self.root), "repository conventions")
        self.assertTrue(next(item for item in by_text if item["path"].endswith("custom.mdc"))["selected"])
        self.assertFalse(next(item for item in load_project_rules(str(self.root), paths=["elsewhere/Foo.php"]) if item["path"].endswith("custom.mdc"))["selected"])

    def test_generated_rule_requires_owned_bytes_completed_receipt_and_three_examples(self) -> None:
        path, receipt = self.managed_rule()
        def rule() -> dict:
            return next(item for item in load_project_rules(str(self.root), "Domain repositories") if item["path"] == path)
        self.assertTrue(rule()["selected"])
        for changed in ({**receipt, "status": "incomplete"}, {**receipt, "conventions": []},
                        {**receipt, "conventions": [{**receipt["conventions"][0], "evidence": receipt["conventions"][0]["evidence"][:2]}]}):
            with self.subTest(receipt=changed):
                self.receipt(changed)
                self.assertFalse(rule()["selected"])
                self.assertTrue(rule()["omission"])
        self.receipt(receipt)
        self.put(path, (self.root / path).read_text() + "User edit.\n")
        self.assertFalse(rule()["selected"])

    def test_external_generated_rules_are_validated_against_clean_clone(self) -> None:
        path, _ = self.managed_rule()
        clone = self.base / "clone"
        shutil.copytree(self.root, clone)
        (clone / "src/Domain/Alpha/Repository.php").write_text("<?php clean target differs\n")
        rules = load_project_rules(str(self.root), "Domain repositories", evidence_repo_path=str(clone))
        generated = next(item for item in rules if item["path"] == path)
        self.assertFalse(generated["selected"])
        self.assertTrue(generated["omission"])

    def test_uncommitted_generation_is_not_exposed_to_concurrent_readers(self) -> None:
        path, receipt = self.managed_rule()
        receipt["snapshot_identity"] = "b" * 64
        self.receipt(receipt)
        snapshot = collect_architecture(str(self.root), self.project)
        self.assertEqual(snapshot["conventions"], [])
        self.assertTrue(snapshot["semantic_stale"])
        self.assertTrue(any("unpublished" in warning for warning in snapshot["warnings"]))
        rule = next(item for item in load_project_rules(str(self.root), "Domain repositories") if item["path"] == path)
        self.assertFalse(rule["selected"])
        manifest = json.loads((self.root / ".omp/nesti-boost.json").read_text())
        manifest["snapshot_identity"] = "b" * 64
        self.put(".omp/nesti-boost.json", json.dumps(manifest))
        self.assertTrue(collect_architecture(str(self.root), self.project)["conventions"])
        clone = self.base / "clean-clone"
        shutil.copytree(self.root, clone)
        shutil.rmtree(clone / ".omp")
        self.assertTrue(collect_architecture(str(clone), {**self.project, "root": str(clone)})["conventions"])

    def test_rule_budget_omits_whole_instruction_and_names_it(self) -> None:
        snapshot = collect_architecture(str(self.root), self.project)
        rules = [{"path": "small.md", "body": "Keep this complete.", "selected": True},
                 {"path": "large.md", "body": "NEVER-TRUNCATE" * 5000, "selected": True}]
        context = format_project_context(snapshot, rules)
        self.assertIn("Keep this complete.", context)
        self.assertIn("Complete body omitted due to instruction budget: large.md", context)
        self.assertNotIn("NEVER-TRUNCATE", context)
        self.assertIn("human rules outrank inferred facts", context)




class RuleMetadataBoundaryTests(unittest.TestCase):
    def test_invalid_yaml_and_traversing_globs_are_named_omissions(self) -> None:
        metadata_cases = [
            "description: Invalid\nglobs: ['../outside/**']",
            "description: Invalid\nglobs: ['/absolute/**']",
            "description: Invalid\nglobs: [42]",
            "description: Invalid\nenabled: 'false'",
            "description: !!python/object:builtins.object {}",
            "description: " + "x" * 17000,
        ]
        with tempfile.TemporaryDirectory(prefix="nesti-rules-") as directory:
            root = Path(directory)
            rules = root / ".omp" / "rules"
            rules.mkdir(parents=True)
            for index, metadata in enumerate(metadata_cases):
                (rules / f"invalid-{index}.md").write_text(f"---\n{metadata}\n---\nNever execute me.\n")
            loaded = load_project_rules(str(root), "Invalid")
            self.assertEqual(len(loaded), len(metadata_cases))
            self.assertTrue(all(not item["selected"] and item["omission"] and not item["body"] for item in loaded))


if __name__ == "__main__":
    unittest.main()
