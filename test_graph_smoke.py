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
import re
import shutil
import tempfile

# ── Environment before any project import ────────────────────────────────────
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ["ANTHROPIC_API_ENABLED"] = "true"
os.environ["DEEPSEEK_API_ENABLED"] = "true"
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
        "plan_prompts": [], "plan_systems": [], "code_prompts": [], "code_systems": [],
        "memory_search": [], "memory_similar": [], "memory_remember_solution": [],
        "memory_remember_failure": [], "memory_forget": [], "memory_recall": [],
    })


def initial(issue_id: int, subject: str = "", description: str = "Implement the thing.") -> dict:
    subject = subject or f"Test issue {issue_id}"
    return {
        "issue": {"id": issue_id, "subject": subject, "description": description},
        "issue_id": issue_id, "subject": subject,
        "skills": [], "plan": "", "scope": "fullstack", "code_response": "", "repo_path": "",
        "branch_name": "", "workspace": "", "messages": [],
        "attempt": 0, "max_attempts": 3,
        "files_written": False, "written_files": [],
        "has_vue_files": False, "stack": "php", "run_phpunit": True, "run_frontend": False,
        "is_laravel": False, "bootstrapped": False,
        "has_api_routes": False, "run_openapi": False,
        "test_output": "", "test_passed": False,
        "openapi_passed": False, "openapi_output": "", "openapi_paths": [],
        "vitest_passed": False, "vitest_output": "",
        "playwright_passed": False, "playwright_output": "",
        "fixture_request": None, "dependency_status": "",
        "retrieved_chunks": 0, "past_solutions": 0, "recalled_failures": 0,
        "mr_url": "", "failure_reason": "", "error": "",
    }


