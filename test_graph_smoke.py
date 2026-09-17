"""
test_graph_smoke.py – verifies the LangGraph pipeline against the acceptance
checklists of Phase 2 (core loop), Phase 4 (layered frontend testing) and
Phase 5 (Laravel bootstrap + Scramble OpenAPI gate), with all external
services (GitLab Issues, GitLab, Docker, LLM providers) monkeypatched at the
node/tool seam.

``tool_detect_stack`` is deliberately NOT patched: the fake clone is a real
temporary directory and the fake coder writes real files into it, so stack
detection — including the Laravel and /api markers — is exercised for real
against each scenario's file tree.

``skill_catalog`` is likewise exercised for real against the vendored corpus
in ``skills/``; only the *node-level* selection tool is faked, so prompt
building stays offline.

Run:  python test_graph_smoke.py
"""

import json
import logging
import os
import shutil
import tempfile

# ── Environment before any project import ────────────────────────────────────
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ["LOCAL_LLM_ENABLED"] = "false"
os.environ["HERMES3_LLM_ENABLED"] = "false"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"   # unreachable → memory fallback
os.environ["MAX_CODE_RETRIES"] = "2"                 # → max_attempts = 3
os.environ["NESTI_STACK"] = "auto"                   # exercise real detection
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TELEGRAM_CHAT_ID", None)
os.environ.pop("DEEPSEEK_API_KEY", None)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "DEBUG"),
                    format="%(levelname)s %(name)s – %(message)s")

import graph.nodes as nodes                      # noqa: E402
from graph.builder import graph as compiled     # noqa: E402
from graph.edges import (                        # noqa: E402
    route_after_plan, route_after_detect_stack, route_after_phpunit,
    route_after_openapi, route_after_vitest, route_after_playwright,
)
from graph.tools import tool_detect_stack        # noqa: E402
import skill_catalog                             # noqa: E402

PHP_CODE = (
    "Implementation below.\n\n"
    "### FILE: src/Hello.php\n```php\n<?php\necho 'hello';\n```\n\n"
    "### FILE: tests/HelloTest.php\n```php\n<?php\n// phpunit test\n```\n"
)
VUE_CODE = (
    "Implementation below.\n\n"
    "### FILE: package.json\n```json\n{\"name\": \"app\"}\n```\n\n"
    "### FILE: src/components/FileTable.vue\n```vue\n<template><div/></template>\n```\n\n"
    "### FILE: src/components/__tests__/FileTable.test.js\n```js\n// vitest\n```\n\n"
    "### FILE: e2e/file-table.spec.js\n```js\n// playwright\n```\n"
)
FULLSTACK_CODE = PHP_CODE + "\n" + VUE_CODE

# Phase 5 fixtures: a real Laravel change (backend + API surface) and the same
# change with a PrimeVue component on top.
LARAVEL_CODE = (
    "Implementation below.\n\n"
    "### FILE: routes/api.php\n```php\n<?php\n// Route::apiResource('tasks', ...)\n```\n\n"
    "### FILE: app/Http/Controllers/TaskController.php\n```php\n<?php\n// controller\n```\n\n"
    "### FILE: app/Models/Task.php\n```php\n<?php\n// model\n```\n\n"
    "### FILE: database/migrations/2026_01_01_000000_create_tasks_table.php\n"
    "```php\n<?php\n// migration\n```\n\n"
    "### FILE: tests/Feature/TaskApiTest.php\n```php\n<?php\n// feature test\n```\n"
)
LARAVEL_VUE_CODE = LARAVEL_CODE + (
    "\n"
    "### FILE: resources/js/components/TaskTable.vue\n"
    "```vue\n<template><div/></template>\n```\n\n"
    "### FILE: resources/js/components/__tests__/TaskTable.test.js\n```js\n// vitest\n```\n\n"
    "### FILE: e2e/tasks.spec.js\n```js\n// playwright\n```\n"
)
GOOD_CODE = PHP_CODE          # Phase 2 scenarios stay backend-only
NO_BLOCKS = "Here is a prose description of the change instead of files."

calls: dict = {}


def reset_calls(issue_id: int) -> None:
    calls.clear()
    calls.update({
        "issue_id": issue_id, "issues": [], "docker": 0, "escalate": 0,
        "openapi": 0, "vitest": 0, "playwright": 0,
        "bootstrap": [], "layers": [],
        "pushes": [], "mrs": [], "history_at_commit": None, "workspaces": [],
    })


def initial(issue_id: int) -> dict:
    return {
        "issue": {"id": issue_id, "subject": f"Test issue {issue_id}",
                  "description": "Implement the thing."},
        "issue_id": issue_id, "subject": f"Test issue {issue_id}",
        "skills": [], "plan": "", "code_response": "", "repo_path": "",
        "branch_name": "", "workspace": "", "messages": [],
        "attempt": 0, "max_attempts": 3,
        "files_written": False, "written_files": [],
        "has_vue_files": False, "stack": "php", "run_phpunit": True,
        "is_laravel": False, "bootstrapped": False,
        "has_api_routes": False, "run_openapi": False,
        "test_output": "", "test_passed": False,
        "openapi_passed": False, "openapi_output": "", "openapi_paths": [],
        "vitest_passed": False, "vitest_output": "",
        "playwright_passed": False, "playwright_output": "",
        "mr_url": "", "failure_reason": "", "error": "",
    }


