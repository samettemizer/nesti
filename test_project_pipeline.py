"""Offline custom-layout, clean-clone and project-instruction regressions."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import git

with patch.dict(os.environ, {"REDIS_URL": "redis://127.0.0.1:1/0"}):
    import graph.nodes as nodes
from graph import tools
from prompt_builder import build_code_prompt, build_plan_prompt


def put(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


class ProjectPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nesti-pipeline-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {"NESTI_STACK": "auto", "NESTI_PROJECT_PATH": ""})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def laravel(self, root: Path) -> None:
        put(root, "artisan", "<?php")
        put(root, "composer.json", json.dumps({
            "require": {"laravel/framework": "^12", "dedoc/scramble": "*"},
            "autoload": {"psr-4": {"Domain\\": "src/", "Domain\\Sales\\": "modules/Sales/"}},
        }))
        put(root, "src/Marker.php", "<?php namespace Domain;")
        put(root, "modules/Sales/Http/Controllers/OrderController.php",
            "<?php namespace Domain\\Sales\\Http\\Controllers; use Domain\\Sales\\Http\\Resources\\OrderResource; // CONTROLLER_BODY")
        put(root, "modules/Sales/Http/Resources/OrderResource.php", "<?php // RESOURCE_BODY")
        put(root, "bootstrap/app.php", "<?php return Application::configure()->withRouting(api: __DIR__.'/../modules/Sales/routes.php');")
        put(root, "modules/Sales/routes.php", "<?php use Domain\\Sales\\Http\\Controllers\\OrderController; Route::get('/orders', [OrderController::class, 'index']);")

    def test_custom_psr4_inventory_and_api_gate(self) -> None:
        self.laravel(self.root)
        context = nodes._repo_inventory(str(self.root), "backend", "Update orders API")
        self.assertIn("CONTROLLER_BODY", context)
        self.assertIn("RESOURCE_BODY", context)
        self.assertIn("modules/Sales/routes.php", context)
        self.assertNotIn("The repository is a freshly scaffolded", context)
        for path in ("modules/Sales/routes.php", "modules/Sales/Http/Controllers/OrderController.php"):
            result = tools.tool_detect_stack(str(self.root), [path])
            self.assertTrue(result["success"], result)
            self.assertTrue(result["result"]["run_openapi"])
        for path in ("database/migrations/add_orders.php", "modules/Sales/Tests/OrderTest.php"):
            self.assertFalse(tools.tool_detect_stack(str(self.root), [path])["result"]["run_openapi"])

    def test_custom_pages_and_unresolved_routing_are_shared(self) -> None:
        self.laravel(self.root)
        put(self.root, "ui/Orders.vue", "<template>Orders</template>")
        put(self.root, "modules/Sales/pages.php", "<?php Route::view('/orders', 'orders');")
        result = tools.tool_detect_stack(str(self.root), ["modules/Sales/pages.php"])["result"]
        self.assertTrue(result["run_phpunit"])
        self.assertTrue(result["run_frontend"])
        put(self.root, "src/RouteProvider.php", "<?php $this->loadRoutesFrom($dynamicRoutes);")
        for path in ("src/RouteProvider.php", "src/Service.php"):
            result = tools.tool_detect_stack(str(self.root), [path])["result"]
            self.assertTrue(result["run_openapi"])
        self.assertTrue(tools.tool_detect_stack(str(self.root), ["src/RouteProvider.php"])["result"]["run_frontend"])
        self.assertFalse(tools.tool_detect_stack(str(self.root), ["ui/Orders.vue"])["result"]["run_phpunit"])

    def test_external_human_rules_are_prompt_only_and_stale_generated_rules_omitted(self) -> None:
        shared, clone = self.root / "shared", self.root / "clone"
        self.laravel(shared)
        self.laravel(clone)
        put(shared, ".omp/rules/orders.md", "---\ndescription: Order conventions\nalwaysApply: true\n---\nHUMAN_RULE: retain domain boundaries.\n")
        put(shared, ".omp/rules/nesti-boost-old.md", "---\ndescription: Old orders\nalwaysApply: true\n---\nSTALE_GENERATED_BODY\n")
        put(shared, "src/Rejected.php", "<?php // FAILED_LOCAL_PATCH")
        context = nodes._repo_inventory(str(clone), "backend", "Orders", project={"root": str(shared)})
        for builder, args in ((build_plan_prompt, ({"subject": "Orders"},)),
                              (build_code_prompt, ({"subject": "Orders"}, "Update orders"))):
            _, prompt = builder(*args, scope="backend", repo_context=context)
            self.assertIn("HUMAN_RULE", prompt)
            self.assertIn("Generated rule omitted", prompt)
            self.assertNotIn("STALE_GENERATED_BODY", prompt)
            self.assertNotIn("FAILED_LOCAL_PATCH", prompt)
        self.assertFalse((clone / ".omp").exists())
        self.assertFalse((clone / "src/Rejected.php").exists())

    def test_empty_and_unsafe_inventory_never_claims_greenfield(self) -> None:
        outside = self.root / "outside"
        clone = self.root / "clone"
        clone.mkdir()
        put(outside, "Secret.php", "NEVER_READ_SECRET")
        (clone / "linked").symlink_to(outside, target_is_directory=True)
        put(clone, ".env", "NEVER_READ_ENV")
        put(clone, "composer.json", json.dumps({"autoload": {"psr-4": {"Bad\\": "../outside"}}}))
        context = nodes._repo_inventory(str(clone), task_text="linked/Secret.php .env")
        self.assertIn("Unresolved Composer", context)
        self.assertNotIn("NEVER_READ", context)
        empty = self.root / "empty"
        empty.mkdir()
        self.assertIn("No eligible source evidence", nodes._repo_inventory(str(empty)))

    def test_api_topup_preserves_frontend_configuration(self) -> None:
        self.laravel(self.root)
        vite = "export default { plugins: [] };\n"
        package = '{"scripts":{"build":"vite build"},"dependencies":{"some-tool":"1"}}'
        put(self.root, "vite.config.js", vite)
        put(self.root, "package.json", package)
        with patch.object(tools, "DockerRunner") as runner:
            result = tools.tool_laravel_bootstrap(str(self.root))
        self.assertTrue(result["success"], result)
        runner.assert_not_called()
        self.assertEqual((self.root / "vite.config.js").read_text(), vite)
        self.assertEqual((self.root / "package.json").read_text(), package)
        self.assertFalse((self.root / "resources/js/app.js").exists())
        self.assertFalse((self.root / "vitest.config.js").exists())

    def test_split_changes_select_only_the_affected_application_gates(self) -> None:
        self.laravel(self.root / "backend")
        put(self.root, "frontend/package.json", '{"dependencies":{"vue":"^3"}}')
        put(self.root, "frontend/src/App.vue", "<template>Orders</template>")
        layout = {"application_root": "backend", "frontend_root": "frontend"}
        cases = (
            (["frontend/src/App.vue"], (False, True, False)),
            (["backend/modules/Sales/Http/Controllers/OrderController.php"], (True, False, True)),
            (["backend/database/migrations/add_orders.php"], (True, False, False)),
            (["frontend/src/App.vue", "backend/modules/Sales/routes.php"], (True, True, True)),
            (["README.md"], (True, False, False)),
        )
        for changed, gates in cases:
            with self.subTest(changed=changed):
                response = tools.tool_detect_stack(str(self.root), changed, **layout)
                self.assertTrue(response["success"], response)
                result = response["result"]
                self.assertEqual(tuple(result[key] for key in (
                    "run_phpunit", "run_frontend", "run_openapi",
                )), gates)

    def test_split_file_batch_rejects_embedded_frontend_before_writing(self) -> None:
        from docker_runner import DockerRunner

        valid = "### FILE: backend/app/Example.php\n```php\n<?php // API\n```\n"
        invalid = valid + "### FILE: backend/resources/js/App.vue\n```vue\n<template>Wrong root</template>\n```\n"
        layout = {"backend_root": "backend", "frontend_root": "frontend"}
        with self.assertRaisesRegex(ValueError, "SPA files"):
            DockerRunner.write_files(invalid, str(self.root), **layout)
        self.assertFalse((self.root / "backend/app/Example.php").exists())
        with self.assertRaisesRegex(ValueError, "SPA files"):
            DockerRunner.write_files(
                "### FILE: resources/js/App.vue\n```vue\n<template>No SPA configured</template>\n```\n",
                str(self.root), backend_root="",
            )
        response = valid + "### FILE: frontend/src/App.vue\n```vue\n<template>Separate SPA</template>\n```\n"
        DockerRunner.write_files(response, str(self.root), **layout)
        self.assertEqual((self.root / "frontend/src/App.vue").read_text(), "<template>Separate SPA</template>\n")
        self.assertEqual((self.root / "backend/app/Example.php").read_text(), "<?php // API\n")

    def test_nested_setup_and_commit_use_git_root(self) -> None:
        source = self.root / "source"
        self.laravel(source / "backend")
        project = {"root": str(source / "backend"), "application_root": "backend"}
        def clone(target: str) -> dict:
            shutil.copytree(source, target)
            return {"success": True, "result": {"repo_path": target}}
        with patch.dict(os.environ, {"NESTI_PROJECT_PATH": str(source / "backend")}), \
             patch.object(nodes, "configured_project_root", return_value=source / "backend"), \
             patch.object(nodes, "inspect_project", return_value=project), \
             patch.object(nodes, "tool_issue_set_status", return_value={"success": True}), \
             patch.object(nodes, "tool_gitlab_clone", side_effect=clone), \
             patch.object(nodes, "tool_gitlab_create_branch", return_value={"success": True, "result": {"branch_name": "feature/test"}}) as branch:
            state = nodes.node_setup({"issue_id": 7, "subject": "Orders"})
        self.addCleanup(shutil.rmtree, state["workspace"], True)
        self.assertEqual(Path(state["repo_path"]), Path(state["git_root"]) / "backend")
        self.assertEqual(branch.call_args.args[0], state["git_root"])
        with patch.object(nodes, "tool_gitlab_commit_and_push", return_value={"success": True, "result": {"pushed": True}}) as push, \
             patch.object(nodes, "tool_gitlab_open_mr", return_value={"success": False, "error": "test stop"}) as mr:
            nodes.node_commit({**state, "issue_id": 7})
        self.assertEqual(push.call_args.args[0], state["git_root"])
        self.assertIn("Application subdirectory: `backend`", mr.call_args.kwargs["description"])

    def test_absent_nested_app_refuses_bootstrap(self) -> None:
        source = self.root / "source"
        source.mkdir()
        def clone(target: str) -> dict:
            shutil.copytree(source, target)
            return {"success": True}
        with patch.dict(os.environ, {"NESTI_PROJECT_PATH": str(source)}), \
             patch.object(nodes, "configured_project_root", return_value=source), \
             patch.object(nodes, "inspect_project", return_value={"application_root": "backend"}), \
             patch.object(nodes, "tool_issue_set_status", return_value={"success": True}), \
             patch.object(nodes, "tool_gitlab_clone", side_effect=clone), \
             patch.object(nodes, "tool_gitlab_create_branch") as branch:
            with self.assertRaisesRegex(RuntimeError, "refusing bootstrap"):
                nodes.node_setup({"issue_id": 7})
        branch.assert_not_called()

    def test_nested_retry_restores_committed_file(self) -> None:
        repo = git.Repo.init(self.root)
        app = self.root / "backend"
        put(app, "src/Original.php", "original")
        repo.index.add(["backend/src/Original.php"])
        repo.index.commit("baseline")
        put(app, "src/Original.php", "changed")
        put(app, "src/Temporary.php", "temporary")
        reverted = nodes._prune_stale_files(["src/Original.php", "src/Temporary.php"], [], str(app))
        self.assertEqual(len(reverted), 2)
        self.assertEqual((app / "src/Original.php").read_text(), "original")
        self.assertFalse((app / "src/Temporary.php").exists())


if __name__ == "__main__":
    unittest.main()