def patch_tools(docker_outcomes, code_responses, plan_exc=None, code_exc_first=False,
                openapi_outcomes=(True,),
                vitest_outcomes=(True,), playwright_outcomes=(True,),
                laravel_repo: bool = False, bootstrap_created: bool = False,
                vue_repo: bool = False, plan_text: str = "",
                doc_chunks=(), similar_solutions=(), recalled=(),
                memory_error: str = ""):
    """
    Install fakes on graph.nodes (node functions resolve names at call time).

    ``laravel_repo`` makes the fake clone look like a Laravel application so the
    REAL tool_detect_stack reports is_laravel/has_api_routes.  It defaults to
    False on purpose: dropping a composer.json into every fake clone would turn
    the Vue-only scenario into "fullstack" and silently void that regression.

    The Phase 8 memory fixtures default to empty, so every scenario that does
    not ask for memory runs against a degraded (empty) memory layer — the
    regression net for graceful degradation.  ``memory_error`` makes every
    memory tool report a genuine failure instead.

    ``vue_repo`` puts an existing component into the clone, so a scenario can
    prove that a backend change in a repository WITH .vue files still skips
    the frontend layers.  ``plan_text`` replaces the fake planner's answer
    (e.g. to declare a scope on line 1).
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
        if vue_repo:
            os.makedirs(os.path.join(target_path, "resources", "js", "components"))
            open(os.path.join(target_path, "resources", "js", "components",
                              "Existing.vue"), "w").close()
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
        lambda text, mc=3, mt=2, mp=0: {"success": True, "result": []})
    nodes.tool_skill_catalog_status = lambda: {"success": True, "result": {
        "available": True, "components": 92, "topics": 66, "practices": 4,
        "primevue_version": "5.0.1", "laravel_branch": "13.x"}}

    def _layered(key, outcomes, pass_out, fail_out):
        def fake(workspace_path):
            calls[key] += 1
            calls["layers"].append(key)
            passed = outcomes[min(calls[key] - 1, len(outcomes) - 1)]
            result = {"passed": passed, "output": pass_out if passed else fail_out}
            if key == "playwright":
                result["fixture_request"] = None
            return {"success": True, "result": result}
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

    # Phase 8 memory fakes – record every call, return the fixtures.
    def _memory(key, record, result):
        calls[key].append(record)
        if memory_error:
            return {"success": False, "error": memory_error}
        return {"success": True, "result": result}

    nodes.tool_memory_search_docs = lambda text, stack="", limit=6: _memory(
        "memory_search", {"text": text, "stack": stack, "limit": limit}, list(doc_chunks))
    nodes.tool_memory_find_similar = lambda text, limit=2: _memory(
        "memory_similar", text, list(similar_solutions))
    nodes.tool_memory_recall_failures = lambda issue_id, text, attempt, limit=2: _memory(
        "memory_recall", {"issue_id": issue_id, "text": text, "attempt": attempt},
        list(recalled))
    nodes.tool_memory_remember_failure = lambda issue_id, attempt, layer, output: _memory(
        "memory_remember_failure",
        {"issue_id": issue_id, "attempt": attempt, "layer": layer, "output": output},
        {"stored": True})
    nodes.tool_memory_remember_solution = (
        lambda issue_id, subject, description, plan, stack, mr_url: _memory(
            "memory_remember_solution",
            {"issue_id": issue_id, "subject": subject, "plan": plan,
             "stack": stack, "mr_url": mr_url},
            {"stored": True}))
    nodes.tool_memory_forget_episodes = lambda issue_id: _memory(
        "memory_forget", issue_id, {"deleted": 0})

    # LLM fakes (instance attributes shadow bound methods)
    if plan_exc:
        def fail_plan(sp, up, messages=None):
            raise RuntimeError(plan_exc)
        nodes._llm.generate_plan = fail_plan
    else:
        def fake_plan(sp, up, messages=None):
            calls["plan_prompts"].append(up)
            calls["plan_systems"].append(sp)
            return plan_text or "1. Objective: implement Hello\n2. Files: src/Hello.php"
        nodes._llm.generate_plan = fake_plan

    seq = list(code_responses)

    def fake_code(system_prompt, user_prompt, messages=None):
        calls["code_prompts"].append(user_prompt)
        calls["code_systems"].append(system_prompt)
        if code_exc_first:
            raise RuntimeError("All coding providers exhausted.")
        return seq.pop(0) if len(seq) > 1 else seq[0]
    nodes._llm.generate_code = fake_code
    nodes._llm.escalate_coder = lambda: calls.__setitem__("escalate", calls["escalate"] + 1)


def run(issue_id, subject="", description="Implement the thing.", **kw):
    reset_calls(issue_id)
    patch_tools(**kw)
    final = compiled.invoke(initial(issue_id, subject, description),
                            config={"recursion_limit": 60})
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
    check(status["topics"] >= 60,
          f"catalog has {status['topics']} Laravel topic docs (>= 60)")
    check(status["practices"] >= 4,
          f"catalog has {status['practices']} practice docs (>= 4)")

    _registry = skill_catalog.load_registry()
    _rows = (_registry["primevue"]["components"] + _registry["primevue"]["pages"]
             + _registry["laravel"]["topics"] + _registry["practices"]["documents"])
    _missing = [row["path"] for row in _rows
                if not (skill_catalog.CATALOG_DIR / row["path"]).is_file()]
    check(not _missing,
          f"every registry row has a vendored file (missing {_missing[:3]})")

    titles = [s.title for s in skill_catalog.select_skills("use the PrimeVue DataTable")]
    check(titles[:1] == ["DataTable"], "DataTable selected first for a DataTable issue")

    picked = skill_catalog.select_skills("Replace the grid with a Dropdown")
    check(any(s.url.endswith("/select.md") for s in picked),
          "legacy name 'Dropdown' resolves to the PrimeVue 5 Select doc")
    picked = skill_catalog.select_skills("Pick the tags with a MultiSelect")
    check(any(s.url.endswith("/select.md") for s in picked),
          "v5-deprecated 'MultiSelect' resolves to its replacement, the Select doc")
    _titles = lambda text: [s.title for s in skill_catalog.select_skills(text)]  # noqa: E731
    check("Strings" in _titles("Normalise every SKU with Str::upper() before saving"),
          "a facade trigger ending in '::' fires on real code (Str::upper)")
    check("Select" not in _titles("Use a SelectButton for plans and a TreeSelect for categories"),
          "alphanumeric word boundaries still hold on both sides (SelectButton/TreeSelect ≠ Select)")
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
              "DataTable Dialog Select Calendar Button", max_component_docs=2)) <= 2 + 2 + 1,
          "max_component_docs is honoured")

    _security = "Mask sensitive data in the JSON response of the audit log API"
    picked = skill_catalog.select_skills(_security)
    check(len(picked) >= 2 and picked[-1].title == "Application Security Engineering",
          "a security issue selects the security practice doc, after the API docs")
    check(all(not s.content.lstrip().startswith("---") for s in picked),
          "practice front matter never reaches the prompt")
    check("Application Security Engineering" not in [
              s.title for s in skill_catalog.select_skills(_security, max_practice_docs=0)],
          "max_practice_docs=0 suppresses the practice lane entirely")
    picked = skill_catalog.select_skills("write a failing test first, then red green refactor")
    check(any(s.title == "Test-Driven Development" for s in picked),
          "TDD wording selects the test-driven-development practice doc")

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

# ═════ Scenario 24: issue scope — classification, declaration, documentation ═════
print("\n── Scenario 24: issue_scope ──")
from issue_scope import (  # noqa: E402
    SCOPES, classify_issue, declared_scope, documentation_request, widen,
)

# ISSUE_GUIDELINE.md examples 1–4 (abridged to the lines that carry the signal).
_GUIDELINE_EXAMPLES = (
    ("Add a paginated /api/tasks endpoint backed by a tasks table",
     "- New migration creating a `tasks` table.\n- `GET /api/tasks` paginated 10 per page, "
     "returning a `TaskResource` collection.\n- Feature tests for both routes.", "backend"),
    ("Show the task list with a PrimeVue DataTable component",
     "- `resources/js/components/TaskTable.vue` fetching `GET /api/tasks`.\n"
     "- PrimeVue `DataTable` + `Column` for `title`, `due_date` and `is_done`.", "frontend"),
    ("Add a PrimeVue Dialog form that creates a task",
     "- `resources/js/components/TaskCreateDialog.vue` using PrimeVue `Dialog`.\n"
     "- Posts to `POST /api/tasks`.", "frontend"),
    ("Fix incorrect total price calculation when a discount coupon is applied",
     "- Fix the rounding logic in app/Services/CartService.php.\n"
     "- Do NOT change the database schema.\n- Add a PHPUnit Feature test.", "backend"),
)
for _subject, _description, _expected in _GUIDELINE_EXAMPLES:
    _decision = classify_issue(_subject, _description)
    check(_decision.scope == _expected,
          f"{_subject[:44]!r} → {_expected} (got {_decision.scope}: {_decision.evidence()})")
check(classify_issue("Change the green button colour to orange", "").scope == "frontend",
      "a button colour change is frontend work")
check(classify_issue("Add a /api/ping endpoint for uptime checks", "").scope == "backend",
      "a trial endpoint is backend work")
check(classify_issue("Add a /api/tasks/{id}/complete endpoint and a Complete button", "").scope
      == "fullstack", "an endpoint plus the button that calls it is fullstack")
check(classify_issue("Implement the thing", "").scope == "fullstack",
      "no signal → fullstack, the prompt every issue received before scopes")
check(classify_issue("Polish the totals", "Do NOT change the database schema.").scope
      == "fullstack", "a negated mention is not a signal")
check(classify_issue("Show the Save button", "Scope: backend").scope == "backend",
      "an explicit 'Scope:' line wins over the signals")
check(classify_issue("Speed up the task list", "No frontend changes.").scope == "backend",
      "'no frontend changes' selects the backend")

check(declared_scope("**SCOPE:** Frontend\n\n1. Objective") == "frontend",
      "a markdown-wrapped SCOPE line on line 1 is read")
check(declared_scope("# Plan\n\nScope: full-stack\n1. Objective") == "fullstack",
      "the declaration may follow a heading")
check(declared_scope("1. Objective\n2. a\n3. b\n4. c\n5. d\nSCOPE: backend") is None,
      "a SCOPE line deep inside the plan is prose, not the declaration")
check(declared_scope("1. Objective: implement Hello") is None, "no declaration → None")
check(widen("backend", "frontend") == "fullstack" and widen("frontend", "frontend") == "frontend"
      and widen("fullstack", "backend") == "fullstack" and widen("backend", "") == "backend",
      "widen covers both sides and never narrows")

check(documentation_request("Add a /api/ping endpoint", "Return ok.") == "",
      "a new endpoint is not a documentation request")
check(documentation_request("Add /api/ping and describe it in the README", "") == "readme",
      "naming the README is a documentation request")
check(documentation_request("Add /api/ping", "Do not touch the README.") == "",
      "a negated README mention is not a request")
check(documentation_request("Show tasks", "https://primevue.dev/llms/components/datatable.md")
      == "", "a skill URL ending in .md is not a documentation request")
check(documentation_request("Add /api/tasks", "The OpenAPI documentation must list it.") == "",
      "OpenAPI documentation is Scramble's job, not a documentation file")

import prompt_builder as _scoped  # noqa: E402
_button = {"id": 5, "subject": "Change the green button colour to orange", "description": ""}
_plan_sys = {s: _scoped.build_plan_prompt(_button, scope=s)[0] for s in SCOPES}
_plan_user = {s: _scoped.build_plan_prompt(_button, scope=s)[1] for s in SCOPES}
_code_sys = {s: _scoped.build_code_prompt(_button, "plan", scope=s)[0] for s in SCOPES}
check(all(f"TASK SCOPE: {s}" in _plan_sys[s] and f"TASK SCOPE: {s}" in _code_sys[s]
          for s in SCOPES), "both system prompts carry the TASK SCOPE block of their scope")
check(not any(section in _code_sys["frontend"] or section in _plan_sys["frontend"]
              for section in ("DATABASE POLICY", "LARAVEL BACKEND", "API DOCUMENTATION")),
      "a frontend issue gets no database policy and no Laravel/Scramble standards")
check(not any(section in _code_sys["backend"]
              for section in ("PRIMEVUE FRONTEND", "@playwright/test", "getByRole")),
      "a backend issue gets no PrimeVue standards and no Playwright instructions")
check(all(section in _code_sys["fullstack"]
          for section in ("DATABASE POLICY", "LARAVEL BACKEND", "PRIMEVUE FRONTEND")),
      "fullstack keeps both standards")
check("Database changes" not in _plan_user["frontend"] and "Frontend files" in _plan_user["frontend"]
      and "Frontend files" not in _plan_user["backend"] and "Database changes" in _plan_user["backend"],
      "the plan structure only asks for the sections of its scope")
check(all(f"Line 1 of the plan, alone: SCOPE: {s}" in _plan_user[s] for s in SCOPES),
      "the planner is asked to declare the scope on line 1")
check(all("Documentation is out of scope" in p and "README.md" in p
          for p in list(_plan_sys.values()) + list(_code_sys.values())),
      "every prompt keeps README.md out of an issue that does not ask for it")
_docs_sys = _scoped.build_code_prompt(
    {"id": 6, "subject": "Add /api/ping and describe it in the README", "description": ""},
    "plan", scope="backend")[0]
check("Documentation is out of scope" not in _docs_sys
      and 'asks for documentation ("readme")' in _docs_sys,
      "an issue that names the README gets it back in scope, limited to what it asks")

# ═════ Scenario 25: the layers follow the change, not the repository ═════
print("\n── Scenario 25: change-aware layer gates ──")
_gate_repo = tempfile.mkdtemp(prefix="nesti-gates-")
try:
    os.makedirs(os.path.join(_gate_repo, "resources", "js", "components"))
    open(os.path.join(_gate_repo, "artisan"), "w").close()
    open(os.path.join(_gate_repo, "composer.json"), "w").close()
    _existing_vue = os.path.join(_gate_repo, "resources", "js", "components", "TaskTable.vue")
    open(_existing_vue, "w").close()

    def _gates(written):
        r = tool_detect_stack(_gate_repo, written)["result"]
        return r["run_phpunit"], r["run_frontend"]

    check(_gates(["app/Http/Controllers/PingController.php", "routes/api.php",
                  "tests/Feature/PingTest.php"]) == (True, False),
          "a backend change in a repository WITH .vue files skips Vitest and Playwright")
    check(_gates(["resources/js/components/TaskTable.vue",
                  "resources/js/components/__tests__/TaskTable.test.js",
                  "e2e/tasks.spec.js"]) == (False, True),
          "a frontend-only change skips PHPUnit")
    check(_gates(["resources/views/app.blade.php"]) == (True, True),
          "a Blade view is PHP that serves a page: both sides run")
    check(_gates(["app/Models/Task.php", "resources/js/components/TaskTable.vue"]) == (True, True),
          "a change on both sides runs every layer")
    check(_gates(["README.md"]) == (True, False),
          "a change on neither side still runs PHPUnit — never commits untested")
    check(_gates(None) == (True, True), "written_files=None → every layer (MCP callers)")
    os.remove(_existing_vue)
    check(_gates(["resources/js/app.js"]) == (True, False),
          "a JavaScript change in a repository without Vue falls back to PHPUnit")
finally:
    shutil.rmtree(_gate_repo, ignore_errors=True)

# ═════ Scenario 26: scope end-to-end — SCOPE line, prompts, layers, widening ═════
print("\n── Scenario 26: scope through the graph ──")
BUTTON_CODE = (
    "### FILE: resources/js/components/SaveButton.vue\n"
    "```vue\n<template><Button severity=\"warn\" label=\"Save\"/></template>\n```\n\n"
    "### FILE: resources/js/components/__tests__/SaveButton.test.js\n```js\n// vitest\n```\n\n"
    "### FILE: e2e/save-button.spec.js\n```js\n// playwright\n```\n"
)
BLADE_BUTTON_CODE = (
    "### FILE: resources/views/app.blade.php\n```blade\n<div id=\"app\"><save-button/></div>\n```\n\n"
    + BUTTON_CODE
)


class _ScopeLines(logging.Handler):
    """Collects the graph.nodes SCOPE lines whatever LOG_LEVEL the run uses."""

    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, record):
        if record.getMessage().startswith("SCOPE:"):
            self.lines.append(record.getMessage())


def run_logged(issue_id, **kw):
    """run() with the SCOPE lines of that run captured."""
    handler, node_logger = _ScopeLines(), logging.getLogger("graph.nodes")
    previous_level = node_logger.level
    node_logger.addHandler(handler)
    node_logger.setLevel(logging.DEBUG if previous_level == logging.DEBUG else logging.INFO)
    try:
        return run(issue_id, **kw), handler.lines
    finally:
        node_logger.removeHandler(handler)
        node_logger.setLevel(previous_level)


f, scope_lines = run_logged(
    2601, subject="Add a /api/ping endpoint for uptime checks", description="Return ok.",
    docker_outcomes=[True], code_responses=[LARAVEL_CODE], laravel_repo=True, vue_repo=True)
check(len(scope_lines) == 1 and scope_lines[0].startswith("SCOPE: backend · GitLab issue #2601 · "),
      f"exactly one SCOPE line per run, final scope and issue number first ({scope_lines})")
check(calls["layers"] == ["docker", "openapi"],
      f"backend issue in a Vue repository: PHPUnit → OpenAPI only (got {calls['layers']})")
check(f["scope"] == "backend" and not any("PRIMEVUE FRONTEND" in p for p in
                                          calls["plan_systems"] + calls["code_systems"]),
      "a backend issue's plan and code prompts carry no PrimeVue standards")
check("scope: backend" in calls["mrs"][0], "the MR body reports the scope")

f, scope_lines = run_logged(
    2602, subject="Change the green button colour to orange", description="",
    docker_outcomes=[True], code_responses=[BUTTON_CODE], laravel_repo=True, vue_repo=True)
check(f["scope"] == "frontend" and calls["layers"] == ["vitest", "playwright"],
      f"button colour change: frontend scope, Vitest → Playwright, no PHPUnit (got {calls['layers']})")
check(not any("DATABASE POLICY" in p for p in calls["plan_systems"] + calls["code_systems"]),
      "a frontend issue's prompts carry no database policy")
check(f["mr_url"] == "https://gitlab.example/mr/2602", "frontend-only change reaches its MR")

f, scope_lines = run_logged(
    2603, subject="Change the green button colour to orange", description="",
    plan_text="**SCOPE:** fullstack\n1. Objective: orange button",
    docker_outcomes=[True], code_responses=[BUTTON_CODE], laravel_repo=True, vue_repo=True)
check(f["scope"] == "fullstack" and "LARAVEL BACKEND" in calls["code_systems"][0],
      "the coder follows the scope the planner declared")
check(len(scope_lines) == 1 and scope_lines[0].startswith("SCOPE: fullstack · GitLab issue #2603")
      and "issue text: frontend" in scope_lines[0] and scope_lines[0].endswith("planner: fullstack"),
      f"the SCOPE line shows the final scope and both sources ({scope_lines})")

f, _ = run_logged(
    2604, subject="Change the green button colour to orange", description="",
    plan_text="SCOPE: frontend\n1. Objective: orange button",
    docker_outcomes=[False, True], code_responses=[BLADE_BUTTON_CODE],
    laravel_repo=True, vue_repo=True)
check(calls["layers"] == ["docker", "docker", "vitest", "playwright"],
      f"a Blade view puts PHPUnit in front of the frontend layers (got {calls['layers']})")
check("LARAVEL BACKEND" not in calls["code_systems"][0]
      and "LARAVEL BACKEND" in calls["code_systems"][1] and f["scope"] == "fullstack",
      "a red PHPUnit layer widens a frontend scope to fullstack for the retry")
check(f["mr_url"] == "https://gitlab.example/mr/2604", "the widened retry reaches its MR")

# The layer set changes between attempts (Vitest on attempt 1, PHPUnit on
# attempt 2): attempt 2's red PHPUnit must be fed back as PHPUnit — not as the
# stale Vitest output of attempt 1 — and attempt 1's Vitest output must not
# reach the MR body of code it never ran on.
f = run(2605, subject="Change the green button colour to orange", description="",
        docker_outcomes=[False, True], vitest_outcomes=[False],
        code_responses=[BUTTON_CODE, LARAVEL_CODE, LARAVEL_CODE],
        laravel_repo=True, vue_repo=True)
check([(e["attempt"], e["layer"]) for e in calls["memory_remember_failure"]]
      == [(1, "Vitest (component tests)"), (2, "PHPUnit")],
      "each attempt's failure is reported as its own layer, never a stale earlier one")
check(f["scope"] == "fullstack", "the PHPUnit failure widened the frontend scope")
check(f["mr_url"] and "### Vitest" not in calls["mrs"][0],
      "the MR body lists only the layers that ran on the merged code")

# ═════ Scenario 19: Phase 8 hierarchical memory end-to-end ═════
print("\n── Scenario 19: Phase 8 hierarchical memory end-to-end ──")
_CHUNKS = [
    {"doc_title": "Database: Migrations", "heading": "Creating Tables",
     "doc_url": "https://raw.githubusercontent.com/laravel/docs/13.x/migrations.md",
     "doc_path": "laravel/migrations.md", "source": "laravel", "stack": "php",
     "text": "# Database: Migrations\n## Creating Tables\n\nUse Schema::create.",
     "score": 0.81},
    {"doc_title": "HTTP Tests", "heading": "Testing JSON APIs",
     "doc_url": "https://raw.githubusercontent.com/laravel/docs/13.x/http-tests.md",
     "doc_path": "laravel/http-tests.md", "source": "laravel", "stack": "php",
     "text": "# HTTP Tests\n## Testing JSON APIs\n\nUse getJson and assertJson.",
     "score": 0.74},
]
_SOLUTIONS = [{"issue_id": 77, "subject": "Add hello endpoint", "similarity": 0.91,
               "mr_url": "https://gitlab.example/mr/77", "stack": "php",
               "plan": "1. Objective: say hello from PAST-PLAN-MARKER"}]
_RECALLED = [{"issue_id": 119, "attempt": 1, "layer": "PHPUnit", "similarity": 0.88,
              "summary": "EARLIER-FAILURE-MARKER: no such table hello"}]
f = run(1190, docker_outcomes=[False, False, True], code_responses=[GOOD_CODE],
        doc_chunks=_CHUNKS, similar_solutions=_SOLUTIONS, recalled=_RECALLED)
check(f["mr_url"] == "https://gitlab.example/mr/1190" and f["attempt"] == 3,
      "memory-enabled issue reaches its MR on attempt 3")
check(len(calls["memory_similar"]) == 1 and "Test issue 1190" in calls["memory_similar"][0],
      "the solution cache is consulted once, at plan time, with the issue text")
check([c["stack"] for c in calls["memory_search"]] == ["", "", "php", "php"],
      "doc search: unfiltered at plan time and on attempt 1 (seeded stack ignored), "
      "stack=php once node_detect_stack has run")
check(len(calls["memory_recall"]) == 1 and calls["memory_recall"][0]["attempt"] == 3,
      "episodic recall runs only from attempt 3 (attempt 2 has nothing older than "
      "the failure already in the history)")
check("PHPUnit failure:" in calls["memory_recall"][0]["text"]
      and "PHPUnit FAILURES!" in calls["memory_recall"][0]["text"],
      "recall is queried with the failing layer and its (condensed) output")
check([(e["attempt"], e["layer"]) for e in calls["memory_remember_failure"]]
      == [(1, "PHPUnit"), (2, "PHPUnit")]
      and all("PHPUnit FAILURES!" in e["output"] for e in calls["memory_remember_failure"]),
      "each failed attempt is stored once with its layer and output")
check(len(calls["memory_remember_solution"]) == 1
      and calls["memory_remember_solution"][0]["mr_url"] == "https://gitlab.example/mr/1190"
      and calls["memory_remember_solution"][0]["plan"] == f["plan"]
      and calls["memory_remember_solution"][0]["stack"] == "php",
      "the merged plan is written back to the solution cache with the real MR URL")
check(calls["memory_forget"] == [1190], "episodes are dropped once the issue is done")
check(f["retrieved_chunks"] == 2 and f["past_solutions"] == 1 and f["recalled_failures"] == 1,
      "state counters report what reached the prompts")
check("## Past Nesti Experience" in calls["plan_prompts"][0]
      and "PAST-PLAN-MARKER" in calls["plan_prompts"][0],
      "past solutions are rendered into the plan prompt")
check(all("## Retrieved Reference Snippets" in p
          for p in calls["plan_prompts"] + calls["code_prompts"]),
      "retrieved doc chunks reach the plan prompt and every code prompt")
check(all("EARLIER-FAILURE-MARKER" not in p for p in calls["code_prompts"][:2])
      and "## Earlier Failed Attempts on This Issue" in calls["code_prompts"][2]
      and "EARLIER-FAILURE-MARKER" in calls["code_prompts"][2],
      "recalled failures appear only in the attempt-3 code prompt")
check("doc chunk(s)" in calls["mrs"][0] and "past solution(s)" in calls["mrs"][0]
      and "memory: 2 doc chunk(s), 1 past solution(s)" in calls["mrs"][0],
      "the MR body reports memory usage")

# Catalog de-duplication at node level is on CONTENT: a passage the keyword
# catalog already injected is dropped, but a passage of the same document that
# lies past the catalog's 7 000-char cap must survive — reaching it is the
# point of the vector index.
reset_calls(1191)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE], doc_chunks=_CHUNKS)
from skill_loader import Skill  # noqa: E402
_dedup = nodes._retrieve_chunks("x", [Skill(
    title="Database: Migrations", url=_CHUNKS[0]["doc_url"],
    content="# Database: Migrations\n\n## Creating Tables\n\nUse Schema::create.\n")])
check([c["doc_title"] for c in _dedup] == ["HTTP Tests"],
      "_retrieve_chunks drops a passage the catalog already injected")
_kept = nodes._retrieve_chunks("x", [Skill(
    title="Database: Migrations", url=_CHUNKS[0]["doc_url"],
    content="# Database: Migrations\n\n## Introduction\n\nOnly the first 7 000 chars.")])
check([c["doc_title"] for c in _kept] == ["Database: Migrations", "HTTP Tests"],
      "_retrieve_chunks keeps a passage of a catalog document that lies past its cap")

# ═════ Scenario 20: Phase 8 memory unavailable ═════
print("\n── Scenario 20: Phase 8 memory unavailable → pipeline unchanged ──")
f = run(1200, docker_outcomes=[False, False, True], code_responses=[GOOD_CODE],
        doc_chunks=_CHUNKS, similar_solutions=_SOLUTIONS, recalled=_RECALLED,
        memory_error="Qdrant and Redis are down")
check(f["mr_url"] == "https://gitlab.example/mr/1200",
      "an issue still reaches its MR when every memory tool fails")
check(f["retrieved_chunks"] == 0 and f["past_solutions"] == 0 and f["recalled_failures"] == 0,
      "no memory is counted when none was injected")
check("memory: 0 doc chunk(s), 0 past solution(s)" in calls["mrs"][0],
      "the MR body renders zero memory usage")
check(all("## Retrieved Reference Snippets" not in p and "## Past Nesti Experience" not in p
          and "## Earlier Failed Attempts" not in p
          for p in calls["plan_prompts"] + calls["code_prompts"]),
      "no memory section is rendered into any prompt")
check(len(calls["memory_remember_failure"]) == 2,
      "a failing episodic write never blocks the retry loop")

# ═════ Scenario 21: Phase 8 pure-function checks (no Redis, no Qdrant) ═════
print("\n── Scenario 21: Phase 8 formatters, chunker and degradation ──")
import prompt_builder as _pb  # noqa: E402
_url_x = "https://example/x.md"
_catalog_rendered = "### Skill: X\nSource: " + _url_x + "\n\n# X\n\n## H\n\nalready injected body\n"
check(_pb._format_retrieved_section(
          [{"doc_title": "X", "heading": "H", "doc_url": _url_x,
            "text": "# X\n## H\n\nalready injected body", "score": 0.9}],
          6000, exclude_text=_catalog_rendered) == "",
      "_format_retrieved_section drops a passage already in the catalog section")
check("past the cap" in _pb._format_retrieved_section(
          [{"doc_title": "X", "heading": "Deep", "doc_url": _url_x,
            "text": "# X\n## Deep\n\npast the cap", "score": 0.9}],
          6000, exclude_text=_catalog_rendered),
      "_format_retrieved_section keeps a same-document passage the catalog cut off")
_big = [{"doc_title": f"D{i}", "heading": "H", "doc_url": f"https://example/{i}.md",
         "text": "y" * 4000, "score": 0.9 - i / 10} for i in range(2)]
_rendered = _pb._format_retrieved_section(_big, 6000)
check(_rendered.count("\nSource: ") == 1 and "### D0 — H" in _rendered,
      "_format_retrieved_section skips (never truncates) a chunk over budget")
check(_pb._format_retrieved_section(
          [{"doc_title": "T", "heading": "H", "doc_url": "u",
            "text": "# T\n## H\n\nbody text", "score": 1.0}], 6000).count("# T\n## H") == 0,
      "the indexer's embedding context line is not repeated in the prompt")
check(_pb._format_solutions_section([], 4000) == "" and _pb._format_episodes_section([], 3000) == "",
      "empty memory renders no section")
_long_plan = "\n".join(f"{n}. step {'z' * 60}" for n in range(1, 120))
_sol = _pb._format_solutions_section(
    [{"issue_id": 5, "subject": "s", "similarity": 0.9, "mr_url": "u", "plan": _long_plan}], 4000)
check("### Issue #5: s" in _sol and "truncated" in _sol and len(_sol) < 4000 + 400,
      "an over-budget past plan is cut to fit rather than silently dropped")

from scripts.index_skills import chunk_document, _MAX_CHUNK_CHARS  # noqa: E402
_doc = "# Title\n\n## Alpha\n\n" + "a" * 300 + "\n\n## Beta\n\n" + "b" * 400 + "\n"
_chunks = chunk_document(_doc, "Title", "x/title.md")
check(len(_chunks) == 2 and all(c["text"].startswith("# Title\n## ") for c in _chunks),
      "chunk_document yields one chunk per ## section, each with its context line")
check([c["id"] for c in _chunks] == [c["id"] for c in chunk_document(_doc, "Title", "x/title.md")],
      "chunk ids are deterministic (re-indexing overwrites, never duplicates)")
_huge = "# T\n\n## Big\n\n" + "\n\n".join("p" * 700 for _ in range(10)) + "\n\n" + "q" * 5000
_hchunks = chunk_document(_huge, "T", "x/t.md")
check(len(_hchunks) > 3 and all(
          len(c["text"]) <= _MAX_CHUNK_CHARS + len(f"# T\n## {c['heading']}\n\n")
          for c in _hchunks),
      "long sections split on paragraphs, giant paragraphs hard-cut, all within the cap")
check(len(chunk_document("# Stub\n\nTiny page.", "Stub", "x/stub.md")) == 1,
      "a stub document still keeps one chunk (stays hash-tracked in the index)")

import embedding as _embedding  # noqa: E402
os.environ["NESTI_MEMORY_ENABLED"] = "false"
try:
    _off = _embedding.Embedder()
    check(_off.available is False and _off.embed_query("x") == []
          and _off.embed_documents(["x"]) == [],
          "NESTI_MEMORY_ENABLED=false: embedder unavailable, embeds return [] without raising")
finally:
    os.environ.pop("NESTI_MEMORY_ENABLED", None)

import semantic_cache as _sc  # noqa: E402
_sm = _sc.SemanticMemory()   # REDIS_URL points at 127.0.0.1:1 (unreachable)
check(_sm.available is False and _sm.find_similar_solutions("x") == []
      and _sm.remember_solution(1, "s", "d", "p", "php", "u") is False
      and _sm.recall_failures(1, "x", attempt=5) == [] and _sm.forget_episodes(1) == 0,
      "SemanticMemory degrades on an unreachable Redis: reads [], writes False")
check(_sm.status()["solutions"] is None and _sm.status()["engine"] == "unavailable",
      "unreadable memory counts are None, never guessed")

import vector_store as _vs  # noqa: E402
_php = [{"stack": "php", "score": 0.70, "doc_title": "Routing"},
        {"stack": "php", "score": 0.66, "doc_title": "Controllers"}]
_vue = [{"stack": "vue", "score": 0.69, "doc_title": "ToggleSwitch"},
        {"stack": "vue", "score": 0.68, "doc_title": "ToggleButton"},
        {"stack": "vue", "score": 0.67, "doc_title": "Gallery"}]
check([h["doc_title"] for h in _vs._interleave([_vue, _php], 4)]
      == ["Routing", "ToggleSwitch", "Controllers", "ToggleButton"],
      "an unfiltered doc search interleaves both stacks — the PrimeVue-heavy corpus "
      "cannot crowd the Laravel docs out of a backend issue's prompt")
check(_vs._interleave([[], _vue], 2) == _vue[:2] and _vs._interleave([[], []], 3) == [],
      "interleaving tolerates an empty stack")


class _LaneProbe(_vs.DocumentMemory):
    """DocumentMemory.search over a canned Qdrant: doc lanes score 0.60 and below."""

    def __init__(self, practice_scores):  # pylint: disable=super-init-not-called
        self._practice_scores = practice_scores
        self._url = "probe"
        self._collection_known = True

    @property
    def available(self):
        return True

    def _query(self, vector, stack, limit):
        scores = (self._practice_scores if stack == _vs.PRACTICE_STACK
                  else [0.60 - i / 100 for i in range(limit)])
        return [{"stack": stack, "score": s, "doc_title": f"{stack}{i}"}
                for i, s in enumerate(scores[:limit])]


_real_get_embedder = _vs.get_embedder
_vs.get_embedder = lambda: type("_Embedder", (), {"embed_query": staticmethod(lambda t: [0.1])})()
try:
    _hits = _LaneProbe([0.95] * 10).search("issue", stack="php", limit=8)
    check(len(_hits) == 8
          and sum(h["stack"] == _vs.PRACTICE_STACK for h in _hits) == 2
          and {h["stack"] for h in _hits} == {"php", _vs.PRACTICE_STACK},
          "practice passages that outscore every doc still get at most a quarter of the "
          "slots, and a stack-narrowed search stays on its stack")
    _hits = _LaneProbe([0.95, _vs._PRACTICE_MIN_SCORE - 0.01]).search("issue", limit=8)
    check([h["doc_title"] for h in _hits if h["stack"] == _vs.PRACTICE_STACK] == ["practice0"],
          "a practice passage below the relevance floor never reaches the prompt")
    check(not any(h["stack"] == _vs.PRACTICE_STACK
                  for h in _LaneProbe([0.95] * 10).search("issue", limit=3)),
          "below four slots the practice lane is dropped entirely")
finally:
    _vs.get_embedder = _real_get_embedder

# ═════ Scenario 22: coder chain escalation and per-issue reset ═════
print("\n── Scenario 22: coder escalation + per-issue reset ──")
from llm_client import LLMClient  # noqa: E402


class _StubCoder:
    def __init__(self, name, available=True, fail=False):
        self.name, self.label, self.available, self.fail = name, name, available, fail

    def generate_code(self, system_prompt, user_prompt, messages=None):
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return f"code from {self.name}"

    def generate_plan(self, system_prompt, user_prompt, messages=None):
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return f"plan from {self.name}"


_chain = LLMClient()
_a, _b, _c, _d = (_StubCoder("A", fail=True), _StubCoder("B", available=False),
                  _StubCoder("C"), _StubCoder("D"))
_chain._coders = [_a, _b, _c, _d]
check(_chain.generate_code("s", "u") == "code from C" and _chain.current_coder_name == "C",
      "an API failure cascades past the unavailable tier to the next live coder")
_chain.escalate_coder()
check(_chain.current_coder_name == "D",
      "a test failure escalates to a HIGHER tier than the one that produced the code "
      "(never 'C → C' after an API cascade)")
_d.fail = True
check(_chain.generate_code("s", "u") == "code from C",
      "a dead escalated tier falls back to the strongest untried tier below it "
      "instead of declaring the chain exhausted while a reachable coder was never asked")
_c.fail = True
try:
    _chain.generate_code("s", "u")
    _exhausted = False
except RuntimeError:
    _exhausted = True
check(_exhausted and _chain.current_coder_name == "none (all exhausted)",
      "every reachable coder failed → exhausted")
_a.fail = False
_chain.reset_coder_tier()
check(_chain.current_coder_name == "A" and _chain.generate_code("s", "u") == "code from A",
      "reset_coder_tier puts the next issue back on the head of the chain")

# The loop process keeps one LLMClient: a new issue must not inherit the
# previous issue's exhausted chain (observed live: attempt 1 of the next issue
# started at "none (all exhausted)" and failed without a single coder call).
nodes._llm._min_coder_tier = len(nodes._llm._coders)
nodes._llm._api_failed_coders = set(range(len(nodes._llm._coders)))
check(nodes._llm.current_coder_name == "none (all exhausted)", "precondition: chain exhausted")
f = run(1220, docker_outcomes=[True], code_responses=[GOOD_CODE])
check(f["mr_url"] == "https://gitlab.example/mr/1220"
      and nodes._llm.current_coder_name != "none (all exhausted)",
      "node_setup resets the coder chain at the start of every issue")

# Paid APIs must never be contacted when disabled, including below-floor
# fallback; flags are evaluated again on an already-constructed chain.
from unittest.mock import patch  # noqa: E402
from llm_client import AnthropicLLMClient, DeepSeekLLMClient  # noqa: E402

with patch.dict(os.environ, {
    "DEEPSEEK_API_KEY": "deepseek-test-key",
    "ANTHROPIC_API_KEY": "anthropic-test-key",
    "DEEPSEEK_API_ENABLED": "false",
    "ANTHROPIC_API_ENABLED": "false",
}), patch("llm_client.build_consumer_clients", return_value=[_StubCoder("Consumer")]), \
        patch("llm_client.requests.post") as _deep_http, \
        patch("llm_client.anthropic.Anthropic") as _anthropic_sdk:
    _deep_http.return_value.json.return_value = {
        "choices": [{"message": {"content": "deepseek answer"}}],
    }
    _anthropic_sdk.return_value.messages.create.return_value.content[0].text = "anthropic answer"
    _gated = LLMClient()
    _consumer = _gated._coders[0]
    check(_gated.generate_plan("s", "u") == "plan from Consumer"
          and _gated.generate_code("s", "u") == "code from Consumer"
          and not _deep_http.called and not _anthropic_sdk.called,
          "disabled paid APIs leave the consumer first and make no transport calls")
    _consumer.fail = True
    os.environ["DEEPSEEK_API_ENABLED"] = " TrUe "
    check(_gated.generate_plan("s", "u") == "deepseek answer"
          and _gated.generate_code("s", "u") == "deepseek answer"
          and _deep_http.call_count == 2 and not _anthropic_sdk.called,
          "enabling DeepSeek after construction supplies both planner and coder fallback")
    os.environ["DEEPSEEK_API_ENABLED"] = "false"
    try:
        _gated.generate_code("s", "u")
        _disabled_exhausted = False
    except RuntimeError:
        _disabled_exhausted = True
    check(_disabled_exhausted and _deep_http.call_count == 2 and not _anthropic_sdk.called,
          "disabled APIs remain skipped after escalation and below-floor fallback")
    os.environ["ANTHROPIC_API_ENABLED"] = "true"
    check(_gated.generate_plan("s", "u") == "anthropic answer"
          and _gated.generate_code("s", "u") == "anthropic answer",
          "explicit Anthropic opt-in is respected by an existing chain")
    os.environ["ANTHROPIC_API_ENABLED"] = "false"
    _anthropic_calls = _anthropic_sdk.call_count
    _blocked_direct = 0
    for _paid in (DeepSeekLLMClient(), AnthropicLLMClient()):
        for _method in (_paid.generate_plan, _paid.generate_code):
            try:
                _method("s", "u")
            except RuntimeError:
                _blocked_direct += 1
    check(_blocked_direct == 4 and _deep_http.call_count == 2
          and _anthropic_sdk.call_count == _anthropic_calls,
          "direct plan/code calls to disabled paid clients stop before HTTP or SDK creation")
    os.environ.update(DEEPSEEK_API_ENABLED="true", ANTHROPIC_API_ENABLED="true",
                      DEEPSEEK_API_KEY="", ANTHROPIC_API_KEY="")
    check(not DeepSeekLLMClient().available and not AnthropicLLMClient().available,
          "enabling a paid API without credentials cannot make it callable")

# ═════ Scenario 23: ChatGPT subscription — Codex backend stream and quota ═════
print("\n── Scenario 23: ChatGPT subscription (Codex backend) ──")
import io  # noqa: E402
from datetime import datetime  # noqa: E402
import requests  # noqa: E402
import scripts.oauth as _oauth  # noqa: E402
from llm_client import ChatGPTConsumerClient  # noqa: E402

# chatgpt.com streams the answer without a Content-Type. Observed live: every
# request died in the stream parser with "startswith first arg must be bytes",
# so the subscription never answered and the chain silently moved on.
_sse_text = "Türkçe — ğüşıöç → " * 40   # multi-byte characters over many 512-byte chunks
_sse_events = [{"type": "response.output_text.delta", "delta": _sse_text[i:i + 50]}
               for i in range(0, len(_sse_text), 50)]
_sse_events.append({"type": "response.completed", "response": {"output": []}})
_sse_resp = requests.Response()
_sse_resp.status_code = 200
_sse_resp.raw = io.BytesIO(b"".join(
    b"data: " + json.dumps(e, ensure_ascii=False).encode("utf-8") + b"\n\n" for e in _sse_events))
check(ChatGPTConsumerClient._read_stream(_sse_resp) == _sse_text,
      "a Codex SSE stream without a Content-Type decodes as UTF-8, intact across chunk boundaries")


class _UsageResponse:
    ok, status_code, text = True, 200, ""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _chatgpt_usage(rate_limit):
    real_get = _oauth.requests.get
    _oauth.requests.get = lambda *a, **k: _UsageResponse({"plan_type": "plus", "rate_limit": rate_limit})
    try:
        return _oauth.PROVIDERS["chatgpt-plus"].get_usage({"access_token": "t", "account_id": "a"})
    finally:
        _oauth.requests.get = real_get


_usage = _chatgpt_usage({
    "primary_window": {"used_percent": 30, "limit_window_seconds": 18000, "reset_at": 1790000000},
    "secondary_window": {"used_percent": 96, "limit_window_seconds": 604800, "reset_at": 1790500000},
})
check([w["label"] for w in _usage["windows"]] == ["ChatGPT 7 Day", "ChatGPT 5 Hour"],
      "ChatGPT windows are labelled by their length, longest first")
check(_usage["remaining"] == 4 and _usage["limit"] == 100
      and datetime.fromisoformat(_usage["reset_time"]).timestamp() == 1790500000,
      "remaining/reset_time come from the most depleted window, not the first one")
_usage = _chatgpt_usage({
    "primary_window": {"used_percent": 10, "limit_window_seconds": 604800, "reset_at": 1790500000},
    "secondary_window": None,
})
check([w["label"] for w in _usage["windows"]] == ["ChatGPT 7 Day"] and _usage["remaining"] == 90,
      "a lone weekly window reported as primary is still labelled weekly")
check(_chatgpt_usage(None)["remaining"] is None,
      "no rate-limit window means unknown quota, never a fabricated figure")

# ═════ Scenario 12: nodes/edges testable in isolation (total=False state) ═════
print("\n── Scenario 12: isolated node/edge tests with partial state ──")
r = nodes.node_test({})   # empty state – every field optional
check(r == {"test_passed": False,
            "test_output": nodes._NO_FILE_BLOCKS_OUTPUT}, "node_test runs on empty state")
check(nodes.node_detect_stack({}) ==
      {"has_vue_files": False, "stack": "unknown",
       "run_phpunit": True, "run_frontend": False, "run_openapi": False},
      "node_detect_stack defers to the files_written guard on empty state")
check(route_after_detect_stack({"run_phpunit": True}) == "phpunit_test",
      "edge: php-bearing stack → phpunit_test")
check(route_after_detect_stack({"run_phpunit": False, "stack": "vue"}) == "vitest_test",
      "edge: vue stack → vitest_test (PHPUnit bypassed)")
check(route_after_detect_stack({}) == "phpunit_test", "edge: default → phpunit_test")
check(route_after_phpunit({"test_passed": True}) == "commit",
      "edge: pass, frontend untouched → commit")
check(route_after_phpunit({"test_passed": True, "run_openapi": True}) == "openapi_test",
      "edge: pass + API touched → openapi_test")
check(route_after_phpunit({"test_passed": True, "run_openapi": True,
                           "run_frontend": True}) == "openapi_test",
      "edge: OpenAPI precedes the frontend layers")
check(route_after_phpunit({"test_passed": True, "run_frontend": True}) == "vitest_test",
      "edge: pass + frontend touched → vitest_test")
check(route_after_phpunit({"test_passed": True, "has_vue_files": True}) == "commit",
      "edge: .vue files in the repo alone never start the frontend layers")
check(route_after_phpunit({"test_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_layer_failure", "edge: fail + retries → on_layer_failure")
check(route_after_phpunit({"test_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: fail + exhausted → failure")
check(route_after_openapi({"openapi_passed": True}) == "commit",
      "edge: openapi pass, frontend untouched → commit")
check(route_after_openapi({"openapi_passed": True, "run_frontend": True}) == "vitest_test",
      "edge: openapi pass + frontend touched → vitest_test")
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

# A file the clone has committed is restored, never deleted: an unrequested
# README edit dropped on a retry must not come back as a deleted README.
import git as _git  # noqa: E402
git_root = tempfile.mkdtemp(prefix="nesti-prune-git-")
try:
    _repo = _git.Repo.init(git_root)
    with open(os.path.join(git_root, "README.md"), "w") as fh:
        fh.write("# Project\n")
    _repo.index.add(["README.md"])
    _repo.index.commit("init", author=_git.Actor("t", "t@example.com"),
                       committer=_git.Actor("t", "t@example.com"))
    _repo.close()
    with open(os.path.join(git_root, "README.md"), "w") as fh:
        fh.write("# Project\n\n## GET /api/ping\n")
    os.makedirs(os.path.join(git_root, "app"))
    open(os.path.join(git_root, "app", "Ping.php"), "w").close()
    reverted = nodes._prune_stale_files(["README.md", "app/Ping.php"], [], git_root)
    check(sorted(reverted) == ["README.md", "app/Ping.php"], "both stale files are reverted")
    check(open(os.path.join(git_root, "README.md")).read() == "# Project\n",
          "a committed README edited by an earlier attempt gets its content back, not deleted")
    check(not os.path.exists(os.path.join(git_root, "app")),
          "a file the attempt created is deleted, with its emptied directory")
finally:
    shutil.rmtree(git_root, ignore_errors=True)

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
finally:
    shutil.rmtree(inv_root, ignore_errors=True)

# ═════ Scenario 12d: GitLab Issues intake (label state model) ═════
print("\n── Scenario 12d: GitLabIssuesClient intake ──")
os.environ["GITLAB_URL"] = "https://gitlab.test"
os.environ["GITLAB_TOKEN"] = "t"
os.environ["GITLAB_PROJECT_PATH"] = "ai/hello-world"
os.environ["GITLAB_ISSUE_LABEL"] = "nesti"
import gitlab_issues_client as gic  # noqa: E402


from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from urllib.parse import urlsplit
import e2e_fixtures as ef
from issue_dependencies import FixtureDependencies


class _FakeResponse:
    def __init__(self, payload, status=200, next_page=""):
        self._payload = deepcopy(payload)
        self.status_code = status
        self.headers = {"X-Next-Page": next_page}
        self.text = json.dumps(payload)

    def json(self):
        return deepcopy(self._payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _IssueHTTP:
    """Stateful, independently read-back GitLab transport with one-item pages."""

    def __init__(self):
        self.issues = {}
        self.notes = {}
        self.mrs = {}
        self.related = {}
        self.requests = []
        self.apply_put = True
        self.lost_child = ""
        self.lost_note = False
        self.failed_get = set()
        self.note_id = 0
        self.child_posts = 0

    def add_issue(self, iid, labels=None, state="opened", description=""):
        self.issues[iid] = {
            "iid": iid, "id": iid + 1000, "project_id": 63, "title": f"Issue {iid}",
            "description": description, "labels": list(labels if labels is not None else ["nesti"]),
            "state": state, "web_url": f"https://gitlab.test/issues/{iid}",
            "author": {"id": 15, "username": "automation"},
        }
        return self.issues[iid]

    def client(self):
        result = gic.GitLabIssuesClient()
        result.session.get = self.get
        result.session.put = self.put
        result.session.post = self.post
        return result

    def _page(self, items, params):
        page = int((params or {}).get("page", 1))
        return _FakeResponse(items[page - 1:page], next_page=str(page + 1)
                             if page < len(items) else "")

    def get(self, url, params=None, timeout=None):
        path = urlsplit(url).path
        self.requests.append(("GET", path, deepcopy(params)))
        if path in self.failed_get:
            return _FakeResponse({"error": "read unavailable"}, 503)
        if path.endswith("/user"):
            return _FakeResponse({"id": 15})
        suffix = path.split("/issues", 1)
        if len(suffix) == 2:
            parts = suffix[1].strip("/").split("/") if suffix[1].strip("/") else []
            if not parts:
                values = sorted(self.issues.values(), key=lambda x: x["iid"])
                if (params or {}).get("state") != "all":
                    values = [i for i in values if i["state"] == (params or {}).get("state", "opened")]
                labels = ((params or {}).get("labels") or "").split(",")
                values = [i for i in values if all(not label or label in i["labels"] for label in labels)]
                return self._page(values, params)
            iid = int(parts[0])
            if len(parts) == 1:
                return _FakeResponse(self.issues[iid])
            if parts[1] == "notes":
                notes = self.notes.get(iid, [])
                if len(parts) == 3:
                    return _FakeResponse(next(n for n in notes if n["id"] == int(parts[2])))
                return self._page(notes, params)
            if parts[1] == "related_merge_requests":
                return self._page([self.mrs[n] for n in self.related.get(iid, [])], params)
        if "/merge_requests/" in path:
            return _FakeResponse(self.mrs[int(path.rsplit("/", 1)[1])])
        raise AssertionError(f"Unexpected GET {url}")

    def put(self, url, json=None, timeout=None):
        path = urlsplit(url).path
        self.requests.append(("PUT", path, deepcopy(json)))
        iid = int(path.rsplit("/", 1)[1])
        candidate = deepcopy(self.issues[iid])
        labels = candidate["labels"]
        for label in (json.get("remove_labels") or "").split(","):
            if label in labels:
                labels.remove(label)
        for label in (json.get("add_labels") or "").split(","):
            if label and label not in labels:
                labels.append(label)
        if "state_event" in json:
            candidate["state"] = "closed" if json["state_event"] == "close" else "opened"
        if self.apply_put:
            self.issues[iid] = candidate
        return _FakeResponse(candidate)

    def add_note(self, iid, body, author=15, system=False):
        self.note_id += 1
        note = {"id": self.note_id, "body": body, "system": system, "author": {"id": author}}
        self.notes.setdefault(iid, []).append(note)
        return note

    def post(self, url, json=None, timeout=None):
        path = urlsplit(url).path
        self.requests.append(("POST", path, deepcopy(json)))
        if path.endswith("/notes"):
            iid = int(path.split("/issues/")[1].split("/")[0])
            note = self.add_note(iid, json["body"])
            if self.lost_note:
                self.lost_note = False
                raise RuntimeError("accepted note response lost")
            return _FakeResponse(note, 201)
        if path.endswith("/issues"):
            self.child_posts += 1
            if self.lost_child != "absent":
                iid = max(self.issues, default=0) + 1
                child = self.add_issue(iid, json.get("labels", "").split(","),
                                       description=json["description"])
                child["title"] = json["title"]
            if self.lost_child:
                self.lost_child = ""
                raise RuntimeError("creation response lost")
            return _FakeResponse(child, 201)
        raise AssertionError(f"Unexpected POST {url}")


http = _IssueHTTP()
http.add_issue(7, ["nesti", "nesti::in-progress", "bug"])
http.add_issue(8, ["nesti", "nesti::pause"])
http.add_issue(9, ["nesti", "human"])
client = http.client()
check([i["id"] for i in client.list_pending(1)] == [9],
      "pagination passes locked and paused pages without starvation")
check(client.get_next_issue()["id"] == 9, "next issue finds eligible later page")
check(client.lock_issue(9) and "human" in http.issues[9]["labels"],
      "verified claim preserves human labels")
check(client.reopen_issue(9) and "human" in http.issues[9]["labels"],
      "failure release preserves human labels")
http.apply_put = False
check(not client.lock_issue(9), "successful PUT with unapplied independent GET fails claim")
http.apply_put = True
check(client.pause_issue(9) and not client.reopen_issue(9),
      "ordinary crash recovery cannot undo a manual pause")
check(client.resume_issue(9), "explicit resume clears control labels")
http.issues[9]["state"] = "closed"
check(not client.pause_issue(9) and not client.resume_issue(9) and not client.reopen_issue(9),
      "human-closed issue is never resurrected")
http.issues[9]["state"] = "opened"
http.issues[9]["labels"] = ["human"]
check(not client.pause_issue(9) and not client.resume_issue(9) and not client.reopen_issue(9),
      "manual opt-out is never reversed")

http.add_issue(10, ["nesti", "nesti::in-progress", "human"])
ordinary_put = http.put
def pause_during_unlock(url, **kwargs):
    response = ordinary_put(url, **kwargs)
    http.issues[10]["labels"].append("nesti::pause")
    return response
client.session.put = pause_during_unlock
check(not client.reopen_issue(10)
      and http.issues[10]["labels"] == ["nesti", "human", "nesti::pause"],
      "a manual pause arriving during unlock is preserved and cannot report pending")
client.session.put = ordinary_put

# Inventory consumes whole entry bodies, not basename-only or partial context.
print("\n── Frontend inventory budgets and isolation ──")
with tempfile.TemporaryDirectory(prefix="nesti-inventory-") as root:
    def put_file(relative, body):
        file = Path(root, relative)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(body, encoding="utf-8")
    put_file("resources/js/app.js", "ENTRY_CHAIN_SENTINEL")
    put_file("resources/views/app.blade.php", "SERVED_VIEW_SENTINEL")
    put_file("resources/js/components/admin/Table.vue", "admin")
    put_file("resources/js/components/public/Table.vue", "public")
    put_file("resources/js/components/vendor/Hidden.vue", "hidden")
    put_file("database/seeders/nested/TaskSeeder.php", "seeder")
    put_file("database/factories/nested/TaskFactory.php", "factory")
    backend = nodes._repo_inventory(root, "backend")
    frontend = nodes._repo_inventory(root, "frontend")
    check("ENTRY_CHAIN_SENTINEL" not in backend and "SERVED_VIEW_SENTINEL" not in backend,
          "backend scope does not quote page entry bodies")
    check(all(value in frontend for value in (
        "ENTRY_CHAIN_SENTINEL", "SERVED_VIEW_SENTINEL", "admin/Table.vue", "public/Table.vue",
        "nested/TaskSeeder.php", "nested/TaskFactory.php")) and "Hidden.vue" not in frontend,
          "frontend context retains relative nested paths and prunes dependencies")
    put_file("resources/js/app.js", "WHOLE_ENTRY_BODY\n \t\n")
    check("WHOLE_ENTRY_BODY\n \t\n" in nodes._repo_inventory(root, "frontend"),
          "quoted entry retains its complete body including trailing whitespace")
    put_file("resources/js/app.js", "OVERSIZE_SENTINEL" + "é" * 6001)
    check("OVERSIZE_SENTINEL" not in nodes._repo_inventory(root, "frontend"),
          "oversized multibyte entry body is omitted whole")
    for relative, sentinel in (
        ("resources/js/app.js", "BUDGET_FIRST"), ("resources/js/app.ts", "BUDGET_SECOND"),
        ("resources/views/app.blade.php", "BUDGET_THIRD"), ("resources/js/App.vue", "BUDGET_FOURTH")):
        put_file(relative, sentinel + "x" * (6000 - len(sentinel)))
    inventory = nodes._repo_inventory(root, "fullstack")
    check("BUDGET_FIRST" in inventory and "BUDGET_SECOND" in inventory
          and "BUDGET_THIRD" not in inventory and "BUDGET_FOURTH" not in inventory,
          "aggregate quote budget keeps priority complete bodies only")
    check(len("\n\n".join(nodes._quoted_entry_files(Path(root)))) <= 16000,
          "inventory headings and bodies together stay within aggregate budget")
    original_read = Path.read_text
    def unreadable(path, *args, **kwargs):
        if path == Path(root, "resources/js/app.js"):
            raise OSError("simulated unreadable optional entry")
        return original_read(path, *args, **kwargs)
    with patch.object(Path, "read_text", unreadable):
        inventory = nodes._repo_inventory(root, "frontend")
    check("BUDGET_FIRST" not in inventory and "BUDGET_SECOND" in inventory
          and "admin/Table.vue" in inventory, "one optional read error preserves other usable context")

print("\n── Playwright report transport and container lifecycle ──")
import frontend_runner as fr
import requests
import docker
requirement = {"endpoint": "/api/tasks", "model": r"App\Models\Task",
               "seeder": r"Database\Seeders\TaskSeeder", "table": "tasks"}
declaration = {key: value for key, value in requirement.items() if key != "table"}
blocked_report = {"version": 1, "status": "missing_seeder", "requirement": requirement}
ready_report = {"version": 1, "status": "ready"}


def runner_case(root, exit_code, report=None, logs="sandbox log", error=None, start_error=None):
    """Run the real runner against a report-writing detached fake container."""
    results = []
    removed = []
    waits = []
    class Container:
        def wait(self, timeout):
            waits.append(timeout)
            if error:
                raise error
            return {"StatusCode": exit_code}
        def logs(self, **kwargs):
            return logs.encode()
        def remove(self, force):
            removed.append(force)
    def start(**kwargs):
        check(kwargs["detach"] is True and kwargs["remove"] is False,
              "runner retains enforceable detached lifecycle")
        directory = next(path for path, mount in kwargs["volumes"].items()
                         if mount["bind"] == "/nesti-results")
        results.append(directory)
        check(not list(Path(directory).iterdir()), "each run starts with an empty report directory")
        if start_error:
            raise start_error
        if report is not None:
            Path(directory, "fixtures.json").write_text(
                report if isinstance(report, str) else json.dumps(report), encoding="utf-8")
        return Container()
    with patch.object(fr.docker, "from_env",
                      return_value=SimpleNamespace(containers=SimpleNamespace(run=start))):
        runner = fr.FrontendRunner()
        result = runner.run_playwright(root)
    check(all(not Path(directory).exists() for directory in results),
          "result mount removed after outcome")
    check(removed == ([] if start_error else [True]), "every started container removed forcibly")
    if not start_error:
        check(waits == [runner.timeout], "container waits with configured timeout")
    return result


with tempfile.TemporaryDirectory(prefix="nesti-runner-") as root:
    Path(root, "artisan").touch()
    Path(root, "e2e").mkdir()
    Path(root, ef.MANIFEST_PATH).write_text(json.dumps({"version": 1, "fixtures": [declaration]}))
    result = runner_case(root, 78, blocked_report)
    check(not result["passed"] and result["fixture_request"] == requirement,
          "exit 78 with matching report carries verified prerequisite")
    wrong = deepcopy(blocked_report)
    wrong["requirement"]["endpoint"] = "/api/other"
    for code, report, logs, error in (
        (1, blocked_report, "setup error", None),
        (1, ready_report, "browser suite failed", None),
        (78, wrong, "wrong declaration", None),
        (78, '{"version":1,"status":"ready"}', "stale ready report", None),
        (78, "{" + "x" * 5000, "oversized forged report", None),
        (78, None, json.dumps(blocked_report), None),
        (1, None, "0 locators; timed out waiting for /api/tasks", None),
        (0, None, "tests passed without fixture helper", None),
        (1, None, "Could not open input file: /opt/nesti/e2e_fixtures.php", None),
        (78, blocked_report, "partial log", requests.exceptions.ReadTimeout("timeout")),
    ):
        result = runner_case(root, code, report, logs, error)
        check(not result["passed"] and result["fixture_request"] is None,
              f"exit/report/log mismatch never invents dependency ({logs[:40]})")
        check(logs in result["output"], "ordinary error preserves container logs")
    check(runner_case(root, 0, ready_report)["passed"], "ready setup reaches ordinary green browser gate")
    result = runner_case(root, 1, start_error=docker.errors.ImageNotFound("missing image"))
    check(not result["passed"] and result["fixture_request"] is None, "missing image remains ordinary failure")
    import builtins
    original_open = builtins.open
    def denied_report(path, mode="r", *args, **kwargs):
        if Path(path).name == "fixtures.json" and mode == "rb":
            raise OSError("report read denied")
        return original_open(path, mode, *args, **kwargs)
    with patch.object(builtins, "open", denied_report):
        result = runner_case(root, 78, blocked_report)
    check(result["fixture_request"] is None and not result["passed"], "report read error cannot request dependency")

print("\n── Graph pause versus ordinary retry and rejected claim ──")
for pause_status, attempts, expected_attempts in (("paused", 1, 1), ("ineligible", 2, 2)):
    reset_calls(310)
    patch_tools(docker_outcomes=[True], code_responses=[BUTTON_CODE],
                laravel_repo=True, vue_repo=True, plan_text="SCOPE: frontend\nimplement button")
    pauses = []
    def pause_fixture(iid, repo, requested, written):
        pauses.append((iid, requested, written))
        return {"success": True, "result": {"status": pause_status, "child_iid": 311,
                                           "reason": "backend prerequisite belongs to parent"}}
    nodes.tool_issue_pause_for_fixture = pause_fixture
    nodes.tool_playwright_run_tests = lambda repo: {
        "success": True, "result": {"passed": False, "output": "fixture preparation stopped",
                                   "fixture_request": requirement}}
    state = initial(310, "Button", "Scope: frontend. Change button colour.")
    state["max_attempts"] = attempts
    final = compiled.invoke(state, config={"recursion_limit": 60})
    check(final["attempt"] == expected_attempts and not calls["mrs"] and not calls["pushes"],
          f"{pause_status} fixture result never commits untested change")
    check(not any(Path(workspace).exists() for workspace in calls["workspaces"]),
          f"{pause_status} fixture path cleans workspace")
    if pause_status == "paused":
        check(final["scope"] == "frontend" and final["dependency_status"] == "paused"
              and len(calls["plan_prompts"]) == len(calls["code_prompts"]) == 1
              and calls["escalate"] == 0 and not any(s == "new" for _, s, _ in calls["issues"]),
              "verified frontend prerequisite pauses at last attempt without LLM escalation or reopen")
    else:
        check(calls["escalate"] == 1 and len(pauses) == 2
              and any(s == "new" for _, s, _ in calls["issues"]),
              "ineligible backend dependency spends shared retry budget then normal failure")
reset_calls(312)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
nodes.tool_issue_set_status = lambda *args, **kwargs: {"success": False, "error": "claim rejected"}
final = compiled.invoke(initial(312), config={"recursion_limit": 60})
check(not calls["workspaces"] and not calls["bootstrap"] and not calls["plan_prompts"]
      and not calls["code_prompts"] and final["failure_reason"],
      "rejected initial claim cannot clone, bootstrap or invoke LLM")

print("\n── Durable dependency intent, ownership and merge boundary ──")
import issue_dependencies as deps
deps.telegram_notify = lambda message: None


def dependency_repo(root):
    """Create committed existing API/model prerequisites without a seeder."""
    repo = _git.Repo.init(root)
    for relative, body in (("app/Models/Task.php", "<?php class Task {}"),
                           ("routes/api.php", "<?php // existing GET /api/tasks")):
        file = Path(root, relative)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(body)
    repo.index.add(["app/Models/Task.php", "routes/api.php"])
    repo.index.commit("existing API", author=_git.Actor("Test", "test@example.invalid"),
                      committer=_git.Actor("Test", "test@example.invalid"))
    return repo


def fresh_dependency():
    transport = _IssueHTTP()
    transport.add_issue(20, ["nesti", "nesti::in-progress", "human"])
    return transport, FixtureDependencies(transport.client(), "main")


def merged_mr(child, **changes):
    result = {"iid": 5, "project_id": 63, "target_project_id": 63, "state": "merged",
              "merged_at": "2026-10-05T10:00:00Z", "target_branch": "main",
              "description": f"Closes #{child}\n\nSeeder implementation",
              "merge_commit_sha": None, "squash_commit_sha": None, "sha": None}
    result.update(changes)
    return result


with tempfile.TemporaryDirectory(prefix="nesti-dependency-") as root:
    repo = dependency_repo(root)
    Path(root, "composer.json").write_text("bootstrap-only Scramble setup")
    http, manager = fresh_dependency()
    result = manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
    child = result["child_iid"]
    state = http.client().get_fixture_state(20)
    check(result["status"] == "paused" and http.child_posts == 1
          and "nesti::pause" in http.issues[20]["labels"] and "human" in http.issues[20]["labels"],
          "frontend change with bootstrap-only Composer mutation durably pauses and creates one child")
    check(http.issues[child]["description"].startswith("Scope: backend")
          and ef.parse_child_marker(http.issues[child]["description"])["key"] == state["items"][0]["key"]
          and http.issues[child]["labels"] == ["nesti"],
          "backend child carries verified ownership and opt-in in original creation")
    fresh = FixtureDependencies(http.client(), "main")
    check(20 in fresh.reconcile()["waiting"] and http.child_posts == 1,
          "reconstructed manager recovers from GitLab without duplicate child")
    check(manager.pause_for_fixture(20, root, requirement, ["./app/Models/Task.php"])["status"]
          == "ineligible" and http.child_posts == 1, "coder-authored backend source cannot become dependency")
    Path(root, "app/Models/Task.php").write_text("unmerged model modification")
    check(manager.pause_for_fixture(20, root, requirement, [])["status"] == "ineligible",
          "changed HEAD-backed model rejects dependency independently of authored paths")
    repo.git.checkout("HEAD", "--", "app/Models/Task.php")
    http.issues[child]["state"] = "closed"
    http.related[child] = [5]
    for changes in ({"state": "opened", "merged_at": None}, {"state": "closed"},
                    {"target_project_id": 999}, {"target_branch": "other"},
                    {"merged_at": None}, {"description": "Unrelated implementation"},
                    {"description": f" Closes #{child}\n"},
                    {"merged_at": "2026-01-01T12:00:00"}, {"iid": 5.0}):
        http.mrs[5] = merged_mr(child, **changes)
        summary = FixtureDependencies(http.client(), "main").reconcile()
        check(not summary["resumed"] and "nesti::pause" in http.issues[20]["labels"],
              f"nonqualifying merge retains hold ({changes})")
    http.mrs[5] = merged_mr(child)
    http.failed_get.add(urlsplit(manager.client._project_api).path + "/merge_requests/5")
    check(FixtureDependencies(http.client(), "main").reconcile()["errors"]
          and "nesti::pause" in http.issues[20]["labels"], "failed MR detail read retains pause")
    http.failed_get.clear()
    check(FixtureDependencies(http.client(), "other").reconcile()["errors"],
          "configured target change cannot release recorded dependency")
    summary = FixtureDependencies(http.client(), "main").reconcile()
    check(summary["resumed"] == [20] and "nesti::pause" not in http.issues[20]["labels"],
          "actual related fast-forward merge without commit SHA releases parent")
    client = http.client()
    check(client.lock_issue(20), "released parent can be claimed normally")
    before = deepcopy(http.issues[20]["labels"])
    check(not FixtureDependencies(http.client(), "main").reconcile()["resumed"]
          and http.issues[20]["labels"] == before, "later reconciliation preserves live claim")
    check(client.pause_issue(20), "manual later pause applies to released record")
    FixtureDependencies(http.client(), "main").reconcile()
    check("nesti::pause" in http.issues[20]["labels"], "released metadata cannot clear later manual pause")
    result = FixtureDependencies(http.client(), "main").pause_for_fixture(
        20, root, requirement, ["resources/js/app.js"])
    check(result["status"] == "paused" and http.child_posts == 1
          and http.client().get_fixture_state(20)["items"][0]["state"] == "blocked",
          "merged but unsatisfied fixture blocks rather than creating another child")

    for outcome in ("accepted", "absent"):
        http, manager = fresh_dependency()
        http.lost_child = outcome
        manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
        summary = FixtureDependencies(http.client(), "main").reconcile()
        item = http.client().get_fixture_state(20)["items"][0]
        check(http.child_posts == 1 and 20 in summary["waiting"]
              and (item["child_iid"] is not None if outcome == "accepted"
                   else item["creation_submitted"] and item["child_iid"] is None),
              f"lost child POST {outcome} response recovers or holds without second creation")

    for trusted in (False, True):
        http, manager = fresh_dependency()
        http.lost_child = "accepted"
        manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
        child = max(http.issues)
        if trusted:
            key = http.client().get_fixture_state(20)["items"][0]["key"]
            http.issues[child]["description"] = f"<!-- NESTI_FIXTURE_CHILD_V1 {key} broken -->"
        else:
            http.issues[child]["author"]["id"] = 99
        FixtureDependencies(http.client(), "main").reconcile()
        item = http.client().get_fixture_state(20)["items"][0]
        check(http.child_posts == 1 and item["child_iid"] is None
              and item["state"] == ("blocked" if trusted else "creating"),
              "corrupt trusted ownership blocks; foreign ownership cannot attach a child")

    # Closed reused children are observed immediately, including squashed
    # merges. Paginated candidate selection uses the newest merge, not page 1.
    http, manager = fresh_dependency()
    http.lost_child = "accepted"
    manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
    child = max(http.issues)
    http.issues[child]["state"] = "closed"
    http.related[child] = [4, 5, 6]
    http.mrs[4] = merged_mr(child, iid=4, merged_at="2026-10-04T10:00:00Z")
    http.mrs[5] = merged_mr(child, iid=5, squash_commit_sha="a" * 40)
    http.mrs[6] = merged_mr(child, iid=6, squash_commit_sha="b" * 40)
    FixtureDependencies(http.client(), "main").reconcile()
    item = http.client().get_fixture_state(20)["items"][0]
    check(item["state"] == "merged" and item["mr_iid"] == 6 and item["merge_sha"] == "b" * 40
          and "nesti::pause" not in http.issues[20]["labels"] and http.child_posts == 1,
          "closed reused child with paginated squash merges releases using newest IID tie-break")

    http, manager = fresh_dependency()
    manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
    child = max(http.issues)
    http.issues[child]["labels"] = ["human-only"]
    FixtureDependencies(http.client(), "main").reconcile()
    check(http.issues[child]["labels"] == ["human-only"], "child opt-out is not undone")
    state = http.client().get_fixture_state(20)
    creating = deepcopy(state)
    creating["items"][0].update(state="creating", child_iid=None, creation_submitted=True)
    client = http.client()
    client.get_fixture_state(20)
    client.save_fixture_state(20, creating)
    duplicate = http.add_issue(child + 1, [], state="closed",
                               description=http.issues[child]["description"])
    FixtureDependencies(http.client(), "main").reconcile()
    check(http.client().get_fixture_state(20)["items"][0]["state"] == "blocked"
          and http.child_posts == 1, "multiple trusted child owners fail closed without selecting one")

    # Interrupt after each durable transition, including label writes. A fresh
    # client must rediscover state, not replay a local in-memory transaction.
    class Crash(BaseException):
        pass
    for boundary in ("intent", "pause", "submitted", "linked", "merged", "resume", "released"):
        http, manager = fresh_dependency()
        save = manager.client.save_fixture_state
        pause = manager.client.pause_issue
        resume = manager.client.resume_issue
        def crash_save(iid, state):
            save(iid, state)
            item = state["items"][0]
            hit = ((boundary == "intent" and item["state"] == "creating" and not item["creation_submitted"])
                   or (boundary == "submitted" and item["state"] == "creating" and item["creation_submitted"])
                   or (boundary == "linked" and item["state"] == "waiting")
                   or (boundary == "merged" and item["state"] == "merged" and state["release_pending"])
                   or (boundary == "released" and item["state"] == "merged" and not state["release_pending"]))
            if hit:
                raise Crash()
        def crash_pause(*args, **kwargs):
            result = pause(*args, **kwargs)
            if boundary == "pause":
                raise Crash()
            return result
        def crash_resume(*args, **kwargs):
            result = resume(*args, **kwargs)
            if boundary == "resume":
                raise Crash()
            return result
        manager.client.save_fixture_state = crash_save
        manager.client.pause_issue = crash_pause
        manager.client.resume_issue = crash_resume
        try:
            manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
            child = max(http.issues)
            http.related[child] = [5]
            http.mrs[5] = merged_mr(child)
            manager.reconcile()
        except Crash:
            pass
        recovered = FixtureDependencies(http.client(), "main")
        recovered.reconcile()
        item = http.client().get_fixture_state(20)["items"][0]
        if boundary == "submitted":
            check(http.child_posts == 0 and item["child_iid"] is None
                  and "nesti::pause" in http.issues[20]["labels"],
                  "crash after submitted intent conservatively holds unknown outcome")
        elif boundary in ("intent", "pause", "linked"):
            check(http.child_posts == 1 and item["state"] == "waiting"
                  and "nesti::pause" in http.issues[20]["labels"],
                  f"crash after {boundary} recovers one waiting child")
        else:
            check(http.child_posts == 1 and item["state"] == "merged"
                  and not http.client().get_fixture_state(20)["release_pending"]
                  and "nesti::pause" not in http.issues[20]["labels"],
                  f"crash after {boundary} completes release exactly once")

    http, manager = fresh_dependency()
    manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
    state = http.client().get_fixture_state(20)
    http.issues[20]["labels"] = ["nesti", "human"]
    check(20 not in [i["id"] for i in http.client().list_pending()],
          "durable waiting intent excludes parent even when pause label was lost")
    http.add_note(20, "NESTI_FIXTURE_DEPENDENCIES_V1\nforeign malformed", author=99)
    check(http.client().get_fixture_state(20) == state, "foreign latest marker cannot override trusted state")
    http.add_note(20, "NESTI_FIXTURE_DEPENDENCIES_V1\nsystem malformed", system=True)
    check(http.client().get_fixture_state(20) == state, "system marker cannot override trusted state")
    http.add_note(20, "NESTI_FIXTURE_DEPENDENCIES_V1\ntrusted malformed")
    http.add_issue(50)
    check(50 in [i["id"] for i in http.client().list_pending()] and
          20 not in [i["id"] for i in http.client().list_pending()],
          "malformed newest trusted metadata fails only affected issue closed")

    http, manager = fresh_dependency()
    manager.pause_for_fixture(20, root, requirement, ["resources/js/app.js"])
    stale_client = http.client()
    stale = stale_client.get_fixture_state(20)
    external = deepcopy(stale)
    external["items"][0]["reason"] = "operator updated hold"
    http.add_note(20, ef.format_dependency_note(external))
    stale["items"][0]["reason"] = "stale worker update"
    try:
        stale_client.save_fixture_state(20, stale)
        refused = False
    except RuntimeError:
        refused = True
    check(refused and http.client().get_fixture_state(20) == external,
          "external trusted note change rejects stale worker write")
    client = http.client()
    current = client.get_fixture_state(20)
    current["items"][0]["reason"] = "verified lost-note update"
    http.lost_note = True
    client.save_fixture_state(20, current)
    note_count = len(http.notes[20])
    client.save_fixture_state(20, current)
    check(http.client().get_fixture_state(20) == current and len(http.notes[20]) == note_count,
          "accepted lost note response is rediscovered and identical saves do not append")
    client = http.client()
    current = client.get_fixture_state(20)
    current["items"][0]["reason"] = "readback unavailable"
    next_note = http.note_id + 1
    http.failed_get.add(urlsplit(client._project_api).path + f"/issues/20/notes/{next_note}")
    try:
        client.save_fixture_state(20, current)
        rejected = False
    except RuntimeError:
        rejected = True
    check(rejected, "accepted dependency note with unavailable independent readback cannot confirm transition")
    http.failed_get.clear()
    for state_value, labels in (("closed", ["nesti", "nesti::pause"]), ("opened", ["human"])):
        http.issues[20].update(state=state_value, labels=labels)
        snapshot = deepcopy(http.issues[20])
        FixtureDependencies(http.client(), "main").reconcile()
        check(http.issues[20] == snapshot, "reconciliation leaves closed or opted-out parent untouched")

print("\n── Configured target checkout versus server HEAD ──")
from gitlab_client import GitLabClient
with tempfile.TemporaryDirectory(prefix="nesti-target-") as root:
    origin = _git.Repo.init(Path(root, "origin"))
    source = Path(origin.working_tree_dir, "fixture.txt")
    source.write_text("server default without fixture")
    origin.index.add(["fixture.txt"])
    actor = _git.Actor("Test", "test@example.invalid")
    origin.index.commit("server default", author=actor, committer=actor)
    server_default = origin.active_branch.name
    target = origin.create_head("fixture-target")
    target.checkout()
    source.write_text("merged fixture prerequisite")
    origin.index.add(["fixture.txt"])
    origin.index.commit("fixture merged", author=actor, committer=actor)
    origin.heads[server_default].checkout()
    client = GitLabClient()
    client.use_ssh = True
    client.repo_url = origin.working_tree_dir
    client.default_branch = "fixture-target"
    clone = client.clone(str(Path(root, "clone")))
    check(clone.active_branch.name == "fixture-target"
          and Path(clone.working_tree_dir, "fixture.txt").read_text() == "merged fixture prerequisite",
          "real local clone uses configured merge target rather than server default")

# ═════ Scenario 12e: failure output must carry signal, not installer chatter ═════
print("\n── Scenario 12e: layer_output.condense ──")
from layer_output import condense as _condense  # noqa: E402

_NOISY = (
    "added 199 packages, and audited 200 packages in 1m\n"
    "56 packages are looking for funding\n"
    "  run `npm fund` for details\n"
    "2 high severity vulnerabilities\n"
    "To address all issues, run:\n"
    "  npm audit fix --force\n"
    "Run `npm audit` for details.\n"
    "npm notice New major version of npm available! 10.9.8 -> 12.0.2\n"
    "[PrimeUI] PrimeUI license is not configured.\n"
    "Installing dependencies from lock file (including require-dev)\n"
    "Nothing to install, update or remove\n"
    "Generating optimized autoload files\n"
    "  - Locking phpunit/phpunit (11.5.56)\n"
    "  - Downloading sebastian/diff (6.0.2)\n"
    "  dedoc/scramble ........................................ DONE\n"
    " \x1b[31m\u00d7\x1b[39m HelloWorldDialog > dialog has the expected header text\n"
    "   \x1b[31mAssertionError\x1b[39m: expected '' to contain 'Hello World'\n"
    "    at resources/js/components/__tests__/HelloWorldDialog.test.js:24:31\n"
    " Tests  1 failed | 1 passed (2)\n"
)
_out = _condense(_NOISY, 1000)
check("AssertionError: expected '' to contain 'Hello World'" in _out,
      "the assertion failure survives condensing")
check("HelloWorldDialog.test.js:24:31" in _out,
      "the file:line of the failure survives (the old head-slice cut it off)")
check("Tests  1 failed | 1 passed (2)" in _out,
      "the run summary survives — it is the LAST line, so only a tail keeps it")
for noise in ("npm notice", "npm audit", "looking for funding", "PrimeUI",
              "Nothing to install", "- Locking ", "- Downloading ",
              "dedoc/scramble", "severity vulnerabilit"):
    check(noise not in _out, f"installer noise dropped: {noise!r}")
check("\x1b[" not in _out and "[31m" not in _out,
      "ANSI colour escapes stripped (they leaked into issue comments verbatim)")

# Conservatism: a line is noise only when it MATCHES the pattern, not when it
# merely mentions one of those words. Dropping a real error would be far worse.
_lookalike = "Failed asserting that 2 high severity vulnerabilities were reported\n"
check(_lookalike.strip() in _condense(_lookalike, 500),
      "a real message that merely mentions a noise phrase is kept")

# Tail selection and bounds.
_long = "".join(f"line {n}\n" for n in range(1, 2001))
_tailed = _condense(_long, 200)
check("line 2000" in _tailed and "\nline 1\n" not in _tailed,
      "condense keeps the end of a long output, not the beginning")
check(len(_tailed) <= 200 + 40, "condensed output respects its budget")
check("trimmed" in _tailed, "a trimmed output says so")
check(_tailed.split("\n")[1].startswith("line "),
      "the tail starts on a line boundary, never mid-line")

# Degenerate inputs must never lose information or raise.
_all_noise = "npm notice\nnpm notice again\nadded 3 packages\n"
check(_condense(_all_noise, 500).strip() != "",
      "output that is entirely noise still yields something rather than nothing")
check(_condense("", 500) == "", "empty input stays empty")
check(_condense("boom", 0) == "", "a non-positive budget yields nothing")
check(_condense("boom", 500) == "boom", "short output passes through untouched")


# ═════ Scenario 13: TaskEngine thin wrapper ═════
print("\n── Scenario 13: TaskEngine.run_once() ──")
import task_engine  # noqa: E402
reset_calls(111)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
task_engine.tool_issue_list_pending = lambda: {
    "success": True,
    "result": [{"id": 111, "subject": "Wrapper test", "description": "d"}]}
task_engine.tool_issue_set_status = nodes.tool_issue_set_status
task_engine.tool_issue_reconcile_dependencies = lambda: {
    "success": True, "result": {"resumed": [], "waiting": [], "errors": []}}
engine = task_engine.TaskEngine()
check(engine.run_once() is True, "run_once returns True when MR opened")
check(calls["docker"] == 1, "graph executed via wrapper")
task_engine.tool_issue_list_pending = lambda: {"success": True, "result": []}
check(engine.run_once() is False, "run_once returns False when no pending issues")

# ═════ Static acceptance checks ═════
print("\n── Static acceptance checks ──")
import graph.tools as tools_mod

# Regression check for the TokenStore Redis-outage bug: tool_quota_check()
# must degrade like every other store in this codebase (ConversationStore,
# GitLabIssuesClient) — never crash the whole orchestrator loop just because
# Redis is unreachable when node_on_layer_failure calls it on every retry.
quota_result = tools_mod.tool_quota_check()
check(quota_result == {"success": True, "result": {}},
      "tool_quota_check degrades to an empty result on a Redis outage, "
      "never raises/exits")



if os.path.isfile(_registry_path):
    registry = json.load(open(_registry_path))
    topics = {t["topic"] for t in registry["laravel"]["topics"]}
    check({"migrations", "eloquent", "validation", "controllers", "routing",
           "http-tests", "queries", "pagination", "errors"} <= topics,
          "the backend topics the live issues need are vendored")
    practices = {d["slug"] for d in registry["practices"]["documents"]}
    check({"tdd", "senior-security", "frontend-design", "minimalist-ui"} == practices,
          f"the curated practice corpus is exactly the whitelist (got {sorted(practices)})")
    # Practice docs are edited by hand, so guard what the tooling cannot: a doc
    # without triggers is never selected, a "## " line inside a code fence
    # splits a Qdrant chunk mid-code, and a cited licence file must ship.
    _practice_faults = []
    for _doc in registry["practices"]["documents"]:
        _text = (skill_catalog.CATALOG_DIR / _doc["path"]).read_text(encoding="utf-8")
        if not _doc["triggers"]:
            _practice_faults.append(f"{_doc['slug']}: no triggers")
        _fenced = False
        for _line in _text.splitlines():
            if _line.lstrip().startswith(("```", "~~~")):
                _fenced = not _fenced
            elif _fenced and _line.startswith("## "):
                _practice_faults.append(f"{_doc['slug']}: '## ' inside a code fence")
        for _licence in re.findall(r"^license: .*\((practices/licenses/[^)]+)\)", _text, re.M):
            if not (skill_catalog.CATALOG_DIR / _licence).is_file():
                _practice_faults.append(f"{_doc['slug']}: missing {_licence}")
    check(not _practice_faults,
          f"every practice doc is selectable, chunk-safe and ships its licence ({_practice_faults})")
    check({"multiselect", "galleria", "image", "colorpicker", "imagecompare", "scrollpanel",
           "password", "inputmask", "panelmenu", "editor"}.isdisjoint(
              c["slug"] for c in registry["primevue"]["components"]),
          "no component PrimeVue 5 deprecated is vendored — the coder never learns a doomed API")
    slugs = {c["slug"] for c in registry["primevue"]["components"]}
    check({"datatable", "select", "organizationchart", "dialog", "inputtext",
           "datepicker", "button", "message", "chart"} <= slugs,
          "every component the live issues need is vendored")
else:
    print("  ⚠ SKIPPED registry static checks (corpus not generated)")


print(f"\nALL {passed_checks} CHECKS PASSED ✅")