def patch_tools(docker_outcomes, code_responses, plan_exc=None, code_exc_first=False,
                openapi_outcomes=(True,),
                vitest_outcomes=(True,), playwright_outcomes=(True,),
                laravel_repo: bool = False, bootstrap_created: bool = False):
    """
    Install fakes on graph.nodes (node functions resolve names at call time).

    ``laravel_repo`` makes the fake clone look like a Laravel application so the
    REAL tool_detect_stack reports is_laravel/has_api_routes.  It defaults to
    False on purpose: dropping a composer.json into every fake clone would turn
    the Vue-only scenario into "fullstack" and silently void that regression.
    """

    def fake_set_status(issue_id, status, note=""):
        calls["issues"].append((issue_id, status, note))
        return {"success": True, "result": {"issue_id": issue_id, "status": status}}
    nodes.tool_issue_set_status = fake_set_status

    def fake_clone(target_path):
        os.makedirs(target_path, exist_ok=True)
        calls["workspaces"].append(os.path.dirname(target_path))
        if laravel_repo:
            # Real markers, so detection is not faked — only the repo is.
            open(os.path.join(target_path, "artisan"), "w").close()
            open(os.path.join(target_path, "composer.json"), "w").close()
        return {"success": True, "result": {"repo_path": target_path}}
    nodes.tool_gitlab_clone = fake_clone

    def fake_bootstrap(repo_path):
        calls["bootstrap"].append(repo_path)
        return {"success": True, "result": {
            "created": bootstrap_created,
            "mode": "scaffold" if bootstrap_created else "top-up",
            "reason": "scaffolded" if bootstrap_created
                      else "already a Laravel application",
            "output": "",
        }}
    nodes.tool_laravel_bootstrap = fake_bootstrap

    nodes.tool_gitlab_create_branch = lambda repo_path, issue_id, subject: {
        "success": True, "result": {"branch_name": f"feature/issue-{issue_id}-test"}}

    def fake_push(repo_path, branch_name, message):
        calls["pushes"].append(message)
        calls["history_at_commit"] = nodes._store.load(calls["issue_id"])
        return {"success": True, "result": {"pushed": True}}
    nodes.tool_gitlab_commit_and_push = fake_push

    def fake_mr(branch_name, issue_id, subject, description):
        calls["mrs"].append(description)
        return {"success": True,
                "result": {"mr_url": f"https://gitlab.example/mr/{issue_id}", "mr": {}}}
    nodes.tool_gitlab_open_mr = fake_mr

    nodes.tool_skill_fetch = lambda issue: {"success": True, "result": []}
    # Keep prompt building offline: the real catalog is unit-tested separately.
    nodes.tool_skill_catalog_select = (
        lambda text, mc=3, mt=2: {"success": True, "result": []})
    nodes.tool_skill_catalog_status = lambda: {"success": True, "result": {
        "available": True, "components": 92, "topics": 24,
        "primevue_version": "5.0.1", "laravel_branch": "13.x"}}

    def _layered(key, outcomes, pass_out, fail_out):
        def fake(workspace_path):
            calls[key] += 1
            calls["layers"].append(key)
            passed = outcomes[min(calls[key] - 1, len(outcomes) - 1)]
            return {"success": True,
                    "result": {"passed": passed, "output": pass_out if passed else fail_out}}
        return fake

    nodes.tool_docker_run_tests = _layered(
        "docker", docker_outcomes,
        "OK (2 tests, 4 assertions)", "PHPUnit FAILURES!\n1) HelloTest::testHello")
    nodes.tool_vitest_run_tests = _layered(
        "vitest", vitest_outcomes,
        "Test Files  1 passed (1)", "FAIL  src/components/__tests__/FileTable.test.js")
    nodes.tool_playwright_run_tests = _layered(
        "playwright", playwright_outcomes,
        "1 passed (2.1s)", "1 failed\n  e2e/file-table.spec.js:4:1 › sorts rows")

    def fake_openapi(workspace_path):
        calls["openapi"] += 1
        calls["layers"].append("openapi")
        passed = openapi_outcomes[min(calls["openapi"] - 1, len(openapi_outcomes) - 1)]
        if passed:
            return {"success": True, "result": {
                "passed": True, "output": "3 path(s) documented",
                "paths": ["/api/tasks"], "undocumented": []}}
        return {"success": True, "result": {
            "passed": False,
            "output": "Undocumented API routes:\n- POST /api/tasks",
            "paths": [], "undocumented": ["POST /api/tasks"]}}
    nodes.tool_openapi_export = fake_openapi

    # LLM fakes (instance attributes shadow bound methods)
    if plan_exc:
        def fail_plan(sp, up, messages=None):
            raise RuntimeError(plan_exc)
        nodes._llm.generate_plan = fail_plan
    else:
        nodes._llm.generate_plan = (
            lambda sp, up, messages=None: "1. Objective: implement Hello\n2. Files: src/Hello.php")

    seq = list(code_responses)

    def fake_code(system_prompt, user_prompt, messages=None):
        if code_exc_first:
            raise RuntimeError("All coding providers exhausted.")
        return seq.pop(0) if len(seq) > 1 else seq[0]
    nodes._llm.generate_code = fake_code
    nodes._llm.escalate_coder = lambda: calls.__setitem__("escalate", calls["escalate"] + 1)


def run(issue_id, **kw):
    reset_calls(issue_id)
    patch_tools(**kw)
    final = compiled.invoke(initial(issue_id), config={"recursion_limit": 60})
    return final


passed_checks = 0
def check(cond, label):
    global passed_checks
    assert cond, f"FAILED: {label}"
    passed_checks += 1
    print(f"  ✓ {label}")


# ═════ Scenario 1: no FILE blocks on attempt 1 → feedback → pass on attempt 2 ═
print("\n── Scenario 1: no-blocks retry → success ──")
f = run(101, docker_outcomes=[True], code_responses=[NO_BLOCKS, GOOD_CODE])
check(f["mr_url"] == "https://gitlab.example/mr/101", "MR opened end-to-end")
check(f["attempt"] == 2, "attempt counter == 2")
check(calls["docker"] == 1, "docker skipped on no-blocks attempt (guard works)")
check(calls["escalate"] == 1, "coder escalated once")
statuses = [(s, n) for _, s, n in calls["issues"]]
check(statuses[0][0] == "in_progress", "issue locked first")
check(statuses[-1][0] == "closed" and "gitlab.example/mr/101" in statuses[-1][1],
      "issue closed with MR note")
hist = calls["history_at_commit"]
roles = [m["role"] for m in hist]
check(roles == ["user", "assistant", "user", "assistant", "user", "user", "assistant"],
      f"history role sequence correct ({len(hist)} turns)")
check("No files could be written" in hist[4]["content"], "corrective feedback in history")
check(hist[3]["content"] == NO_BLOCKS and hist[6]["content"] == GOOD_CODE,
      "both coder responses recorded")
check(nodes._store.load(101) == [], "history deleted after success")
check(not os.path.exists(calls["workspaces"][0]), "cleanup removed workspace")
check(os.path.isfile(os.path.join(f["repo_path"], "src", "Hello.php")) is False,
      "repo files gone with workspace")
check("## Summary" in calls["mrs"][0] and "OK (2 tests" in calls["mrs"][0],
      "MR description has plan + test output")

