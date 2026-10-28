"""Offline project-layout selection, trust-boundary and consumer-only regressions."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from git import Repo

import llm_client
import project_context as context


class ProjectLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="nesti-layout-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.repo = Repo.init(self.root)
        self.repo.create_remote("origin", "git@gitlab.invalid:Group/App.git")
        self.backend = "services/orders"
        self.frontend = "clients/browser"
        self.put(f"{self.backend}/artisan", "<?php // source must not be sent")
        self.put(f"{self.backend}/composer.json", json.dumps({"require": {"laravel/framework": "^13.0"}}))
        self.put(f"{self.frontend}/package.json", json.dumps({
            "dependencies": {"vue": "^3.0"}, "description": "manifest-secret-must-not-leak",
        }))
        self.put(f"{self.frontend}/src/main.ts", "source-secret-must-not-leak")
        self.put("whatsapp-bot/package.json", json.dumps({"dependencies": {"express": "^5.0"}}))
        self.model = Mock()
        self.model.generate_plan.return_value = json.dumps({"backend": self.backend, "frontend": self.frontend})
        self.attribution = {"provider": "ChatGPT Plus (consumer)", "model": "fixture", "billing": "consumer subscription"}
        self.model.last_planner_attribution.return_value = self.attribution
        for patcher in (
            patch.dict(os.environ, {
                "NESTI_PROJECT_PATH": str(self.root), "NESTI_STATE_DIR": str(self.base / "state"),
                "GITLAB_URL": "https://gitlab.invalid", "GITLAB_PROJECT_PATH": "Group/App",
                "GITLAB_TARGET_BRANCH": "main", "GITLAB_TOKEN": "test-only",
            }),
            patch("gitlab_issues_client.GitLabIssuesClient.get_project", return_value={
                "id": 7, "path_with_namespace": "Group/App", "web_url": "https://gitlab.invalid/Group/App",
            }),
            patch.object(llm_client, "LLMClient", return_value=self.model),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def put(self, relative: str, value: str) -> None:
        file = self.root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(value, encoding="utf-8")

    def test_selects_once_persists_attribution_and_reuses_without_model(self) -> None:
        self.assertEqual(context.configured_project_root(discover=True), self.root / self.backend)
        saved = json.loads(context._layout_path().read_text())
        self.assertEqual(saved["attribution"], self.attribution)
        self.assertEqual(saved["project_root"], str(self.root))
        self.assertEqual(saved["git_root"], str(self.root))
        self.assertEqual(saved["frontend"], self.frontend)
        for discover in (False, True):
            self.assertEqual(context.configured_project_root(discover=discover), self.root / self.backend)
        self.model.generate_plan.assert_called_once()
        project = context.inspect_project(str(self.root / self.backend))
        self.assertEqual(project["application_root"], self.backend)
        self.assertEqual(project["frontend_root"], self.frontend)
        self.assertEqual(project["project_root"], str(self.root))
        self.model.generate_plan.assert_called_once()

    def test_directory_inventory_never_sends_contents_or_private_dependency_trees(self) -> None:
        for directory in ("vendor", "node_modules", "private", "credentials", ".git/private", "secrets"):
            self.put(f"{directory}/hidden-directory/package.json", "{}")
        self.put(".env", "another-secret")
        context.configured_project_root(discover=True)
        prompt = self.model.generate_plan.call_args.args[1]
        for forbidden in ("hidden-directory", "manifest-secret", "source-secret", "another-secret", "<?php", ".env"):
            self.assertNotIn(forbidden, prompt)
        self.assertIn("whatsapp-bot", prompt)
        self.assertIn("clients/browser", prompt)

    def test_identity_failure_happens_before_model(self) -> None:
        self.repo.remotes.origin.set_url("git@gitlab.invalid:Other/Project.git")
        with self.assertRaisesRegex(ValueError, "origin does not match"):
            context.configured_project_root(discover=True)
        self.model.generate_plan.assert_not_called()

    def test_missing_and_stale_selections_require_explicit_discovery(self) -> None:
        with self.assertRaisesRegex(ValueError, "layout missing"):
            context.configured_project_root()
        self.model.generate_plan.assert_not_called()
        context.configured_project_root(discover=True)
        self.put("services/orders/app/NewArea/Example.php", "<?php")
        with self.assertRaisesRegex(ValueError, "stale"):
            context.configured_project_root()
        self.model.generate_plan.assert_called_once()
        context.configured_project_root(discover=True)
        self.assertEqual(self.model.generate_plan.call_count, 2)

    def test_unsafe_missing_overlapping_and_non_spa_paths_are_rejected(self) -> None:
        (self.root / "linked").symlink_to(self.root / self.backend, target_is_directory=True)
        for backend, frontend in (
            ("../outside", self.frontend), (str(self.root / self.backend), self.frontend),
            ("linked", self.frontend), (self.backend, self.backend),
            (self.backend, "whatsapp-bot"), (self.backend, ""),
        ):
            with self.subTest(backend=backend, frontend=frontend):
                self.model.generate_plan.return_value = json.dumps({"backend": backend, "frontend": frontend})
                with self.assertRaises(ValueError):
                    context.configured_project_root(discover=True)
                self.assertFalse(context._layout_path().exists())

    def test_integrated_and_nested_frontends_are_rejected(self) -> None:
        self.put(f"{self.backend}/composer.json", json.dumps({
            "require": {"laravel/framework": "^13.0", "livewire/livewire": "^3.0"},
        }))
        with self.assertRaisesRegex(ValueError, "Integrated"):
            context.configured_project_root(discover=True)
        self.put(f"{self.backend}/composer.json", json.dumps({"require": {"laravel/framework": "^13.0"}}))
        self.put(f"{self.backend}/ui/package.json", json.dumps({"dependencies": {"vue": "^3.0"}}))
        self.put(f"{self.backend}/ui/index.html", "<div></div>")
        with self.assertRaisesRegex(ValueError, "nested"):
            context.configured_project_root(discover=True)

    def test_old_backend_root_needs_no_model_and_default_tooling_is_not_a_spa(self) -> None:
        self.put(f"{self.backend}/package.json", json.dumps({"devDependencies": {
            "vite": "^6.0", "laravel-vite-plugin": "^1.0",
        }}))
        self.put(f"{self.backend}/resources/js/app.js", "import './bootstrap';")
        self.put(f"{self.backend}/resources/views/welcome.blade.php", "welcome")
        with patch.dict(os.environ, {"NESTI_PROJECT_PATH": str(self.root / self.backend)}):
            self.assertEqual(context.configured_project_root(discover=True), self.root / self.backend)
        self.model.generate_plan.assert_not_called()

    def test_symlinked_markers_and_persisted_traversal_are_rejected(self) -> None:
        context.configured_project_root(discover=True)
        path = context._layout_path()
        saved = json.loads(path.read_text())
        saved["backend"] = "../outside"
        path.write_text(json.dumps(saved))
        with self.assertRaises(ValueError):
            context.configured_project_root()
        manifest = self.root / self.backend / "composer.json"
        manifest.unlink()
        manifest.symlink_to(self.root / self.frontend / "package.json")
        with self.assertRaisesRegex(ValueError, "symlink"):
            context.configured_project_root()


class ConsumerOnlyPlanningTests(unittest.TestCase):
    def test_discovery_never_falls_back_to_local_or_paid_providers(self) -> None:
        chain = llm_client.LLMClient.__new__(llm_client.LLMClient)
        consumer = Mock(name="consumer", available=True, billing="consumer subscription", model="fixture")
        consumer.generate_plan.side_effect = RuntimeError("consumer unavailable")
        paid = Mock(name="paid", available=True, billing="platform API")
        local = Mock(name="local", available=True, billing="local model")
        chain._planners = [consumer, local, paid]
        with patch.object(llm_client, "telegram_notify"):
            with self.assertRaisesRegex(RuntimeError, "will not use billed APIs"):
                chain.generate_plan("system", "safe listing", consumer_only=True)
        consumer.generate_plan.assert_called_once()
        paid.generate_plan.assert_not_called()
        local.generate_plan.assert_not_called()
        consumer.available = False
        consumer.generate_plan.reset_mock()
        with patch.object(llm_client, "telegram_notify"):
            with self.assertRaisesRegex(RuntimeError, "consumer subscription"):
                chain.generate_plan("system", "safe listing", consumer_only=True)
        consumer.generate_plan.assert_not_called()
        paid.generate_plan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