# ═════ Scenario 2: tests always fail → 3 attempts → failure path ═════
print("\n── Scenario 2: exhausted attempts → failure ──")
f = run(102, docker_outcomes=[False], code_responses=[GOOD_CODE])
check(f["mr_url"] == "", "no MR on exhausted attempts")
check(f["attempt"] == 3, "stopped exactly at max_attempts (3)")
check(calls["docker"] == 3, "tests ran 3 times")
check(calls["escalate"] == 2, "escalated between attempts (2x)")
check("3 attempt(s)" in f["failure_reason"], "failure_reason set")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check(len(reopen) == 1 and "failed to produce passing tests" in reopen[0][1]
      and "PHPUnit FAILURES!" in reopen[0][1], "issue reopened with failure note + test output")
check(nodes._store.load(102) == [], "history deleted after exhausted failure")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran on failure path")

# ═════ Scenario 3: planning fails → failure without any coding ═════
print("\n── Scenario 3: planning failure ──")
f = run(103, docker_outcomes=[True], code_responses=[GOOD_CODE],
        plan_exc="All planning providers exhausted.")
check(f["plan"] == "" and "Planning failed" in f["failure_reason"], "routed plan → failure")
check(f["attempt"] == 0 and calls["docker"] == 0, "no code/test attempts made")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check(len(reopen) == 1 and "planning providers failed" in reopen[0][1],
      "reopened with planning note")
check("All planning providers exhausted." in f["error"], "error field populated")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran after plan failure")
check(len(nodes._store.load(103)) == 1, "history kept (only the plan request turn)")
nodes._store.delete(103)

# ═════ Scenario 4: coder providers exhausted → immediate failure ═════
print("\n── Scenario 4: coder providers exhausted ──")
f = run(104, docker_outcomes=[True], code_responses=[GOOD_CODE], code_exc_first=True)
check(f["mr_url"] == "" and f["attempt"] == 3, "attempt jumped to max → failure route")
check(calls["docker"] == 0, "no sandbox run for exhausted providers")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check("All coding providers exhausted." in reopen[0][1],
      "reopen note carries provider-exhaustion reason (Phase 1 parity)")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran")

# ═════ Scenario 5: PHP-only issue skips both frontend layers ═════
print("\n── Scenario 5: PHP-only issue → frontend layers skipped ──")
f = run(105, docker_outcomes=[True], code_responses=[PHP_CODE])
check(f["stack"] == "php" and f["has_vue_files"] is False, "stack detected as php")
check(f["run_phpunit"] is True, "PHPUnit layer enabled")
check(calls["docker"] == 1, "PHPUnit ran once")
check(calls["vitest"] == 0 and calls["playwright"] == 0,
      "vitest_test and playwright_test never entered")
check(f["mr_url"] == "https://gitlab.example/mr/105", "went straight to commit")

# ═════ Scenario 6: Vue-only issue skips PHPUnit (the Phase 4 fix) ═════
print("\n── Scenario 6: Vue-only issue → PHPUnit skipped ──")
f = run(106, docker_outcomes=[False], code_responses=[VUE_CODE])
check(f["stack"] == "vue", "stack detected as vue (no PHP anywhere)")
check(f["run_phpunit"] is False, "PHPUnit layer disabled for frontend-only repo")
check(calls["docker"] == 0,
      "PHPUnit never ran — a PHP-free repo no longer fails permanently")
check(calls["vitest"] == 1 and calls["playwright"] == 1, "both frontend layers ran once")
check(f["vitest_passed"] and f["playwright_passed"], "frontend layers passed")
check(f["mr_url"] == "https://gitlab.example/mr/106", "Vue-only issue reaches an MR")
check(f["attempt"] == 1 and calls["escalate"] == 0, "no retries needed")
check("Vitest" in calls["mrs"][0] and "Playwright" in calls["mrs"][0],
      "MR description reports both frontend layers")
check("PHPUnit" not in calls["mrs"][0], "MR description omits the skipped layer")

# ═════ Scenario 7: fullstack issue runs all three layers in order ═════
print("\n── Scenario 7: fullstack issue → PHPUnit → Vitest → Playwright ──")
f = run(107, docker_outcomes=[True], code_responses=[FULLSTACK_CODE])
check(f["stack"] == "fullstack", "stack detected as fullstack")
check(f["run_phpunit"] is True and f["has_vue_files"] is True, "both layers enabled")
check(calls["docker"] == 1 and calls["vitest"] == 1 and calls["playwright"] == 1,
      "all three layers ran exactly once")
check(f["mr_url"] == "https://gitlab.example/mr/107", "MR opened after all layers")
check(all(k in calls["mrs"][0] for k in ("PHPUnit", "Vitest", "Playwright")),
      "MR description reports all three layers")

# ═════ Scenario 8: Vitest failure escalates and retries ═════
print("\n── Scenario 8: Vitest failure → escalate → exhausted ──")
f = run(108, docker_outcomes=[True], code_responses=[VUE_CODE], vitest_outcomes=[False])
check(f["mr_url"] == "" and f["attempt"] == 3, "3 attempts then failure")
check(calls["vitest"] == 3, "Vitest ran on every attempt")
check(calls["playwright"] == 0, "Playwright never ran — Vitest gates it")
check(calls["escalate"] == 2, "coder escalated between attempts (2x)")
check("Vitest" in f["failure_reason"], "failure_reason names the failing layer")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check("FAIL  src/components" in reopen[0][1], "reopen note carries the Vitest output")
hist_snapshot = nodes._store.load(108)
check(hist_snapshot == [], "history deleted after exhausted frontend failure")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran on frontend failure path")

# ═════ Scenario 9: Playwright failure escalates and retries ═════
print("\n── Scenario 9: Playwright failure → escalate → exhausted ──")
f = run(109, docker_outcomes=[True], code_responses=[VUE_CODE], playwright_outcomes=[False])
check(f["mr_url"] == "" and f["attempt"] == 3, "3 attempts then failure")
check(calls["vitest"] == 3 and calls["playwright"] == 3, "both layers ran each attempt")
check(calls["escalate"] == 2, "coder escalated between attempts (2x)")
check("Playwright" in f["failure_reason"], "failure_reason names Playwright")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check("e2e/file-table.spec.js" in reopen[0][1], "reopen note carries the Playwright output")

# ═════ Scenario 10: PHPUnit failure in a fullstack repo gates the frontend ═════
print("\n── Scenario 10: fullstack, PHPUnit fails → frontend layers gated ──")
f = run(110, docker_outcomes=[False], code_responses=[FULLSTACK_CODE])
check(calls["docker"] == 3, "PHPUnit ran on every attempt")
check(calls["vitest"] == 0 and calls["playwright"] == 0,
      "frontend layers never reached while the backend layer is red")
check("PHPUnit" in f["failure_reason"], "failure_reason names PHPUnit")

# ═════ Scenario 11: stack detection unit tests ═════
print("\n── Scenario 11: tool_detect_stack ──")
probe = tempfile.mkdtemp(prefix="nesti-detect-")
try:
    os.makedirs(os.path.join(probe, "src", "components"))
    open(os.path.join(probe, "src", "components", "Widget.vue"), "w").close()
    r = tool_detect_stack(probe)["result"]
    check(r["stack"] == "vue" and r["run_phpunit"] is False, "vue only → run_phpunit False")
    check(r["vue_files"] == [os.path.join("src", "components", "Widget.vue")],
          "vue_files lists repo-relative paths")

    open(os.path.join(probe, "composer.json"), "w").close()
    r = tool_detect_stack(probe)["result"]
    check(r["stack"] == "fullstack" and r["run_phpunit"] is True,
          "composer.json alone flips vue → fullstack")

    # node_modules is populated by the Vitest sandbox from attempt 2 onward and
    # Vue component libraries ship .vue files — those must never be detected.
    os.makedirs(os.path.join(probe, "node_modules", "primevue"))
    open(os.path.join(probe, "node_modules", "primevue", "Vendor.vue"), "w").close()
    r = tool_detect_stack(probe)["result"]
    check(len(r["vue_files"]) == 1, "node_modules pruned from the scan")

    vendored = tempfile.mkdtemp(prefix="nesti-detect-vendor-")
    os.makedirs(os.path.join(vendored, "vendor", "acme"))
    os.makedirs(os.path.join(vendored, "src"))
    open(os.path.join(vendored, "vendor", "acme", "Lib.php"), "w").close()
    open(os.path.join(vendored, "src", "App.vue"), "w").close()
    r = tool_detect_stack(vendored)["result"]
    check(r["stack"] == "vue" and r["has_php"] is False,
          "vendor/ pruned — Composer leftovers do not force the PHP layer on")
    shutil.rmtree(vendored, ignore_errors=True)

    empty = tempfile.mkdtemp(prefix="nesti-detect-empty-")
    r = tool_detect_stack(empty)["result"]
    check(r["stack"] == "unknown" and r["run_phpunit"] is True,
          "unknown stack still runs a test layer (never commits untested)")
    shutil.rmtree(empty, ignore_errors=True)

    os.environ["NESTI_STACK"] = "php"
    r = tool_detect_stack(probe)["result"]
    check(r["stack"] == "php" and r["source"] == "override" and r["has_vue"] is False,
          "NESTI_STACK pins the stack and reports source=override")
    os.environ["NESTI_STACK"] = "bogus"
    check(tool_detect_stack(probe)["success"] is False, "invalid NESTI_STACK rejected")
finally:
    os.environ["NESTI_STACK"] = "auto"
    shutil.rmtree(probe, ignore_errors=True)

# ═════ Scenario 11b: OpenAPI gate detection ═════
print("\n── Scenario 11b: tool_detect_stack → run_openapi gate ──")
laravel_probe = tempfile.mkdtemp(prefix="nesti-detect-laravel-")
try:
    os.makedirs(os.path.join(laravel_probe, "routes"))
    open(os.path.join(laravel_probe, "artisan"), "w").close()
    open(os.path.join(laravel_probe, "composer.json"), "w").close()
    open(os.path.join(laravel_probe, "routes", "api.php"), "w").close()

    r = tool_detect_stack(laravel_probe, ["routes/api.php"])["result"]
    check(r["is_laravel"] is True and r["has_api_routes"] is True,
          "artisan + routes/api.php detected")
    check(r["run_openapi"] is True, "routes/api.php touched → OpenAPI layer runs")

    for touched in ("app/Http/Controllers/TaskController.php",
                    "app/Http/Resources/TaskResource.php",
                    "app/Http/Requests/StoreTaskRequest.php"):
        r = tool_detect_stack(laravel_probe, [touched])["result"]
        check(r["run_openapi"] is True, f"{touched} touched → OpenAPI layer runs")

    r = tool_detect_stack(laravel_probe, ["resources/js/components/X.vue"])["result"]
    check(r["run_openapi"] is False,
          "frontend-only change skips the OpenAPI layer (no wasted container)")
    r = tool_detect_stack(laravel_probe, [])["result"]
    check(r["run_openapi"] is False, "no files written → OpenAPI layer skipped")
    r = tool_detect_stack(laravel_probe, None)["result"]
    check(r["run_openapi"] == r["has_api_routes"],
          "written_files=None → conservative answer (MCP callers)")

    no_api = tempfile.mkdtemp(prefix="nesti-detect-noapi-")
    open(os.path.join(no_api, "artisan"), "w").close()
    r = tool_detect_stack(no_api, ["routes/api.php"])["result"]
    check(r["is_laravel"] is True and r["has_api_routes"] is False
          and r["run_openapi"] is False,
          "Laravel app without routes/api.php never enters the OpenAPI layer")
    shutil.rmtree(no_api, ignore_errors=True)

    os.environ["NESTI_STACK"] = "php"
    r = tool_detect_stack(laravel_probe, ["routes/api.php"])["result"]
    check(r["source"] == "override" and r["run_openapi"] is True,
          "NESTI_STACK override still reports the Laravel markers")
finally:
    os.environ["NESTI_STACK"] = "auto"
    shutil.rmtree(laravel_probe, ignore_errors=True)

# ═════ Scenario 11c: skill_catalog against the real vendored corpus ═════
print("\n── Scenario 11c: skill_catalog (real registry, offline) ──")
_registry_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "skills", "registry.json")
if not os.path.isfile(_registry_path):
    print("  ⚠ SKIPPED (corpus not generated – run scripts/fetch_skills.py)")
else:
    status = skill_catalog.catalog_status()
    check(status["available"] is True, "catalog reports available")
    check(status["components"] >= 85,
          f"catalog has {status['components']} PrimeVue component docs (>= 85)")
    check(status["topics"] == 24, "catalog has all 24 Laravel topics")

    titles = [s.title for s in skill_catalog.select_skills("use the PrimeVue DataTable")]
    check(titles[:1] == ["DataTable"], "DataTable selected first for a DataTable issue")

    picked = skill_catalog.select_skills("Replace the grid with a Dropdown")
    check(any(s.url.endswith("/select.md") for s in picked),
          "legacy name 'Dropdown' resolves to the PrimeVue 5 Select doc")
    picked = skill_catalog.select_skills("render an OrgChart of the team")
    check(any(s.url.endswith("/organizationchart.md") for s in picked),
          "'OrgChart' resolves to organizationchart.md (slug anomaly handled)")
    picked = skill_catalog.select_skills("add a migration for the tasks table")
    check(any(s.url.endswith("/migrations.md") for s in picked),
          "migration wording selects the Laravel migrations topic")

    check(skill_catalog.select_skills("nothing relevant here at all") == [],
          "no alias/trigger hit → no documentation injected")
    check(skill_catalog.select_skills("") == [], "blank text → no documentation")

    budget = skill_catalog._DOC_CHAR_CAP + len(skill_catalog._TRUNCATION_MARKER)
    docs = skill_catalog.select_skills("PrimeVue DataTable migration seeder factory")
    check(docs and all(len(s.content) <= budget for s in docs),
          f"every selected doc is within the {skill_catalog._DOC_CHAR_CAP}-char cap")
    check(all(s.content.endswith(skill_catalog._TRUNCATION_MARKER)
              or "\n## " not in s.content[-200:]
              for s in docs),
          "trimmed docs carry the truncation marker")
    check(len(skill_catalog.select_skills(
              "DataTable Dialog Select Calendar Button", max_component_docs=2)) <= 2 + 2,
          "max_component_docs is honoured")

# ═════ Scenario 14: Laravel API issue → phpunit → openapi → commit ═════
print("\n── Scenario 14: Laravel API issue → PHPUnit → OpenAPI → commit ──")
f = run(114, docker_outcomes=[True], code_responses=[LARAVEL_CODE], laravel_repo=True)
check(f["is_laravel"] is True, "repository detected as Laravel")
check(f["has_api_routes"] is True and f["run_openapi"] is True,
      "API surface touched → OpenAPI layer enabled")
check(calls["layers"] == ["docker", "openapi"],
      f"layer order is PHPUnit → OpenAPI (got {calls['layers']})")
check(calls["vitest"] == 0 and calls["playwright"] == 0,
      "no .vue files → frontend layers never started")
check(f["openapi_passed"] is True and f["openapi_paths"] == ["/api/tasks"],
      "documented paths recorded on the state")
check(f["mr_url"] == "https://gitlab.example/mr/114", "MR opened after the OpenAPI gate")
check("### OpenAPI" in calls["mrs"][0], "MR description carries the OpenAPI section")
check("/api/tasks" in calls["mrs"][0], "MR description lists the documented route")
check("Laravel: True" in calls["mrs"][0], "MR description reports the Laravel flag")

# ═════ Scenario 15: Laravel fullstack issue → all four layers ═════
print("\n── Scenario 15: Laravel fullstack → PHPUnit → OpenAPI → Vitest → Playwright ──")
f = run(115, docker_outcomes=[True], code_responses=[LARAVEL_VUE_CODE], laravel_repo=True)
check(f["stack"] == "fullstack", "stack detected as fullstack")
check(calls["layers"] == ["docker", "openapi", "vitest", "playwright"],
      f"all four layers ran in order (got {calls['layers']})")
check(f["test_passed"] and f["openapi_passed"]
      and f["vitest_passed"] and f["playwright_passed"], "every layer green")
check(len(calls["mrs"]) == 1 and f["mr_url"] == "https://gitlab.example/mr/115",
      "exactly one MR opened")
check(all(k in calls["mrs"][0]
          for k in ("### PHPUnit", "### OpenAPI", "### Vitest", "### Playwright")),
      "MR description reports all four layers")

# ═════ Scenario 16: OpenAPI gate red on every attempt → failure ═════
print("\n── Scenario 16: undocumented /api route → escalate → exhausted ──")
f = run(116, docker_outcomes=[True], code_responses=[LARAVEL_CODE],
        openapi_outcomes=[False], laravel_repo=True)
check(f["mr_url"] == "" and f["attempt"] == 3, "3 attempts then failure")
check(calls["openapi"] == 3, "OpenAPI gate ran on every attempt")
check(calls["escalate"] == 2, "coder escalated between attempts (2x)")
check(calls["vitest"] == 0, "Vitest never ran — the OpenAPI gate blocks it")
check("OpenAPI" in f["failure_reason"],
      f"failure_reason names the OpenAPI layer (got {f['failure_reason']!r})")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check(len(reopen) == 1 and "Undocumented API routes" in reopen[0][1],
      "reopen note names exactly what to document")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran on the OpenAPI failure path")

# ═════ Scenario 17: bootstrap skipped vs. performed ═════
print("\n── Scenario 17: node_bootstrap ──")
f = run(117, docker_outcomes=[True], code_responses=[LARAVEL_CODE], laravel_repo=True)
check(len(calls["bootstrap"]) == 1, "bootstrap ran exactly once, before load_skills")
check(f["bootstrapped"] is False, "existing Laravel app → bootstrapped False (top-up)")
f = run(118, docker_outcomes=[True], code_responses=[LARAVEL_CODE],
        laravel_repo=True, bootstrap_created=True)
check(f["bootstrapped"] is True, "greenfield scaffold → bootstrapped True")
check(f["is_laravel"] is True, "is_laravel set after a scaffold")

# ═════ Scenario 18: bootstrap refusal is fatal, not a silent retry ═════
print("\n── Scenario 18: bootstrap refusal → crash net, workspace removed ──")
reset_calls(119)
patch_tools(docker_outcomes=[True], code_responses=[LARAVEL_CODE])
nodes.tool_laravel_bootstrap = lambda repo_path: {
    "success": False,
    "error": "repository has composer.json but no artisan: not a Laravel app "
             "and not greenfield"}
_bootstrap_raised = ""
try:
    compiled.invoke(initial(119), config={"recursion_limit": 60})
except RuntimeError as exc:
    _bootstrap_raised = str(exc)
check("not a Laravel app" in _bootstrap_raised,
      "a foreign PHP repository raises instead of being scaffolded over")
check(calls["docker"] == 0, "no coding or testing attempted after the refusal")
check(not os.path.exists(calls["workspaces"][0]),
      "node_bootstrap removed its workspace before raising (no tempdir leak)")

# ═════ Scenario 12: nodes/edges testable in isolation (total=False state) ═════
print("\n── Scenario 12: isolated node/edge tests with partial state ──")
r = nodes.node_test({})   # empty state – every field optional
check(r == {"test_passed": False,
            "test_output": nodes._NO_FILE_BLOCKS_OUTPUT}, "node_test runs on empty state")
check(nodes.node_detect_stack({}) ==
      {"has_vue_files": False, "stack": "unknown",
       "run_phpunit": True, "run_openapi": False},
      "node_detect_stack defers to the files_written guard on empty state")
check(route_after_detect_stack({"run_phpunit": True}) == "phpunit_test",
      "edge: php-bearing stack → phpunit_test")
check(route_after_detect_stack({"run_phpunit": False, "stack": "vue"}) == "vitest_test",
      "edge: vue stack → vitest_test (PHPUnit bypassed)")
check(route_after_detect_stack({}) == "phpunit_test", "edge: default → phpunit_test")
check(route_after_phpunit({"test_passed": True}) == "commit", "edge: pass, no vue → commit")
check(route_after_phpunit({"test_passed": True, "run_openapi": True}) == "openapi_test",
      "edge: pass + API touched → openapi_test")
check(route_after_phpunit({"test_passed": True, "run_openapi": True,
                           "has_vue_files": True}) == "openapi_test",
      "edge: OpenAPI precedes the frontend layers")
check(route_after_phpunit({"test_passed": True, "has_vue_files": True}) == "vitest_test",
      "edge: pass + vue → vitest_test")
check(route_after_phpunit({"test_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_layer_failure", "edge: fail + retries → on_layer_failure")
check(route_after_phpunit({"test_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: fail + exhausted → failure")
check(route_after_openapi({"openapi_passed": True}) == "commit",
      "edge: openapi pass, no vue → commit")
check(route_after_openapi({"openapi_passed": True, "has_vue_files": True}) == "vitest_test",
      "edge: openapi pass + vue → vitest_test")
check(route_after_openapi({"openapi_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_layer_failure", "edge: openapi fail + retries → on_layer_failure")
check(route_after_openapi({"openapi_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: openapi fail + exhausted → failure")
check(route_after_vitest({"vitest_passed": True}) == "playwright_test",
      "edge: vitest pass → playwright_test")
check(route_after_vitest({"vitest_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_layer_failure", "edge: vitest fail + retries → escalation")
check(route_after_vitest({"vitest_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: vitest fail + exhausted → failure")
check(route_after_playwright({"playwright_passed": True}) == "commit",
      "edge: playwright pass → commit")
check(route_after_playwright({"playwright_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_layer_failure", "edge: playwright fail + retries → escalation")
check(route_after_playwright({"playwright_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: playwright fail + exhausted → failure")
check(nodes._last_failure_output(
          {"openapi_passed": False, "openapi_output": "Undocumented API routes:\n- X"}
      )[0] == "OpenAPI documentation",
      "_last_failure_output labels an OpenAPI failure")
check(nodes._last_failure_output(
          {"openapi_passed": False, "openapi_output": "o",
           "playwright_passed": False, "playwright_output": "p"}
      )[0] == "Playwright (E2E tests)",
      "_last_failure_output prefers the newest failing layer")
check(route_after_plan({"plan": "do X"}) == "code", "edge: plan → code")
check(route_after_plan({}) == "failure", "edge: empty plan → failure")
r = nodes.node_cleanup({})
check(r == {}, "node_cleanup safe with no workspace")

# ═════ Scenario 12b: retries must not accumulate renamed files ═════
print("\n── Scenario 12b: _prune_stale_files ──")
prune_root = tempfile.mkdtemp(prefix="nesti-prune-")
try:
    os.makedirs(os.path.join(prune_root, "database", "migrations"))
    os.makedirs(os.path.join(prune_root, "app", "Http", "Controllers", "Api"))
    old_migration = os.path.join("database", "migrations", "2025_01_01_000000_create_tasks_table.php")
    new_migration = os.path.join("database", "migrations", "2025_01_15_120000_create_tasks_table.php")
    old_controller = os.path.join("app", "Http", "Controllers", "Api", "TaskController.php")
    for rel in (old_migration, new_migration, old_controller):
        open(os.path.join(prune_root, rel), "w").close()

    removed = nodes._prune_stale_files(
        [old_migration, old_controller], [new_migration, old_controller], prune_root
    )
    check(removed == [old_migration],
          "a renamed migration from the previous attempt is deleted")
    check(not os.path.exists(os.path.join(prune_root, old_migration)),
          "the duplicate create_tasks_table migration is gone (no 'table already exists')")
    check(os.path.isfile(os.path.join(prune_root, new_migration)),
          "the attempt's own migration survives")
    check(os.path.isfile(os.path.join(prune_root, old_controller)),
          "a re-emitted file is never deleted")

    # A renamed package must not leave an empty tree in the Merge Request.
    removed = nodes._prune_stale_files([old_controller], [], prune_root)
    check(removed == [old_controller], "an omitted file is reported as removed")
    check(not os.path.isdir(os.path.join(prune_root, "app", "Http", "Controllers", "Api")),
          "directories left empty by the prune are removed too")
    check(os.path.isdir(os.path.join(prune_root, "database", "migrations")),
          "non-empty directories are kept")

    check(nodes._prune_stale_files(["../../etc/passwd"], [], prune_root) == [],
          "a path escaping the clone is refused")
    check(nodes._prune_stale_files([], [new_migration], prune_root) == [],
          "first attempt prunes nothing")
finally:
    shutil.rmtree(prune_root, ignore_errors=True)

store_msg = nodes._store.append_test_failure(999, "boom", layer="OpenAPI documentation")[-1]
check("OpenAPI documentation layer FAILED" in store_msg["content"],
      "retry feedback names the failing layer")
check("COMPLETE set of files" in store_msg["content"],
      "retry feedback demands the complete file set (pruning depends on it)")
nodes._store.delete(999)

# ═════ Scenario 12c: the coder must see what the repository already has ═════
print("\n── Scenario 12c: _repo_inventory ──")
inv_root = tempfile.mkdtemp(prefix="nesti-inv-")
try:
    check(nodes._repo_inventory(os.path.join(inv_root, "missing")) == "",
          "a missing workspace yields no section (never raises)")
    check("freshly scaffolded" in nodes._repo_inventory(inv_root),
          "an empty Laravel clone is described as having no feature code")

    os.makedirs(os.path.join(inv_root, "database", "migrations"))
    os.makedirs(os.path.join(inv_root, "app", "Models"))
    os.makedirs(os.path.join(inv_root, "routes"))
    open(os.path.join(inv_root, "database", "migrations",
                      "2025_01_01_000000_create_tasks_table.php"), "w").close()
    open(os.path.join(inv_root, "app", "Models", "Task.php"), "w").close()
    with open(os.path.join(inv_root, "routes", "api.php"), "w") as fh:
        fh.write("<?php\nRoute::get('/tasks', [TaskController::class, 'index']);\n")

    inv = nodes._repo_inventory(inv_root)
    check("2025_01_01_000000_create_tasks_table.php" in inv,
          "existing migrations are listed (duplicate create-table is unrecoverable)")
    check("Task.php" in inv, "existing models are listed")
    check("Route::get('/tasks'" in inv,
          "routes/api.php is quoted so the coder sees the registered URIs")
    check("do not add a create-table migration" in inv,
          "the inventory states the rule, not just the file list")

    # The section must actually reach the coder prompt.
    import prompt_builder as pb
    _, code_user = pb.build_code_prompt(
        {"id": 1, "subject": "s", "description": "d"}, "plan", repo_context=inv)
    check("## Existing Repository State" in code_user,
          "the inventory is rendered into the coding prompt")
    check("Never write a create-table migration for a table listed there" in code_user,
          "the coding prompt forbids duplicating an existing table")
    _, plan_user = pb.build_plan_prompt(
        {"id": 1, "subject": "s", "description": "d"}, repo_context=inv)
    check("## Existing Repository State" in plan_user,
          "the inventory is rendered into the planning prompt")
    _, bare = pb.build_code_prompt({"id": 1, "subject": "s", "description": "d"}, "plan")
    check("## Existing Repository State" not in bare,
          "no inventory, no section (backwards compatible)")
finally:
    shutil.rmtree(inv_root, ignore_errors=True)

# ═════ Scenario 12d: GitLab Issues intake (label state model) ═════
print("\n── Scenario 12d: GitLabIssuesClient intake ──")
os.environ["GITLAB_URL"] = "https://gitlab.test"
os.environ["GITLAB_TOKEN"] = "t"
os.environ["GITLAB_PROJECT_PATH"] = "ai/hello-world"
os.environ["GITLAB_ISSUE_LABEL"] = "nesti"
import gitlab_issues_client as gic  # noqa: E402


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


client = gic.GitLabIssuesClient()
check(client.issue_label == "nesti" and client.in_progress_label == "nesti::in-progress",
      "lock label is derived from the opt-in label as a scoped label")
check("ai%2Fhello-world" in client._project_api,
      "project path is URL-encoded for the API")

# list_pending must drop the already-locked issue: GitLab cannot express
# "has label A but not label B" in one query, so the filter is client-side.
_listing = [
    {"iid": 7, "title": "Pending one", "description": "d7",
     "labels": ["nesti"], "state": "opened", "web_url": "u7"},
    {"iid": 8, "title": "Already taken", "description": "d8",
     "labels": ["nesti", "nesti::in-progress"], "state": "opened", "web_url": "u8"},
    {"iid": 9, "title": "Pending two", "description": "d9",
     "labels": ["nesti", "bug"], "state": "opened", "web_url": "u9"},
]
_sent: dict = {}


def _fake_get(url, params=None, timeout=None):
    _sent["url"] = url
    _sent["params"] = params or {}
    return _FakeResponse(_listing)


client.session.get = _fake_get
pending = client.list_pending()
check([i["id"] for i in pending] == [7, 9],
      "an issue already carrying the lock label is not offered again")
check(_sent["params"].get("labels") == "nesti"
      and _sent["params"].get("state") == "opened",
      "the opt-in label and open state are filtered server-side")
check(_sent["params"].get("sort") == "asc", "oldest issue first")

# The normalised shape is what skill_loader / prompt_builder / the nodes read.
first = pending[0]
check(first["id"] == 7 and first["subject"] == "Pending one" and first["description"] == "d7",
      "GitLab iid/title map onto the id/subject/description intake contract")
check(first["iid"] == 7 and first["labels"] == ["nesti"] and first["web_url"] == "u7",
      "GitLab-specific fields are carried alongside, not instead")
check(client.get_next_issue()["id"] == 7, "get_next_issue returns the oldest pending issue")

client.session.get = lambda *a, **k: _FakeResponse([])
check(client.get_next_issue() is None, "no labelled issue means no work")

# Every mutation is verified by reading the issue back — the Redmine intake
# this replaces trusted the HTTP status and silently stranded issues.
def _put_returning(payload):
    def _put(url, json=None, timeout=None):
        _sent["payload"] = json
        return _FakeResponse(payload)
    return _put


client.session.put = _put_returning({"iid": 7, "labels": ["nesti", "nesti::in-progress"],
                                     "state": "opened"})
check(client.lock_issue(7) is True, "lock succeeds when the label really appears")
check(_sent["payload"] == {"add_labels": "nesti::in-progress"},
      "lock adds the label instead of replacing the label set")

client.session.put = _put_returning({"iid": 7, "labels": ["nesti"], "state": "opened"})
check(client.lock_issue(7) is False,
      "a lock that did not apply is reported as failure, never as success")

client.session.post = lambda *a, **k: _FakeResponse({}, 201)
client.session.put = _put_returning({"iid": 7, "labels": ["nesti"], "state": "closed"})
check(client.close_issue(7, note="done") is True, "close succeeds when state becomes closed")
check(_sent["payload"]["state_event"] == "close"
      and _sent["payload"]["remove_labels"] == "nesti::in-progress",
      "closing also drops the lock label")

client.session.put = _put_returning({"iid": 7, "labels": ["nesti"], "state": "opened"})
check(client.reopen_issue(7, note="failed") is True, "reopen returns the issue to pending")
check(_sent["payload"]["remove_labels"] == "nesti::in-progress"
      and _sent["payload"]["add_labels"] == "nesti"
      and _sent["payload"]["state_event"] == "reopen",
      "reopen drops the lock, re-asserts the opt-in label and reopens")

client.session.put = _put_returning({"iid": 7, "labels": ["nesti", "nesti::in-progress"],
                                     "state": "opened"})
check(client.reopen_issue(7) is False,
      "a lock that survives the reopen is a failure – the issue would never be retried")

# A failed note must never fail the transition itself.
def _raising_post(*a, **k):
    raise RuntimeError("notes endpoint down")


client.session.post = _raising_post
client.session.put = _put_returning({"iid": 7, "labels": ["nesti"], "state": "closed"})
check(client.close_issue(7, note="x") is True,
      "an unpostable note does not fail the close")

# ═════ Scenario 13: TaskEngine thin wrapper ═════
print("\n── Scenario 13: TaskEngine.run_once() ──")
import task_engine  # noqa: E402
reset_calls(111)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
task_engine.tool_issue_list_pending = lambda: {
    "success": True,
    "result": [{"id": 111, "subject": "Wrapper test", "description": "d"}]}
task_engine.tool_issue_set_status = nodes.tool_issue_set_status
engine = task_engine.TaskEngine()
check(engine.run_once() is True, "run_once returns True when MR opened")
check(calls["docker"] == 1, "graph executed via wrapper")
task_engine.tool_issue_list_pending = lambda: {"success": True, "result": []}
check(engine.run_once() is False, "run_once returns False when no pending issues")

# ═════ Static acceptance checks ═════
print("\n── Static acceptance checks ──")
src = open("task_engine.py").read()
import ast
imported = set()
for stmt in ast.walk(ast.parse(src)):
    if isinstance(stmt, ast.ImportFrom):
        imported.update(a.name for a in stmt.names)
        imported.add(stmt.module or "")
    elif isinstance(stmt, ast.Import):
        imported.update(a.name for a in stmt.names)
check(not imported & {"GitLabIssuesClient", "GitLabClient", "DockerRunner",
                      "FrontendRunner", "gitlab_issues_client", "gitlab_client",
                      "docker_runner", "frontend_runner", "llm_client"},
      "task_engine.py has no direct client imports")
check("redmine" not in src.lower(),
      "task_engine.py carries no Redmine residue")
check("from graph.builder import graph" in src, "task_engine imports graph.builder.graph")
node_names = set(compiled.get_graph().nodes)
check({"setup", "bootstrap", "load_skills", "plan", "code", "detect_stack",
       "phpunit_test", "openapi_test", "vitest_test", "playwright_test",
       "on_layer_failure", "commit", "failure", "cleanup"} <= node_names,
      "all 14 nodes registered")
check(not {"on_test_failure", "on_frontend_test_failure"} & node_names,
      "the two old escalation nodes are gone (one on_layer_failure replaces both)")
import graph.tools as tools_mod
import inspect
tool_fns = [f for n, f in inspect.getmembers(tools_mod, inspect.isfunction)
            if n.startswith("tool_")]
check(len(tool_fns) == 16, "16 MCP tool functions defined")
check("langgraph" not in inspect.getsource(tools_mod), "tools.py has no LangGraph imports")

env_example = open(".env.example").read()
for var in ("DOCKER_SANDBOX_PHP_IMAGE", "DOCKER_SANDBOX_NODE_IMAGE",
            "DOCKER_SANDBOX_E2E_IMAGE", "NESTI_LARAVEL_VERSION",
            "DOCKER_SANDBOX_BOOTSTRAP_TIMEOUT"):
    check(var in env_example, f"{var} present in .env.example")
check("DOCKER_SANDBOX_IMAGE=" not in env_example,
      "legacy DOCKER_SANDBOX_IMAGE removed from .env.example")
runner_src = open("docker_runner.py").read()
check("DOCKER_SANDBOX_PHP_IMAGE" in runner_src and "DOCKER_SANDBOX_IMAGE\"" not in runner_src,
      "docker_runner.py reads DOCKER_SANDBOX_PHP_IMAGE")
check(all(s in runner_src for s in ("detach=True", "wait(timeout=",
                                    "remove(force=True)", "finally:")),
      "docker_runner keeps the detach → wait → logs → finally:remove sequence")

# ── Phase 5: role, pins and the vendored corpus ──────────────────────────────
import prompt_builder                              # noqa: E402
coding = prompt_builder.CODING_SYSTEM_PROMPT
for needle in ("@playwright/test", "1.50.0", "primevue/", "@primeuix/themes",
               "scramble:export", "routes/api.php"):
    check(needle in coding, f"CODING_SYSTEM_PROMPT mentions {needle!r}")
check("You MUST NOT create new database tables" not in coding,
      "the retired no-database rule is gone from the coding prompt")
check("DATABASE POLICY" in prompt_builder._RULES,
      "the six-point database policy replaced the no-schema rules")
check("{{" not in coding and "}}" not in coding,
      "no doubled f-string braces leaked into the rendered coding prompt")

if os.path.isfile(_registry_path):
    registry = json.load(open(_registry_path))
    check(len(registry["primevue"]["components"]) >= 85,
          f"registry ships {len(registry['primevue']['components'])} component docs (>= 85)")
    check(len(registry["laravel"]["topics"]) == 24, "registry ships 24 Laravel topics")
    slugs = {c["slug"] for c in registry["primevue"]["components"]}
    check({"datatable", "select", "organizationchart", "dialog", "inputtext",
           "datepicker", "button", "message", "chart"} <= slugs,
          "every component the live issues need is vendored")
else:
    print("  ⚠ SKIPPED registry static checks (corpus not generated)")

for rel in ("vite.config.js", "vitest.config.js", "playwright.config.js",
            "resources/js/app.js", "resources/views/app.blade.php",
            "routes/web.php", "routes/api.php",
            "tests/TestCase.php",
            "tests/Feature/OpenApiDocumentationTest.php"):
    check(os.path.isfile(os.path.join("templates", "laravel", rel)),
          f"bootstrap template templates/laravel/{rel} exists")
testcase_tpl = open(os.path.join("templates", "laravel", "tests", "TestCase.php")).read()
check("withoutVite()" in testcase_tpl,
      "scaffolded TestCase disables Vite (the PHP sandbox never builds assets)")
vitest_tpl = open(os.path.join("templates", "laravel", "vitest.config.js")).read()
check("'e2e/**'" in vitest_tpl,
      "generated vitest.config.js excludes e2e/** (Absolute Rule 20)")
pw_tpl = open(os.path.join("templates", "laravel", "playwright.config.js")).read()
check("php artisan serve" in pw_tpl,
      "generated playwright.config.js serves the real Laravel app")
check("Route::" not in open(os.path.join("templates", "laravel", "routes",
                                         "api.php")).read(),
      "the scaffolded /api surface starts empty and fully documented")

print(f"\nALL {passed_checks} CHECKS PASSED ✅")
