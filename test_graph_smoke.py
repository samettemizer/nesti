"""
test_graph_smoke.py – verifies the LangGraph pipeline against the acceptance
checklists of core loop, layered frontend testing and
Laravel bootstrap + Scramble OpenAPI gate, with all external
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
from unittest.mock import patch

# ── Environment before any project import ────────────────────────────────────
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ["ANTHROPIC_API_ENABLED"] = "true"
os.environ["DEEPSEEK_API_ENABLED"] = "true"
os.environ["OPENROUTER_API_ENABLED"] = "false"
os.environ["LOCAL_LLM_ENABLED"] = "false"
os.environ["HERMES3_LLM_ENABLED"] = "false"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"   # unreachable → memory fallback
os.environ["MAX_CODE_RETRIES"] = "2"                 # → max_attempts = 3
os.environ["NESTI_STACK"] = "auto"                   # exercise real detection
os.environ["NESTI_RERANKER_ENABLED"] = "false"
os.environ["GITLAB_URL"] = "https://gitlab.test"       # scopes Redis keys (forge.identity)
os.environ["GITLAB_PROJECT_PATH"] = "ai/hello-world"
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TELEGRAM_CHAT_ID", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("OPENROUTER_API_KEY", None)

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
import project_layout                            # noqa: E402

API_ONLY = {"backend": ".", "frontend": None}
ROOT_SPA = {"backend": ".", "frontend": ".frontend"}

PHP_CODE = (
    "Implementation below.\n\n"
    "### FILE: src/Hello.php\n```php\n<?php\necho 'hello';\n```\n\n"
    "### FILE: tests/HelloTest.php\n```php\n<?php\n// phpunit test\n```\n"
)
VUE_CODE = (
    "Implementation below.\n\n"
    "### FILE: .frontend/package.json\n```json\n{\"name\": \"app\"}\n```\n\n"
    "### FILE: .frontend/src/components/FileTable.vue\n```vue\n<template><div/></template>\n```\n\n"
    "### FILE: .frontend/src/components/__tests__/FileTable.test.js\n```js\n// vitest\n```\n\n"
    "### FILE: .frontend/e2e/file-table.spec.js\n```js\n// playwright\n```\n"
)
FULLSTACK_CODE = PHP_CODE + "\n" + VUE_CODE

# fixtures: a real Laravel change (backend + API surface) and the same
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
    "### FILE: .frontend/src/components/TaskTable.vue\n"
    "```vue\n<template><div/></template>\n```\n\n"
    "### FILE: .frontend/src/components/__tests__/TaskTable.test.js\n```js\n// vitest\n```\n\n"
    "### FILE: .frontend/e2e/tasks.spec.js\n```js\n// playwright\n```\n"
)
GOOD_CODE = PHP_CODE
NO_BLOCKS = "Here is a prose description of the change instead of files."

calls: dict = {}


def reset_calls(issue_id: int) -> None:
    calls.clear()
    calls.update({
        "issue_id": issue_id, "issues": [], "docker": 0, "escalate": 0,
        "openapi": 0, "vitest": 0, "playwright": 0,
        "bootstrap": [], "starter": [], "layers": [], "layer_paths": [],
        "pushes": [], "mrs": [], "history_at_commit": None, "workspaces": [],
        "plan_prompts": [], "plan_systems": [], "code_prompts": [], "code_systems": [],
        "plan_messages": [], "code_messages": [],
        "memory_search": [], "memory_similar": [], "memory_remember_solution": [],
        "memory_remember_failure": [], "memory_forget": [], "memory_recall": [],
    })


def initial(issue_id: int, subject: str = "", description: str = "Implement the thing.") -> dict:
    subject = subject or f"Test issue {issue_id}"
    return {
        "issue": {"id": issue_id, "subject": subject, "description": description},
        "issue_id": issue_id, "subject": subject,
        "skills": [], "plan": "", "scope": "fullstack", "code_response": "", "repo_path": "", "base_sha": "",
        "layout": dict(API_ONLY),
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
        "retrieved_chunks": 0, "past_solutions": 0, "recalled_failures": 0,
        "run_id": f"test-{issue_id}",
        "mr_url": "", "failure_reason": "", "error": "",
    }


def patch_tools(docker_outcomes, code_responses, plan_exc=None, code_exc_first=False,
                openapi_outcomes=(True,),
                vitest_outcomes=(True,), playwright_outcomes=(True,),
                laravel_repo: bool = False, bootstrap_created: bool = False,
                vue_repo: bool = False, plan_text: str = "",
                doc_chunks=(), similar_solutions=(), recalled=(),
                memory_error: str = "", expanded_doc_chunks=None, layout=API_ONLY):
    """
    Install fakes on graph.nodes (node functions resolve names at call time).

    ``laravel_repo`` makes the fake clone look like a Laravel application so the
    REAL tool_detect_stack reports is_laravel/has_api_routes.  It defaults to
    False on purpose: dropping a composer.json into every fake clone would turn
    the Vue-only scenario into "fullstack" and silently void that regression.

    The memory fixtures default to empty, so every scenario that does
    not ask for memory runs against a degraded (empty) memory layer — the
    regression net for graceful degradation.  ``memory_error`` makes every
    memory tool report a genuine failure instead.

    ``vue_repo`` puts an existing component into the clone, so a scenario can
    prove that a backend change in a repository WITH .vue files still skips
    the frontend layers.  ``plan_text`` replaces the fake planner's answer
    (e.g. to declare a scope on line 1).

    ``layout`` pins the clone layout (default: API-only root app, the layout the
    root-relative fake code assumes); ``None`` resolves it for real.
    """
    if layout is None:
        nodes.clone_layout = project_layout.clone_layout
    else:
        nodes.clone_layout = lambda clone: dict(layout)

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
            spa = os.path.join(target_path, ".frontend")
            os.makedirs(os.path.join(spa, "src", "components"))
            with open(os.path.join(spa, "package.json"), "w") as handle:
                json.dump({"dependencies": {"vue": "^3.5.0"}}, handle)
            open(os.path.join(spa, "src", "components", "Existing.vue"), "w").close()
        return {"success": True, "result": {"repo_path": target_path, "head_sha": "b" * 40}}
    nodes.tool_gitlab_clone = fake_clone

    def fake_bootstrap(repo_path, spa_path=""):
        calls["bootstrap"].append((repo_path, spa_path) if spa_path else repo_path)
        return {"success": True, "result": {
            "created": bootstrap_created,
            "mode": "scaffold" if bootstrap_created else "top-up",
            "reason": "scaffolded" if bootstrap_created
                      else "already a Laravel application",
            "output": "",
        }}
    nodes.tool_laravel_bootstrap = fake_bootstrap

    def fake_starter(repo_path, backend_dir, spa_dir):
        calls["starter"].append((repo_path, backend_dir, spa_dir))
        spa = os.path.join(repo_path, spa_dir)
        os.makedirs(os.path.join(spa, "src"), exist_ok=True)
        with open(os.path.join(spa, "package.json"), "w") as handle:
            json.dump({"dependencies": {"vue": "^3.5.0"}}, handle)
        with open(os.path.join(spa, "src", "App.vue"), "w") as handle:
            handle.write("<template><RouterView/></template>\n")
        return {"success": True, "result": {
            "variant": "spatie", "files": [f"{spa_dir}/package.json", f"{spa_dir}/src/App.vue"],
            "reason": "starter kit (spatie roles)"}}
    nodes.tool_starter_kit = fake_starter

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
            calls["layer_paths"].append((key, workspace_path))
            passed = outcomes[min(calls[key] - 1, len(outcomes) - 1)]
            return {"success": True, "result": {"passed": passed, "output": pass_out if passed else fail_out}}
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

    def fake_openapi(workspace_path, baseline_routes=None):
        calls["openapi"] += 1
        calls["layers"].append("openapi")
        calls["layer_paths"].append(("openapi", workspace_path))
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

    # memory fakes – record every call, return the fixtures.
    def _memory(key, record, result):
        calls[key].append(record)
        if memory_error:
            return {"success": False, "error": memory_error}
        return {"success": True, "result": result}

    nodes.tool_memory_search_docs = lambda text, stack="", limit=6: _memory(
        "memory_search", {"text": text, "stack": stack, "limit": limit},
        list(expanded_doc_chunks if limit == 20 and expanded_doc_chunks is not None else doc_chunks))
    nodes.tool_memory_find_similar = lambda text, limit=2: _memory(
        "memory_similar", text, list(similar_solutions))
    nodes.tool_memory_recall_failures = lambda issue_id, run_id, text, attempt, limit=2: _memory(
        "memory_recall",
        {"issue_id": issue_id, "run_id": run_id, "text": text, "attempt": attempt},
        list(recalled))
    nodes.tool_memory_remember_failure = lambda issue_id, run_id, attempt, layer, output: _memory(
        "memory_remember_failure",
        {"issue_id": issue_id, "run_id": run_id, "attempt": attempt, "layer": layer,
         "output": output},
        {"stored": True})
    nodes.tool_memory_remember_solution = (
        lambda issue_id, subject, description, plan, stack, mr_url: _memory(
            "memory_remember_solution",
            {"issue_id": issue_id, "subject": subject, "plan": plan,
             "stack": stack, "mr_url": mr_url},
            {"stored": True}))
    nodes.tool_memory_forget_episodes = lambda issue_id, run_id: _memory(
        "memory_forget", (issue_id, run_id), {"deleted": 0})

    # LLM fakes (instance attributes shadow bound methods)
    if plan_exc:
        def fail_plan(sp, up, messages=None):
            calls["plan_messages"].append(messages)
            raise RuntimeError(plan_exc)
        nodes._llm.generate_plan = fail_plan
    else:
        def fake_plan(sp, up, messages=None):
            calls["plan_messages"].append(messages)
            calls["plan_prompts"].append(up)
            calls["plan_systems"].append(sp)
            return plan_text or "1. Objective: implement Hello\n2. Files: src/Hello.php"
        nodes._llm.generate_plan = fake_plan

    seq = list(code_responses)

    def fake_code(system_prompt, user_prompt, messages=None):
        calls["code_messages"].append(messages)
        calls["code_prompts"].append(user_prompt)
        calls["code_systems"].append(system_prompt)
        if code_exc_first:
            raise RuntimeError("All coding providers exhausted.")
        return seq.pop(0) if len(seq) > 1 else seq[0]
    nodes._llm.generate_code = fake_code

    def domain_tool_reached(*_args, **_kwargs):
        raise AssertionError("domain tools reached on a default-structure repository")
    nodes.tool_issue_domain_answer = domain_tool_reached
    nodes.tool_issue_ask_domain = domain_tool_reached
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
check(reopen[0][1].endswith(
    "\n\n" + nodes.failed_run_marker("Test issue 102", "Implement the thing.", "b" * 40)),
    "exhausted coding failure note carries the title/description/cloned-HEAD marker")
check(nodes._store.load(102) == [], "history deleted after exhausted failure")
check(all(messages == [{"role": "user", "content": prompt}]
          for messages, prompt in zip(calls["code_messages"], calls["code_prompts"])),
      "two coding retries send only the compiled current request, not the transcript")
check(all(prompt.count("## Existing Repository State") == 1
          and prompt.count("## Latest failure") == 1
          and "PHPUnit FAILURES!" in prompt for prompt in calls["code_prompts"][1:]),
      "each retry carries one current repository snapshot and the latest failure")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran on failure path")

# ═════ Scenario 3: planning fails → failure without any coding ═════
print("\n── Scenario 3: planning failure ──")
nodes._store.save(103, [{"role": "user", "content": "stale unanswered plan"}] * 4)
f = run(103, docker_outcomes=[True], code_responses=[GOOD_CODE],
        plan_exc="All planning providers exhausted.")
check(f["plan"] == "" and "Planning failed" in f["failure_reason"], "routed plan → failure")
check(f["attempt"] == 0 and calls["docker"] == 0, "no code/test attempts made")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check(len(reopen) == 1 and "planning providers failed" in reopen[0][1],
      "reopened with planning note")
check("NESTI_FAILED_RUN_V1" not in reopen[0][1], "planning failure leaves no failed-run marker")
check("All planning providers exhausted." in f["error"], "error field populated")
check(not os.path.exists(calls["workspaces"][0]), "cleanup ran after plan failure")
check(nodes._store.load(103) == [], "failed planning clears history before reopening")
check(len(calls["plan_messages"][0]) == 1
      and "stale unanswered plan" not in calls["plan_messages"][0][0]["content"],
      "four unanswered requests collapse to one current planning request")
f = run(103, docker_outcomes=[True], code_responses=[GOOD_CODE],
        plan_exc="All planning providers exhausted.")
check(nodes._store.load(103) == [] and len(calls["plan_messages"][0]) == 1,
      "a fresh run after planning failure cannot accumulate unanswered prompts")

# ═════ Scenario 4: coder providers exhausted → immediate failure ═════
print("\n── Scenario 4: coder providers exhausted ──")
f = run(104, docker_outcomes=[True], code_responses=[GOOD_CODE], code_exc_first=True)
check(f["mr_url"] == "" and f["attempt"] == 3, "attempt jumped to max → failure route")
check(calls["docker"] == 0, "no sandbox run for exhausted providers")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check("All coding providers exhausted." in reopen[0][1],
      "reopen note carries provider-exhaustion reason")
check("NESTI_FAILED_RUN_V1" not in reopen[0][1],
      "exhausted coder providers (transient quota) leave no failed-run marker")
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

# ═════ Scenario 6: Vue-only issue skips PHPUnit ═════
print("\n── Scenario 6: Vue-only issue → PHPUnit skipped ──")
f = run(106, docker_outcomes=[False], code_responses=[VUE_CODE], layout=ROOT_SPA)
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
f = run(107, docker_outcomes=[True], code_responses=[FULLSTACK_CODE], layout=ROOT_SPA)
check(f["stack"] == "fullstack", "stack detected as fullstack")
check(f["run_phpunit"] is True and f["has_vue_files"] is True, "both layers enabled")
check(calls["docker"] == 1 and calls["vitest"] == 1 and calls["playwright"] == 1,
      "all three layers ran exactly once")
check(f["mr_url"] == "https://gitlab.example/mr/107", "MR opened after all layers")
check(all(k in calls["mrs"][0] for k in ("PHPUnit", "Vitest", "Playwright")),
      "MR description reports all three layers")

# ═════ Scenario 8: Vitest failure escalates and retries ═════
print("\n── Scenario 8: Vitest failure → escalate → exhausted ──")
f = run(108, docker_outcomes=[True], code_responses=[VUE_CODE], vitest_outcomes=[False],
        layout=ROOT_SPA)
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
f = run(109, docker_outcomes=[True], code_responses=[VUE_CODE], playwright_outcomes=[False],
        layout=ROOT_SPA)
check(f["mr_url"] == "" and f["attempt"] == 3, "3 attempts then failure")
check(calls["vitest"] == 3 and calls["playwright"] == 3, "both layers ran each attempt")
check(calls["escalate"] == 2, "coder escalated between attempts (2x)")
check("Playwright" in f["failure_reason"], "failure_reason names Playwright")
reopen = [(s, n) for _, s, n in calls["issues"] if s == "new"]
check("e2e/file-table.spec.js" in reopen[0][1], "reopen note carries the Playwright output")

# ═════ Scenario 10: PHPUnit failure in a fullstack repo gates the frontend ═════
print("\n── Scenario 10: fullstack, PHPUnit fails → frontend layers gated ──")
f = run(110, docker_outcomes=[False], code_responses=[FULLSTACK_CODE], layout=ROOT_SPA)
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
    r = tool_detect_stack(probe, ["src/components/Widget.vue"], ".", "src")["result"]
    check(r["stack"] == "vue" and r["run_phpunit"] is False, "vue only → run_phpunit False")
    check(r["vue_files"] == [os.path.join("src", "components", "Widget.vue")],
          "vue_files lists repo-relative paths")

    open(os.path.join(probe, "composer.json"), "w").close()
    r = tool_detect_stack(probe, None, ".", "src")["result"]
    check(r["stack"] == "fullstack" and r["run_phpunit"] is True,
          "composer.json alone flips vue → fullstack")

    # MCP callers may pass host projects with installed node_modules, and
    # Vue component libraries ship .vue files — those must never be detected.
    os.makedirs(os.path.join(probe, "src", "node_modules", "primevue"))
    open(os.path.join(probe, "src", "node_modules", "primevue", "Vendor.vue"), "w").close()
    r = tool_detect_stack(probe, None, ".", "src")["result"]
    check(len(r["vue_files"]) == 1, "node_modules pruned from the scan")

    vendored = tempfile.mkdtemp(prefix="nesti-detect-vendor-")
    os.makedirs(os.path.join(vendored, "vendor", "acme"))
    os.makedirs(os.path.join(vendored, "src"))
    open(os.path.join(vendored, "vendor", "acme", "Lib.php"), "w").close()
    open(os.path.join(vendored, "src", "App.vue"), "w").close()
    r = tool_detect_stack(vendored, None, ".", "src")["result"]
    check(r["stack"] == "vue" and r["has_php"] is False,
          "vendor/ pruned — Composer leftovers do not force the PHP layer on")
    shutil.rmtree(vendored, ignore_errors=True)

    empty = tempfile.mkdtemp(prefix="nesti-detect-empty-")
    r = tool_detect_stack(empty)["result"]
    check(r["stack"] == "unknown" and r["run_phpunit"] is True,
          "unknown stack still runs a test layer (never commits untested)")
    shutil.rmtree(empty, ignore_errors=True)

    os.environ["NESTI_STACK"] = "php"
    r = tool_detect_stack(probe, None, ".", "src")["result"]
    check(r["stack"] == "php" and r["source"] == "override" and r["has_vue"] is False,
          "NESTI_STACK pins the stack and reports source=override")
    os.environ["NESTI_STACK"] = "bogus"
    check(tool_detect_stack(probe, None, ".", "src")["success"] is False, "invalid NESTI_STACK rejected")
    os.environ["NESTI_STACK"] = "auto"
    check(tool_detect_stack(probe, None, ".", ".")["success"] is False,
          "a frontend inside the Laravel app is refused by the stack detector")
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

    for touched, expected in (("app/Domains/Shop/Http/Controllers/OrderController.php", True),
                              ("routes/domains/Shop.php", True),
                              ("app/Domains/Shop/Models/Order.php", False)):
        r = tool_detect_stack(laravel_probe, [touched])["result"]
        check(r["run_openapi"] is expected, f"{touched} touched → OpenAPI layer runs: {expected}")

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
f = run(115, docker_outcomes=[True], code_responses=[LARAVEL_VUE_CODE], laravel_repo=True,
        layout=ROOT_SPA)
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
nodes.tool_laravel_bootstrap = lambda repo_path, spa_path="": {
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
_plan_sys = {s: _scoped.build_plan_prompt(_button, scope=s, layout=ROOT_SPA)[0] for s in SCOPES}
_plan_user = {s: _scoped.build_plan_prompt(_button, scope=s, layout=ROOT_SPA)[1] for s in SCOPES}
_code_sys = {s: _scoped.build_code_prompt(_button, "plan", scope=s, layout=ROOT_SPA)[0] for s in SCOPES}
check(all(f"TASK SCOPE: {s}" in _plan_sys[s] and f"TASK SCOPE: {s}" in _code_sys[s]
          for s in SCOPES), "both system prompts carry the TASK SCOPE block of their scope")
check(not any(section in _code_sys["frontend"] or section in _plan_sys["frontend"]
              for section in ("DATABASE POLICY", "LARAVEL BACKEND", "API DOCUMENTATION")),
      "a frontend issue gets no database policy and no Laravel/Scramble standards")
check(not any(section in _code_sys["backend"]
              for section in ("PRIMEVUE SPA", "@playwright/test", "getByRole")),
      "a backend issue gets no PrimeVue standards and no Playwright instructions")
check(all(section in _code_sys["fullstack"]
          for section in ("DATABASE POLICY", "LARAVEL BACKEND", "PRIMEVUE SPA")),
      "fullstack keeps both standards")
check(all(f"Line 1 of the plan, alone: SCOPE: {s}" in _plan_user[s] for s in SCOPES),
      "the planner is asked to declare the scope on line 1")
check(all("Documentation is out of scope" in p and "README.md" in p
          for p in list(_plan_sys.values()) + list(_code_sys.values())),
      "every prompt keeps README.md out of an issue that does not ask for it")
_docs_sys = _scoped.build_code_prompt(
    {"id": 6, "subject": "Add /api/ping and describe it in the README", "description": ""},
    "plan", scope="backend", layout=API_ONLY)[0]
check("Documentation is out of scope" not in _docs_sys
      and 'asks for documentation ("readme")' in _docs_sys,
      "an issue that names the README gets it back in scope, limited to what it asks")

# ═════ Scenario 25: the layers follow the change, not the repository ═════
print("\n── Scenario 25: change-aware layer gates ──")
_gate_repo = tempfile.mkdtemp(prefix="nesti-gates-")
try:
    os.makedirs(os.path.join(_gate_repo, ".frontend", "src", "components"))
    open(os.path.join(_gate_repo, "artisan"), "w").close()
    open(os.path.join(_gate_repo, "composer.json"), "w").close()
    _existing_vue = os.path.join(_gate_repo, ".frontend", "src", "components", "TaskTable.vue")
    open(_existing_vue, "w").close()

    def _gates(written):
        r = tool_detect_stack(_gate_repo, written, ".", ".frontend")["result"]
        return r["run_phpunit"], r["run_frontend"]

    check(_gates(["app/Http/Controllers/PingController.php", "routes/api.php",
                  "tests/Feature/PingTest.php"]) == (True, False),
          "a backend change in a repository WITH .vue files skips Vitest and Playwright")
    check(_gates([".frontend/src/components/TaskTable.vue",
                  ".frontend/src/components/__tests__/TaskTable.test.js",
                  ".frontend/e2e/tasks.spec.js"]) == (False, True),
          "a frontend-only change skips PHPUnit")
    check(_gates(["app/Models/Task.php", ".frontend/src/components/TaskTable.vue"]) == (True, True),
          "a change on both sides runs every layer")
    check(_gates(["README.md"]) == (True, False),
          "a change on neither side still runs PHPUnit — never commits untested")
    check(_gates(None) == (True, True), "written_files=None → every layer (MCP callers)")
    os.remove(_existing_vue)
    check(_gates([".frontend/src/main.js"]) == (True, False),
          "a JavaScript change in an SPA without Vue falls back to PHPUnit")
finally:
    shutil.rmtree(_gate_repo, ignore_errors=True)

# ═════ Scenario 26: scope end-to-end — SCOPE line, prompts, layers, widening ═════
print("\n── Scenario 26: scope through the graph ──")
BUTTON_CODE = (
    "### FILE: .frontend/src/components/SaveButton.vue\n"
    "```vue\n<template><Button severity=\"warn\" label=\"Save\"/></template>\n```\n\n"
    "### FILE: .frontend/src/components/__tests__/SaveButton.test.js\n```js\n// vitest\n```\n\n"
    "### FILE: .frontend/e2e/save-button.spec.js\n```js\n// playwright\n```\n"
)


class _ScopeLines(logging.Handler):
    """Collects the graph.nodes lines starting with *prefix* whatever LOG_LEVEL the run uses."""

    def __init__(self, prefix="SCOPE:"):
        super().__init__(logging.INFO)
        self.prefix = prefix
        self.lines = []

    def emit(self, record):
        if record.getMessage().startswith(self.prefix):
            self.lines.append(record.getMessage())


def run_logged(issue_id, prefix="SCOPE:", **kw):
    """run() with the *prefix* lines (default SCOPE) of that run captured."""
    handler, node_logger = _ScopeLines(prefix), logging.getLogger("graph.nodes")
    previous_level = node_logger.level
    node_logger.addHandler(handler)
    node_logger.setLevel(logging.DEBUG if previous_level == logging.DEBUG else logging.INFO)
    try:
        return run(issue_id, **kw), handler.lines
    finally:
        node_logger.removeHandler(handler)
        node_logger.setLevel(previous_level)


_FACTS = "PHP 8.4 · Laravel 13.0 · database sqlite\nTables (column type):\n- tasks: id integer"
with patch.object(nodes, "tool_app_facts", lambda path: {"success": True, "result": {
        "facts": _FACTS, "tables": 1, "reason": "1 table(s)"}}):
    f, facts_lines = run_logged(
        2610, prefix="APP FACTS:", subject="Add a /api/ping endpoint for uptime checks",
        description="Return ok.", docker_outcomes=[False, True], code_responses=[LARAVEL_CODE],
        laravel_repo=True)
    check(facts_lines == ["APP FACTS: exported · GitLab issue #2610 · 1 table(s)"]
          and "## Application Facts" in calls["plan_prompts"][0] and len(calls["code_prompts"]) == 2
          and all("## Application Facts" in p and "- tasks: id integer" in p for p in calls["code_prompts"]),
          f"a backend run logs one APP FACTS line and every prompt carries the facts ({facts_lines})")
    f, facts_lines = run_logged(
        2611, prefix="APP FACTS:", subject="Change the green button colour to orange", description="",
        docker_outcomes=[True], code_responses=[BUTTON_CODE], laravel_repo=True, vue_repo=True,
        layout=ROOT_SPA)
    check(facts_lines == ["APP FACTS: skipped · GitLab issue #2611 · frontend scope"]
          and not any("## Application Facts" in p for p in calls["plan_prompts"] + calls["code_prompts"]),
          f"a frontend run skips the facts and its prompts carry none ({facts_lines})")
from graph.tools import _render_app_facts  # noqa: E402
_rendered, _count = _render_app_facts(
    {"php_version": "8.4", "laravel_version": "13.0", "database_engine": "pgsql"},
    {"tables": {"migrations": {"id": "integer"},
                **{f"t{i:03}": {"id": "integer", "body": "x" * 200} for i in range(100)}}})
check("migrations" not in _rendered and len(_rendered) <= 12000 and 0 < _count < 100
      and _rendered.endswith(f"- … {100 - _count} more table(s) omitted"),
      "facts drop framework tables and stop at the character cap with an omission line")


f, scope_lines = run_logged(
    2601, subject="Add a /api/ping endpoint for uptime checks", description="Return ok.",
    docker_outcomes=[True], code_responses=[LARAVEL_CODE], laravel_repo=True, vue_repo=True,
    layout=ROOT_SPA)
check(len(scope_lines) == 1 and scope_lines[0].startswith("SCOPE: backend · GitLab issue #2601 · "),
      f"exactly one SCOPE line per run, final scope and issue number first ({scope_lines})")
check(calls["layers"] == ["docker", "openapi"],
      f"backend issue in a Vue repository: PHPUnit → OpenAPI only (got {calls['layers']})")
check(f["scope"] == "backend" and not any("PRIMEVUE SPA" in p for p in
                                          calls["plan_systems"] + calls["code_systems"]),
      "a backend issue's plan and code prompts carry no PrimeVue standards")
check("scope: backend" in calls["mrs"][0], "the MR body reports the scope")

f, scope_lines = run_logged(
    2602, subject="Change the green button colour to orange", description="",
    docker_outcomes=[True], code_responses=[BUTTON_CODE], laravel_repo=True, vue_repo=True,
    layout=ROOT_SPA)
check(f["scope"] == "frontend" and calls["layers"] == ["vitest", "playwright"],
      f"button colour change: frontend scope, Vitest → Playwright, no PHPUnit (got {calls['layers']})")
check(not any("DATABASE POLICY" in p for p in calls["plan_systems"] + calls["code_systems"]),
      "a frontend issue's prompts carry no database policy")
check(f["mr_url"] == "https://gitlab.example/mr/2602", "frontend-only change reaches its MR")

f, scope_lines = run_logged(
    2603, subject="Change the green button colour to orange", description="",
    plan_text="**SCOPE:** fullstack\n1. Objective: orange button",
    docker_outcomes=[True], code_responses=[BUTTON_CODE], laravel_repo=True, vue_repo=True,
    layout=ROOT_SPA)
check(f["scope"] == "fullstack" and "LARAVEL BACKEND" in calls["code_systems"][0],
      "the coder follows the scope the planner declared")
check(len(scope_lines) == 1 and scope_lines[0].startswith("SCOPE: fullstack · GitLab issue #2603")
      and "issue text: frontend" in scope_lines[0] and scope_lines[0].endswith("planner: fullstack"),
      f"the SCOPE line shows the final scope and both sources ({scope_lines})")

# The layer set changes between attempts (Vitest on attempt 1, PHPUnit on
# attempt 2): attempt 2's red PHPUnit must be fed back as PHPUnit — not as the
# stale Vitest output of attempt 1 — and attempt 1's Vitest output must not
# reach the MR body of code it never ran on.
f = run(2605, subject="Change the green button colour to orange", description="",
        docker_outcomes=[False, True], vitest_outcomes=[False],
        code_responses=[BUTTON_CODE, LARAVEL_CODE, LARAVEL_CODE],
        laravel_repo=True, vue_repo=True, layout=ROOT_SPA)
check([(e["attempt"], e["layer"]) for e in calls["memory_remember_failure"]]
      == [(1, "Vitest (component tests)"), (2, "PHPUnit")],
      "each attempt's failure is reported as its own layer, never a stale earlier one")
check(f["scope"] == "fullstack", "the PHPUnit failure widened the frontend scope")
check(f["mr_url"] and "### Vitest" not in calls["mrs"][0],
      "the MR body lists only the layers that ran on the merged code")
check("FAIL  src/components" in calls["code_messages"][1][0]["content"]
      and "PHPUnit FAILURES!" in calls["code_messages"][2][0]["content"]
      and "FAIL  src/components" not in calls["code_messages"][2][0]["content"],
      "a retry replaces the previous failure evidence instead of sending both layers")


# Unapplied frontend responses must not masquerade as PHPUnit failures or
# reach the untouched clone's green baseline.
f = run(2620, subject="Filter existing tasks", description="Scope: frontend",
        docker_outcomes=[True], code_responses=[NO_BLOCKS, BUTTON_CODE],
        laravel_repo=True, vue_repo=True, layout=ROOT_SPA)
check(calls["layers"] == ["vitest", "playwright"] and f["attempt"] == 2 and f["mr_url"],
      "an unapplied frontend attempt retries before running only its actual layers")
check(calls["memory_remember_failure"][0]["layer"] == "Code generation"
      and f["scope"] == "frontend",
      "unapplied code is attributed to generation without widening frontend scope")
f = run(2621, subject="Filter existing tasks", description="Scope: frontend",
        docker_outcomes=[True], code_responses=[NO_BLOCKS],
        laravel_repo=True, vue_repo=True, layout=ROOT_SPA)
check(not calls["layers"] and not calls["pushes"] and not f["mr_url"],
      "exhausted unapplied code cannot test the baseline, push or open an empty MR")
check("Code generation" in f["failure_reason"]
      and not os.path.exists(calls["workspaces"][0]),
      "generation exhaustion reports its cause and always cleans the workspace")
# ═════ Scenario 19: hierarchical memory end-to-end ═════
print("\n── Scenario 19: hierarchical memory end-to-end ──")
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
check(calls["memory_forget"] == [(1190, "test-1190")],
      "the run's episodes are dropped once the issue is done")
check({e["run_id"] for e in calls["memory_remember_failure"] + calls["memory_recall"]}
      == {"test-1190"},
      "every episode write and recall carries the run's id")
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

# Opt-in retrieval preserves the exact legacy baseline and both final prompts.
import prompt_builder as _pb  # noqa: E402
_dense = [
    {**_CHUNKS[0], "doc_title": "Dense PHP first", "text": "baseline php first", "score": 0.9},
    {**_CHUNKS[1], "doc_title": "Dense practice", "text": "baseline practice",
     "stack": "practice", "score": 0.8},
    {**_CHUNKS[0], "doc_title": "Dense PHP last", "text": "baseline php last", "score": 0.7},
]
_expanded = [
    {**_dense[2], "doc_title": "Reranked PHP first", "text": "reranked php first", "extra": "kept"},
    {**_dense[1], "doc_title": "Reranked practice", "text": "reranked practice"},
    {**_dense[0], "doc_title": "Reranked PHP last", "text": "reranked php last"},
]
_ranked = [
    {**c, "rerank_score": score, "rerank_model": "test-model@pinned"}
    for c, score in zip(_expanded, [3.0, 1.0, 2.0])
]
_rerank_kw = dict(docker_outcomes=[True], code_responses=[GOOD_CODE],
                  doc_chunks=_dense, expanded_doc_chunks=_expanded)
with patch.dict("sys.modules", {"reranker": None}):
    for _disabled in ("false", "0", "no", "off", "", "enabled"):
        with patch.dict(os.environ, {"NESTI_RERANKER_ENABLED": _disabled}):
            reset_calls(1192)
            patch_tools(**_rerank_kw)
            _actual = nodes._retrieve_chunks("same query", [], stack="php")
            check(_actual == _dense and all(a is b for a, b in zip(_actual, _dense))
                  and calls["memory_search"] == [
                      {"text": "same query", "stack": "php", "limit": 8}],
                  f"disabled flag {_disabled!r} returns identical dictionaries without importing reranker")
    run(1192, **_rerank_kw)
_baseline_prompts = (list(calls["plan_prompts"]), list(calls["code_prompts"]))
with patch.dict(os.environ, {"NESTI_RERANKER_ENABLED": "true"}):
    with patch("reranker.rerank_candidates", return_value=_ranked) as _adapter:
        f = run(1192, **_rerank_kw)
        check(_adapter.call_count == 2 and all(
            c.args[1:] == (_expanded, ["php", "practice", "php"])
            for c in _adapter.call_args_list),
            "both graph phases rerank expanded candidates against unchanged baseline lanes")
        check([c["limit"] for c in calls["memory_search"]] == [8, 20, 8, 20]
              and all(calls["memory_search"][i]["text"] == calls["memory_search"][i + 1]["text"]
                      and calls["memory_search"][i]["stack"] == calls["memory_search"][i + 1]["stack"]
                      for i in (0, 2)),
              "expansion keeps each phase query and stack filter")
        check(all(p.index("### Reranked PHP first") < p.index("### Reranked practice")
                  < p.index("### Reranked PHP last")
                  for p in calls["plan_prompts"] + calls["code_prompts"])
              and f["retrieved_chunks"] == 3,
              "final plan and code prompts retain lane replay order rather than dense or global rerank sort")
    for _failure in (None, RuntimeError("synthetic adapter failure")):
        with patch("reranker.rerank_candidates",
                   **({"side_effect": _failure} if isinstance(_failure, Exception)
                      else {"return_value": None})):
            run(1192, **_rerank_kw)
            check((calls["plan_prompts"], calls["code_prompts"]) == _baseline_prompts,
                  "failed reranking produces byte-identical baseline plan and code prompts")
    for _response in (
        {"success": False, "error": "synthetic expansion failure"},
        {"success": True, "result": []},
        {"success": True, "result": None},
        {"success": True, "result": ["malformed"]},
        {"success": True, "result": [{"text": None}]},
        RuntimeError("synthetic search failure"),
    ):
        with patch.object(nodes, "tool_memory_search_docs", side_effect=[
            {"success": True, "result": _dense}, _response,
        ]), patch("reranker.rerank_candidates") as _adapter:
            _actual = nodes._retrieve_chunks("same query", [], stack="php", limit=7)
            check(_actual == _dense and all(a is b for a, b in zip(_actual, _dense))
                  and not _adapter.called,
                  "invalid expansion returns the whole untouched baseline without scoring")
    with patch.object(nodes, "tool_memory_search_docs", return_value={
        "success": True, "result": [],
    }) as _search, patch("reranker.rerank_candidates") as _adapter:
        check(nodes._retrieve_chunks("empty", []) == []
              and _search.call_count == 1 and not _adapter.called,
              "empty baseline never widens retrieval or starts scoring")
    _catalog = [Skill(title="Catalog", url=_dense[0]["doc_url"],
                      content=_dense[0]["text"])]
    with patch.object(nodes, "tool_memory_search_docs", side_effect=[
        {"success": True, "result": _dense},
        {"success": True, "result": [_dense[0], *_expanded]},
    ]), patch("reranker.rerank_candidates", return_value=None) as _adapter:
        check(nodes._retrieve_chunks("same query", _catalog) == _dense[1:]
              and _adapter.call_args.args[1:] == (_expanded, ["practice", "php"]),
              "both searches exclude catalog bodies but retain distinct passages sharing its URL")
    import reranker as _reranker  # noqa: E402
    _profile = {"model_id": "cross-encoder/ettin-reranker-150m-v1", "revision": "a" * 40}
    with patch.object(_reranker._runtime, "profile", _profile), patch.object(
        _reranker._runtime, "score", return_value=([2.0, 9.0, 2.0], "")
    ):
        reset_calls(1193)
        patch_tools(**_rerank_kw)
        _actual = nodes._retrieve_chunks("same query", [], stack="php")
        check([{k: v for k, v in c.items() if k not in {"rerank_score", "rerank_model"}}
               for c in _actual] == _expanded
              and [c["rerank_score"] for c in _actual] == [2.0, 9.0, 2.0]
              and all(c["rerank_model"] == _profile["model_id"] + "@" + _profile["revision"]
                      for c in _actual)
              and all("rerank_score" not in c for c in _expanded + _dense),
              "real adapter keeps stable ties within lanes, dense scores and all metadata without mutation")
    with patch.object(_reranker._runtime, "score") as _score:
        with patch.object(nodes, "tool_memory_search_docs", side_effect=[
            {"success": True, "result": _dense},
            {"success": True, "result": [_expanded[0], _expanded[2]]},
        ]):
            _actual = nodes._retrieve_chunks("same query", [])
            check(_actual == _dense and all(a is b for a, b in zip(_actual, _dense))
                  and not _score.called,
                  "missing practice lane returns complete baseline before scoring")
    for _enabled in ("1", "YES", " on "):
        with patch.dict(os.environ, {"NESTI_RERANKER_ENABLED": _enabled}), patch.object(
            nodes, "tool_memory_search_docs", side_effect=[
                {"success": True, "result": _dense * 3},
                {"success": True, "result": _expanded * 3},
            ]
        ) as _search, patch("reranker.rerank_candidates", return_value=None) as _adapter:
            check(nodes._retrieve_chunks("custom limit", [], stack="vue", limit=7) == _dense * 2
                  and _search.call_args_list[0].kwargs == {"stack": "vue", "limit": 7}
                  and _search.call_args_list[1].kwargs == {"stack": "vue", "limit": 20}
                  and _adapter.call_args.args[2] == ["php", "practice", "php"] * 2,
                  "recognized enable values preserve the custom first limit and six baseline slots")

_dense_rendered = _pb._format_retrieved_section(_expanded, 6000)
for _bad_marker in (
    {}, {"rerank_score": float("nan")}, {"rerank_score": float("inf")},
    {"rerank_score": True}, {"rerank_score": "3"}, {"rerank_score": None},
    {"rerank_score": 10**1000},
    {"rerank_model": ""}, {"rerank_model": " "}, {"rerank_model": None},
    {"rerank_model": "other@revision"}, {"rerank_model": 7},
):
    _mixed = [dict(c) for c in _ranked]
    if _bad_marker:
        _mixed[1].update(_bad_marker)
    else:
        _mixed[1].pop("rerank_score")
    check(_pb._format_retrieved_section(_mixed, 6000) == _dense_rendered,
          "incomplete or incoherent rerank markers preserve the exact legacy formatter")
    check(_pb._format_retrieved_section(_mixed, 6000, _mixed[1]["text"])
          == _pb._format_retrieved_section(_expanded, 6000, _mixed[1]["text"]),
          "marker coherence is checked before excluding the malformed row")
_oversized = {**_ranked[0], "text": "oversized-" * 800}
for _budget in (5000, 6000):
    _packed = _pb._format_retrieved_section(
        [_oversized, _ranked[1], _ranked[2]], _budget, _ranked[1]["text"]
    )
    check("oversized-" not in _packed and "### Reranked practice" not in _packed
          and "### Reranked PHP last" in _packed
          and _packed.count("\nSource: ") == 1,
          "reranked blocks retain catalog exclusion and whole-block skip at both prompt budgets")
_budget_catalog = [Skill(title="Catalog", url=_ranked[1]["doc_url"],
                         content=_ranked[1]["text"])]
for _builder, _args in (
    (_pb.build_plan_prompt, (initial(1194)["issue"],)),
    (_pb.build_code_prompt, (initial(1194)["issue"], "Implement the thing")),
):
    _, _prompt = _builder(
        *_args, retrieved_chunks=[_oversized, _ranked[1], _ranked[2]],
        catalog_skills=_budget_catalog, layout=API_ONLY,
    )
    check("oversized-" not in _prompt and "### Reranked practice" not in _prompt
          and "### Reranked PHP last" in _prompt,
          "actual plan/code builders exclude catalog bodies and skip oversized reranked blocks")

# ═════ Scenario 20: memory unavailable ═════
print("\n── Scenario 20: memory unavailable → pipeline unchanged ──")
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

# ═════ Scenario 21: pure-function checks (no Redis, no Qdrant) ═════
print("\n── Scenario 21: formatters, chunker and degradation ──")
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
with patch.dict(os.environ, {"NESTI_FORGE": "github"}):
    _sol_gh = _pb._format_solutions_section([{"issue_id": 5, "subject": "s", "mr_url": "u", "plan": "p"}], 4000)
check("(similarity 0.9, MR u)" in _sol and "(similarity 0, PR u)" in _sol_gh,
      "a past solution names its MR on GitLab and its PR on GitHub")

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
check(_sm.available is False and _sm.find_similar_solutions("gitlab.test/a/b", "x") == []
      and _sm.remember_solution("gitlab.test/a/b", 1, "s", "d", "p", "php", "u") is False
      and _sm.recall_failures("gitlab.test/a/b", 1, "r", "x", attempt=5) == []
      and _sm.forget_episodes("gitlab.test/a/b", 1, "r") == 0,
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
    caches_user_prefix = False

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
    _anthropic_sdk.return_value.messages.create.return_value.model_dump.return_value = {
        "content": [{"type": "text", "text": "anthropic answer"}]}
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

# ═════ OpenRouter: live model selection, billing gates and failure cascade ═════
print("\n── OpenRouter: model selection + paid fallback ──")
import io  # noqa: E402
from contextlib import redirect_stdout  # noqa: E402
import scripts.oauth as _oauth  # noqa: E402
from llm_client import OpenRouterLLMClient  # noqa: E402


class _ModelRedis:
    def __init__(self):
        self.values = {}

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value
        return True

    def delete(self, key):
        return self.values.pop(key, None) is not None


_model_redis = _ModelRedis()
_text_model = {
    "id": "vendor/model-a", "name": "Model A", "context_length": 100000,
    "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
    "pricing": {"prompt": "0.0000001575", "completion": "0.000008"},
}
_catalog = [
    _text_model,
    {**_text_model, "id": "vendor/model-b", "name": "Model B"},
    {**_text_model, "id": "vendor/image", "architecture": {
        "input_modalities": ["text"], "output_modalities": ["image"],
    }},
]


def _model_command(*args):
    output = io.StringIO()
    with patch.object(_oauth.sys, "argv", ["nesti", "/provider", *args]), redirect_stdout(output):
        try:
            _oauth.main()
        except SystemExit as exc:
            return exc.code, output.getvalue()
    return 0, output.getvalue()


with patch.dict(os.environ, {
    "OPENROUTER_API_ENABLED": "false", "OPENROUTER_API_KEY": "openrouter-test-key",
    "OPENROUTER_MODEL": "vendor/env-model", "DEEPSEEK_API_KEY": "deepseek-test-key",
    "DEEPSEEK_API_ENABLED": "true", "ANTHROPIC_API_ENABLED": "false",
}), patch("scripts.oauth.redis.from_url", return_value=_model_redis), \
        patch("scripts.oauth.requests.get") as _catalog_http, \
        patch("llm_client.requests.post") as _model_http, \
        patch("llm_client.build_consumer_clients", return_value=[_StubCoder("Consumer")]):
    _catalog_http.return_value.json.return_value = {"data": _catalog}
    _store_for_models = _oauth.TokenStore()
    _store_for_models.save_token("claude", {"access_token": "subscription"})
    _exit, _output = _model_command("models", "openrouter", "MODEL A")
    check(_exit == 0 and "vendor/model-a" in _output and "vendor/model-b" not in _output
          and "0.1575" in _output and "8" in _output,
          "model search matches names case-insensitively and converts per-token USD to per-million")
    _exit, _output = _model_command("model", "openrouter", "vendor/model-a")
    check(_exit == 0 and _oauth.TokenStore().get_model("openrouter") == "vendor/model-a"
          and os.environ["OPENROUTER_API_ENABLED"] == "false",
          "CLI selection persists across store instances without enabling billing")
    for _invalid_model in ("vendor/absent", "vendor/image"):
        _exit, _output = _model_command("model", "openrouter", _invalid_model)
        check(_exit == 1 and _store_for_models.get_model("openrouter") == "vendor/model-a",
              f"{_invalid_model} is rejected without overwriting the selected text model")
    with patch("llm_client._token_store", return_value=_store_for_models):
        _openrouter = OpenRouterLLMClient()
        for _method in (_openrouter.generate_plan, _openrouter.generate_code):
            try:
                _method("s", "u")
                _blocked = False
            except RuntimeError:
                _blocked = True
            check(_blocked and not _model_http.called,
                  "disabled OpenRouter rejects direct inference before contacting HTTP")
        os.environ["OPENROUTER_API_ENABLED"] = " TrUe "
        _openrouter_chain = LLMClient()
        _openrouter_chain.generate_code("s", "u")
        check(_openrouter_chain.last_coder_label == "Consumer"
              and not _model_http.called,
              "usable subscriptions still outrank an enabled OpenRouter API")
        _openrouter_chain._coders[0].fail = True
        _model_http.return_value.json.return_value = {
            "choices": [{"message": {"content": "complete answer"}, "finish_reason": "stop"}],
        }
        _openrouter_chain.generate_plan("s", "u")
        check(_model_http.call_args.kwargs["json"]["model"] == "vendor/model-a",
              "planning uses the persisted choice instead of OPENROUTER_MODEL")
        _model_command("model", "openrouter", "vendor/model-b")
        _openrouter_chain.generate_code("s", "u")
        check(_model_http.call_args.kwargs["json"]["model"] == "vendor/model-b"
              and _openrouter_chain.last_coder_attribution() == {
                  "provider": "OpenRouter", "model": "vendor/model-b", "billing": "platform API",
              },
              "an already-running cascade uses the next CLI model selection and attributes it")
        _model_command("model", "openrouter", "vendor/model-a")
        check(_openrouter_chain.last_coder_attribution()["model"] == "vendor/model-b",
              "changing selection cannot relabel code produced by the preceding model")
        _exit, _output = _model_command("model", "openrouter", "--reset")
        check(_exit == 0 and _oauth.configured_model(_store_for_models, "openrouter") == "vendor/env-model"
              and _store_for_models.get_token("claude") == {"access_token": "subscription"},
              "reset restores the environment model without deleting subscription credentials")

        _model_http.reset_mock()
        os.environ["OPENROUTER_MODEL"] = ""
        try:
            _openrouter.generate_code("s", "u")
            _missing_blocked = False
        except RuntimeError:
            _missing_blocked = True
        check(_missing_blocked and not _model_http.called,
              "no selected model never silently bills an arbitrary default")
        os.environ["OPENROUTER_MODEL"] = "vendor/env-model"
        for _bad_payload in (
            {"error": {"code": 429, "message": "quota exhausted"}},
            {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]},
            {"choices": [{"message": {"content": "partial file"}, "finish_reason": "length"}]},
        ):
            _model_http.return_value.json.return_value = _bad_payload
            try:
                _openrouter.generate_code("s", "u")
                _bad_rejected = False
            except RuntimeError:
                _bad_rejected = True
            check(_bad_rejected, "error, empty and truncated responses cannot count as generated code")

        _transport_urls = []

        def _openrouter_failure(url, **kwargs):
            _transport_urls.append(url)
            if url.startswith(_oauth.OPENROUTER_API_BASE):
                raise _oauth.requests.Timeout("OpenRouter timed out")
            response = _oauth.requests.Response()
            response.status_code = 200
            response._content = b'{"choices":[{"message":{"content":"fallback code"}}]}'
            return response

        _model_http.side_effect = _openrouter_failure
        _openrouter_chain.reset_coder_tier()
        _openrouter_chain.generate_code("s", "u")
        check(_openrouter_chain.last_coder_attribution()["provider"] == "DeepSeek"
              and _transport_urls == [
                  f"{_oauth.OPENROUTER_API_BASE}/chat/completions",
                  "https://api.deepseek.com/v1/chat/completions",
              ],
              "OpenRouter timeout falls through to the next paid tier in the same attempt")
        _model_http.reset_mock()
        _store_for_models._available = False
        try:
            _openrouter.generate_code("s", "u")
            _outage_blocked = False
        except RuntimeError:
            _outage_blocked = True
        check(_outage_blocked and not _model_http.called,
              "unreadable selection never silently changes the billed model to the environment default")
    with patch("scripts.oauth.TokenStore", side_effect=AssertionError("catalog must not need Redis")):
        _exit, _output = _model_command("models", "openrouter", "model")
    check(_exit == 0 and "vendor/image" not in _output,
          "the public text model catalog works without Redis or an enabled API")

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


# Current source replaces old answers without changing FILE/DELETE application.
with tempfile.TemporaryDirectory(prefix="nesti-retry-context-") as root:
    from pathlib import Path
    removed = Path(root, "obsolete.js")
    removed.write_text("remove me\n", encoding="utf-8")
    bodies = ["first revision\n \t\n", "second revision\n \t\n", "final revision\n \t\n"]
    responses = [
        f"### FILE: custom/current.txt\n```text\n{body}```\n### DELETE: obsolete.js\n"
        for body in bodies
    ]
    reset_calls(3100)
    patch_tools(docker_outcomes=[True], code_responses=responses)
    state = initial(3100)
    state.update(repo_path=root, plan="Change the feature, with its tests.")
    for index, response in enumerate(responses):
        if index:
            state["test_output"] = f"failure-{index}"
        state.update(nodes.node_code(state))
        check(state["code_response"] == response
              and state["written_files"] == ["custom/current.txt", "obsolete.js"]
              and Path(root, "custom/current.txt").read_text() == bodies[index]
              and not removed.exists(),
              f"attempt {index + 1} preserves raw response, path set, complete bytes and DELETE")
    for index in (1, 2):
        request = calls["code_messages"][index][0]["content"]
        check(bodies[index - 1] in request and f"failure-{index}" in request
              and request.count("## Existing Repository State") == 1,
              f"retry {index} receives latest applied source and failure")
    check(bodies[0] not in calls["code_messages"][2][0]["content"]
          and "failure-1" not in calls["code_messages"][2][0]["content"],
          "second retry excludes obsolete code and failure despite full diagnostic transcript")
    nodes._store.delete(3100)

# A retry quotes the existing file its failure names, so it is fixed in place.
with tempfile.TemporaryDirectory(prefix="nesti-retry-failure-file-") as root:
    _put_retry = Path(root, "tests/Feature/ContractTest.php")
    _put_retry.parent.mkdir(parents=True)
    _put_retry.write_text("<?php\n// CONTRACT_TEST_BODY\n", encoding="utf-8")
    _retry_code = "### FILE: app/X.php\n```php\n<?php\n```\n"
    reset_calls(3101)
    patch_tools(docker_outcomes=[True], code_responses=[_retry_code])
    state = initial(3101)
    state.update(repo_path=root, plan="Add the endpoint.", scope="backend")
    state.update(nodes.node_code(state))
    state["test_output"] = ("FAILED  Tests\\Feature\\ContractTest\n"
                            "  at \x1b[32mtests/Feature/ContractTest.php\x1b[39m:26")
    state.update(nodes.node_code(state))
    check("CONTRACT_TEST_BODY" not in calls["code_prompts"][0]
          and "Current tests/Feature/ContractTest.php (complete)" in calls["code_prompts"][1]
          and "CONTRACT_TEST_BODY" in calls["code_prompts"][1],
          "a retry quotes the existing test file its failure names (tests/Feature/X.php:26)")
    check(any("never remove\n  or loosen its other assertions" in p
              for p in (calls["code_systems"][1], calls["code_prompts"][1])),
          "the coding prompt forbids loosening an existing test's other assertions")
    nodes._store.delete(3101)

# ═════ Scenario 12c: the coder must see what the repository already has ═════
print("\n── Scenario 12c: _repo_inventory ──")
inv_root = tempfile.mkdtemp(prefix="nesti-inv-")
try:
    check(nodes._repo_inventory(os.path.join(inv_root, "missing"), API_ONLY) == "",
          "a missing workspace yields no section (never raises)")

    os.makedirs(os.path.join(inv_root, "database", "migrations"))
    os.makedirs(os.path.join(inv_root, "app", "Models"))
    os.makedirs(os.path.join(inv_root, "routes"))
    open(os.path.join(inv_root, "database", "migrations",
                      "2025_01_01_000000_create_tasks_table.php"), "w").close()
    open(os.path.join(inv_root, "app", "Models", "Task.php"), "w").close()
    with open(os.path.join(inv_root, "routes", "api.php"), "w") as fh:
        fh.write("<?php\nRoute::get('/tasks', [TaskController::class, 'index']);\n")

    inv = nodes._repo_inventory(inv_root, API_ONLY)
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
        self.requests = []
        self.apply_put = True
        self.note_id = 0
        self.head = "h1"

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
        if path.endswith("/user"):
            return _FakeResponse({"id": 15})
        if "/repository/branches/" in path:
            if self.head is None:
                return _FakeResponse({"message": "404 Branch Not Found"}, 404)
            if self.head == "error":
                return _FakeResponse({"error": "down"}, 500)
            return _FakeResponse({"commit": {"id": self.head}})
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
        if "description" in json:
            candidate["description"] = json["description"]
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
            return _FakeResponse(self.add_note(iid, json["body"]), 201)
        if path.endswith("/issues"):
            iid = max(self.issues, default=0) + 1
            issue = self.add_issue(iid, [label for label in json.get("labels", "").split(",") if label],
                                   description=json["description"])
            issue["title"] = json["title"]
            return _FakeResponse(issue, 201)
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

print("\n── Scenario 12d-rerun: an unchanged failed issue is not re-run ──")
rerun = _IssueHTTP()
rerun.add_issue(30, description="Do it.")
rerun.add_issue(31)
rerun.add_issue(32)
rerun.issues[32]["description"] = None


def _mark_failed(iid, author=15, head="h1"):
    issue = rerun.issues[iid]
    rerun.add_note(iid, "AI Developer failed to produce passing tests (PHPUnit).\n\n"
                   + nodes.failed_run_marker(issue["title"], issue["description"] or "", head),
                   author=author)


def _rerun_pending():
    return [i["id"] for i in rerun.client().list_pending()]


_mark_failed(30)
_mark_failed(32)
check([i["id"] for i in rerun.client().list_pending(1)] == [31],
      "a stale-failed oldest issue is skipped and does not count toward the limit")
rerun.requests.clear()
check(_rerun_pending() == [31] and sum("/repository/branches/" in r[1] for r in rerun.requests) == 1,
      "unchanged title/description/HEAD excludes failed issues; HEAD read once per poll")
rerun.issues[30]["title"] = "Issue 30, clarified"
check(_rerun_pending() == [30, 31], "an edited title makes the failed issue pending again")
rerun.issues[30]["title"] = "Issue 30"
rerun.issues[30]["description"] = "Do it properly."
check(_rerun_pending() == [30, 31], "an edited description makes the failed issue pending again")
rerun.issues[30]["description"] = "Do it."
rerun.head = "h2"
check(_rerun_pending() == [30, 31, 32], "a new target-branch commit makes failed issues pending again")
rerun.head = None
check(_rerun_pending() == [30, 31, 32], "a missing target branch (404) matches no marker")
rerun.head = "error"
try:
    rerun.client().list_pending()
    _head_raised = False
except RuntimeError:
    _head_raised = True
check(_head_raised, "any other target-HEAD lookup error aborts the poll")
rerun.head = "h1"
_mark_failed(31, author=99)
check(_rerun_pending() == [31], "a failed-run marker by a foreign author is ignored")
_mark_failed(30, head="h0")
check(_rerun_pending() == [30, 31], "the latest trusted marker decides, older markers do not")

print("\n── Scenario 12d-omp: OMP escalation issue tools ──")
import graph.tools as _issue_tools  # noqa: E402
omp_http = _IssueHTTP()
_real_issue_client = _issue_tools.forge.issue_client
_issue_tools.forge.issue_client = omp_http.client
created = _issue_tools.tool_issue_create("OMP task", "Scope: backend\n\nDo it.")
check(created["success"] and "labels" not in omp_http.requests[0][2],
      "issue_create sends no labels")
omp_iid = created["result"]["id"]
_ordinary_post = omp_http.post
omp_http.post = lambda url, json=None, timeout=None: (
    _FakeResponse({"error": "down"}, 500) if url.endswith("/notes")
    else _ordinary_post(url, json=json, timeout=timeout))
resolved = _issue_tools.tool_issue_resolve(omp_iid, "anthropic/model")
check(not resolved["success"] and omp_http.issues[omp_iid]["state"] == "opened",
      "issue_resolve with a failing note leaves the issue open")
omp_http.post = _ordinary_post
omp_http.add_issue(31, ["nesti"])
check(not _issue_tools.tool_issue_resolve(31, "m")["success"]
      and omp_http.issues[31]["state"] == "opened",
      "issue_resolve refuses an opted-in issue")
handed = _issue_tools.tool_issue_handoff(omp_iid, "must_fix: tests")
check(handed["success"] and "nesti" in omp_http.issues[omp_iid]["labels"]
      and omp_http.issues[omp_iid]["description"].endswith(
          "## Third attempt (OMP team, advised) — rejected\n\nmust_fix: tests\n"),
      "issue_handoff adds the label and appends the section, read back")
resolved = _issue_tools.tool_issue_resolve(omp_http.add_issue(32, [])["iid"], "m")
check(resolved["success"] and omp_http.issues[32]["state"] == "closed"
      and omp_http.notes[32][-1]["body"] == "omp-developer / model: m",
      "issue_resolve closes with the model comment")
check(omp_http.notes[32] and all(n["trusted"] is True for n in omp_http.client().list_notes(32)),
      "GitLab notes are always trusted")
_issue_tools.forge.issue_client = _real_issue_client
with patch.dict(os.environ, {"NESTI_FORGE": "bogus"}):
    _bogus = _issue_tools.tool_issue_get(1)
check(not _bogus["success"] and "NESTI_FORGE='bogus' is not supported" in _bogus["error"],
      "an unknown NESTI_FORGE is a clear tool error, never a silent GitLab fallback")

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

# Inventory lists nested paths relative to their directory and prunes dependency trees.
print("\n── Inventory nested paths and pruning ──")
with tempfile.TemporaryDirectory(prefix="nesti-inventory-") as root:
    def put_file(relative, body):
        file = Path(root, relative)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(body, encoding="utf-8")
    put_file(".frontend/src/components/admin/Table.vue", "admin")
    put_file(".frontend/src/components/public/Table.vue", "public")
    put_file(".frontend/src/node_modules/x/Hidden.vue", "hidden")
    put_file("database/seeders/nested/TaskSeeder.php", "seeder")
    put_file("database/factories/nested/TaskFactory.php", "factory")
    backend = nodes._repo_inventory(root, API_ONLY, "backend")
    frontend = nodes._repo_inventory(root, ROOT_SPA, "frontend")
    check("nested/TaskSeeder.php" in backend and "nested/TaskFactory.php" in backend
          and "Table.vue" not in backend, "backend inventory keeps relative nested paths, no SPA")
    check(all(value in frontend for value in ("admin/Table.vue", "public/Table.vue"))
          and "Hidden.vue" not in frontend,
          "SPA context retains relative nested paths and prunes dependencies")

with tempfile.TemporaryDirectory(prefix="nesti-task-context-") as root:
    def put_target(relative, body):
        file = Path(root, relative)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(body, encoding="utf-8")
    target_body = '<template><p>Existing public task behaviour</p></template>\n'
    unrelated_body = '<template><p>Unrelated admin behaviour</p></template>\n'
    put_target(".frontend/src/components/public/Table.vue", target_body)
    put_target(".frontend/src/components/admin/Table.vue", unrelated_body)
    inventory = nodes._repo_inventory(
        root, ROOT_SPA, "frontend", "Filter .frontend/src/components/public/Table.vue")
    check(target_body in inventory and unrelated_body not in inventory,
          "a named nested target supplies its complete source without a same-name sibling")
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend", "Update Table.vue")
    check(target_body in inventory and unrelated_body in inventory,
          "an ambiguous basename exposes both real candidates instead of guessing one")
    existing_test = "import Table from '../public/Table.vue';\nconst mountOptions = { plugins: ['PrimeVue'] };\n"
    unrelated_test = "import Table from '../admin/Table.vue';\nconst adminOnly = true;\n"
    put_target(".frontend/src/components/__tests__/PublicFilters.test.js", existing_test)
    put_target(".frontend/src/components/__tests__/AdminFilters.test.js", unrelated_test)
    e2e_test = "import { test } from '@playwright/test';\nawait page.goto('/table');\n"
    put_target(".frontend/e2e/table.spec.js", e2e_test)
    put_target(".frontend/package.json", '{"type":"module"}')
    inventory = nodes._repo_inventory(
        root, ROOT_SPA, "frontend", "Filter .frontend/src/components/public/Table.vue")
    check(existing_test in inventory and unrelated_test not in inventory,
          "a component target brings its existing test setup even when the issue names no test")
    check(e2e_test in inventory and '{"type":"module"}' in inventory,
          "component context includes its conventional E2E setup and JavaScript module contract")
    put_target(".frontend/custom/retained.txt", "last valid attempt\n \t\n")
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend", "Update Table.vue",
                                      [".frontend/custom/retained.txt"])
    check("last valid attempt\n \t\n" in inventory,
          "retry includes complete prior changes even outside inventory directories")
    put_target(".frontend/src/components/public/Table.vue",
               "TARGET_OVERSIZE" + "x" * nodes._MAX_QUOTED_FILE_CHARS)
    inventory = nodes._repo_inventory(
        root, ROOT_SPA, "frontend", "Update .frontend/src/components/public/Table.vue")
    check("TARGET_OVERSIZE" not in inventory and "body omitted" in inventory,
          "task-target priority never turns an oversized source into a partial rewrite")

with tempfile.TemporaryDirectory(prefix="nesti-session-context-") as root:
    storage = "export const save = (t) => localStorage.setItem('app.token', t);\n"
    Path(root, ".frontend/src/api").mkdir(parents=True)
    Path(root, ".frontend/src/api/client.ts").write_text(storage)
    Path(root, ".frontend/src/Plain.vue").write_text("<template><p>plain</p></template>\n")
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend", "Add a page")
    check("Current .frontend/src/api/client.ts (complete)" in inventory and "<p>plain</p>" not in inventory,
          "an SPA without e2e/support/session.* quotes the file that stores its session")
    Path(root, ".frontend/e2e/support").mkdir(parents=True)
    Path(root, ".frontend/e2e/support/session.js").write_text("export async function signIn() {}\n")
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend", "Add a page")
    check("Current .frontend/e2e/support/session.js (complete)" in inventory
          and "localStorage.setItem('app.token'" not in inventory,
          "an existing session helper is quoted instead of the session storage source")

with tempfile.TemporaryDirectory(prefix="nesti-api-context-") as root:
    def put_contract(relative, body):
        path = Path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    put_contract("routes/api.php", "<?php\nuse App\\Http\\Controllers\\TaskController;\n")
    controller = (
        "<?php\nuse App\\Http\\Requests\\StoreTaskRequest;\n"
        "use App\\Services\\TaskIndexService;\n"
        "use App\\Http\\Resources\\TaskResource;\n"
    )
    request = "<?php\nreturn ['title' => ['required', 'string']];\n"
    service = "<?php\nuse App\\Http\\Controllers\\TaskController;\n$query->latest()->orderByDesc('id');\n"
    resource = "<?php\nreturn ['is_done' => (bool) $this->is_done];\n"
    put_contract("app/Http/Controllers/TaskController.php", controller)
    put_contract("app/Http/Requests/StoreTaskRequest.php", request)
    put_contract("app/Services/TaskIndexService.php", service)
    put_contract("app/Http/Resources/TaskResource.php", resource)
    put_contract("app/Services/Unrelated.php", "<?php\nUNRELATED_SECRET;\n")
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend", "Add task status radios")
    check(all(body in inventory for body in (controller, request, service, resource)),
          "frontend API context exposes accepted inputs, response fields and actual pagination order")
    check(inventory.count("Current app/Http/Controllers/TaskController.php (complete)") == 1
          and "UNRELATED_SECRET" not in inventory,
          "cyclic API references terminate and unrelated service bodies stay out")
    put_contract("routes/api.php", (
        "<?php\nuse App\\Http\\Controllers\\TaskController as Tasks;\n"
        "use App\\Http\\Controllers\\CurrencyController;\n"
        "Route::apiResource('tasks',\n Tasks::class);\n"
        "Route::get('/currency', [CurrencyController::class, 'index']);\n"
    ))
    put_contract("app/Http/Controllers/CurrencyController.php", "<?php\nUNRELATED_CURRENCY_BODY;\n")
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend",
                                      "Add TitleLength to Table.vue for GET /api/tasks")
    check(all(body in inventory for body in (controller, request, service, resource))
          and "UNRELATED_CURRENCY_BODY" not in inventory and "Route::get('/currency'" in inventory,
          "an /api route in the task keeps its multiline aliased contracts, excludes unrelated route bodies")
    put_contract("app/Services/TaskIndexService.php",
                 "<?php\nOVERSIZED_CONTRACT\n" + "x" * nodes._MAX_QUOTED_FILE_CHARS)
    inventory = nodes._repo_inventory(root, ROOT_SPA, "frontend")
    check("OVERSIZED_CONTRACT" not in inventory and request in inventory
          and "body omitted" in inventory,
          "oversized API source is omitted whole without losing other usable contracts")
    with tempfile.TemporaryDirectory(prefix="nesti-outside-contract-") as outside:
        external = Path(outside, "Outside.php")
        external.write_text("<?php\nOUTSIDE_CONTRACT_SECRET;\n")
        Path(root, "app/Services/Outside.php").symlink_to(external)
        put_contract("routes/api.php", "<?php\nuse App\\Services\\Outside;\n")
        check("OUTSIDE_CONTRACT_SECRET" not in nodes._repo_inventory(root, ROOT_SPA, "frontend"),
              "API reference discovery never quotes files outside the workspace")

print("\n── Playwright container lifecycle ──")
import frontend_runner as fr
import requests
import docker


def runner_case(root, exit_code, logs="sandbox log", error=None, start_error=None):
    """Run the real runner against a detached fake container."""
    removed = []
    names = []
    waits = []
    class Container:
        def wait(self, timeout):
            waits.append(timeout)
            if error:
                raise error
            return {"StatusCode": exit_code}
        def logs(self, **kwargs):
            return logs.encode()
    class Created:
        def __init__(self, name):
            self.name = name
        def remove(self, force, v):
            removed.append((self.name, force, v))
    def start(**kwargs):
        check(kwargs["detach"] is True and kwargs["remove"] is False,
              "runner retains enforceable detached lifecycle")
        check(kwargs["name"].startswith("nesti-fe-"), "sandbox container carries a nesti- name")
        names.append(kwargs["name"])
        check([(m["Target"], m["Type"], m["Source"]) for m in kwargs["mounts"]]
              == [("/app/node_modules", "volume", None)],
              "node_modules installs into an anonymous container volume")
        if start_error:
            raise start_error
        return Container()
    with patch.object(fr.docker, "from_env",
                      return_value=SimpleNamespace(containers=SimpleNamespace(run=start, get=Created))):
        runner = fr.FrontendRunner()
        result = runner.run_playwright(root)
    # Even when run() raises (start failed after create), removal goes by name.
    check(removed == [(names[0], True, True)],
          "every created container removed forcibly by name with its anonymous volume")
    if not start_error:
        check(waits == [runner.timeout], "container waits with configured timeout")
    return result


with tempfile.TemporaryDirectory(prefix="nesti-runner-") as root:
    check(runner_case(root, 0) == (True, "sandbox log"), "exit 0 is a green browser gate")
    passed, output = runner_case(root, 1, "1 failed")
    check(not passed and "1 failed" in output, "a failed suite keeps its container logs")
    passed, output = runner_case(root, 1, "partial log", requests.exceptions.ReadTimeout("timeout"))
    check(not passed and "partial log" in output and "timed out" in output,
          "a timeout keeps the partial logs")
    passed, output = runner_case(root, 1, start_error=docker.errors.ImageNotFound("missing image"))
    check(not passed and "not found" in output, "missing image is an ordinary failure")
    passed, _ = runner_case(root, 1, start_error=docker.errors.APIError("start failed after create"))
    check(not passed, "start failure after create is an ordinary failure, container still removed")

print("\n── PHPUnit PostgreSQL sidecar lifecycle ──")
import docker_runner as dr


def phpunit_case(root, exit_code=0, ready=True, error=None, sidecar_error=None):
    """Run the real run_tests against fake Docker; return (result, events, runs)."""
    events, runs, created = [], [], set()
    class Sandbox:
        def wait(self, timeout):
            if error:
                raise error
            return {"StatusCode": exit_code}
        def logs(self, **kwargs):
            return b"Tests: 3 passed"
        def remove(self, force):
            events.append(("sandbox-removed", force))
    class Sidecar:
        def exec_run(self, cmd):
            events.append(("exec", cmd[0]))
            return SimpleNamespace(exit_code=0 if ready or cmd[0] == "psql" else 2, output=b"")
        def remove(self, force, v):
            events.append(("pg-removed", force, v))
    class Network:
        def __init__(self, name):
            self.name = name
        def remove(self):
            events.append(("net-removed", self.name))
    def run(**kwargs):
        runs.append(kwargs)
        if kwargs["image"] != dr._POSTGRES_IMAGE:
            return Sandbox()
        created.add(kwargs["name"])
        if sidecar_error:
            raise sidecar_error
        return Sidecar()
    def get(name):
        if name not in created:
            raise docker.errors.NotFound(name)
        return Sidecar()
    def create(name, driver):
        events.append(("net-created", name, driver))
        return Network(name)
    client = SimpleNamespace(containers=SimpleNamespace(run=run, get=get),
                             networks=SimpleNamespace(create=create))
    with patch.object(dr.docker, "from_env", return_value=client), \
            patch.object(dr, "_PG_READY_TIMEOUT", 0):
        return dr.DockerRunner().run_tests(root), events, runs


_PG_XML = ('<phpunit><php><env name="DB_CONNECTION" value="pgsql" force="true"/>'
           '<env name="DB_DATABASE" value="app_test"/><server name="DB_USERNAME" value="app_user"/></php></phpunit>')
with tempfile.TemporaryDirectory(prefix="nesti-pg-") as root:
    Path(root, "phpunit.xml").write_text(_PG_XML)
    for code in (0, 1):
        (ok, output), events, runs = phpunit_case(root, exit_code=code)
        sidecar, sandbox = runs
        network = events[0][1]
        check(ok is (code == 0) and "Tests: 3 passed" in output, f"pgsql run follows sandbox exit {code}")
        check(network.startswith("nesti-run-") and events[0][2] == "bridge"
              and sidecar["name"] == network.replace("-run-", "-pg-") and sidecar["network"] == network,
              "sidecar nesti-pg-* starts on its own nesti-run-* bridge network")
        env = sandbox["environment"]
        check(sandbox["network"] == network and sandbox["command"] == dr._TEST_COMMAND
              and env["DB_CONNECTION"] == "pgsql" and env["DB_HOST"] == sidecar["name"]
              and env["DB_PORT"] == "5432" and env["DB_DATABASE"] == "app_test"
              and env["DB_USERNAME"] == "app_user" and len(env["DB_PASSWORD"]) == 32,
              "sandbox joins the network with the phpunit.xml database settings")
        check(events[-3:] == [("sandbox-removed", True), ("pg-removed", True, True), ("net-removed", network)],
              "sandbox, sidecar (with its volume) and network removed")
    (ok, output), events, runs = phpunit_case(root, error=requests.exceptions.ReadTimeout("t"))
    check(not ok and "timed out" in output and events[-2:] == [("pg-removed", True, True), ("net-removed", events[0][1])],
          "sandbox timeout still removes sidecar and network")
    (ok, output), events, runs = phpunit_case(root, ready=False)
    check(not ok and "not ready" in output and len(runs) == 1
          and events[-2:] == [("pg-removed", True, True), ("net-removed", events[0][1])],
          "readiness failure never starts the sandbox and removes sidecar and network")
    (ok, output), events, runs = phpunit_case(root, sidecar_error=docker.errors.APIError("start failed"))
    check(not ok and "PostgreSQL sidecar failed" in output and len(runs) == 1
          and events[-2:] == [("pg-removed", True, True), ("net-removed", events[0][1])],
          "sidecar start failure removes the created container by name and the network")
with tempfile.TemporaryDirectory(prefix="nesti-pg-dist-") as root:
    Path(root, "phpunit.xml.dist").write_text('<phpunit><php><env name="DB_CONNECTION" value="pgsql"/></php></phpunit>')
    (ok, _), _, runs = phpunit_case(root)
    check(ok and runs[1]["environment"]["DB_DATABASE"] == "testing"
          and runs[1]["environment"]["DB_USERNAME"] == "testing", "phpunit.xml.dist fallback with testing defaults")
    Path(root, "phpunit.xml").write_text(_PG_XML.replace("app_test", "x&quot;; DROP"))
    (ok, output), events, runs = phpunit_case(root)
    check(not ok and "identifiers" in output and not events and not runs, "unsafe identifier starts nothing")
with tempfile.TemporaryDirectory(prefix="nesti-sqlite-") as root:
    for xml in (None, '<phpunit><php><env name="DB_CONNECTION" value="sqlite"/></php></phpunit>'):
        if xml:
            Path(root, "phpunit.xml").write_text(xml)
        (ok, _), events, runs = phpunit_case(root)
        check(ok and not events[:-1] and len(runs) == 1 and runs[0]["command"] == dr._TEST_COMMAND
              and runs[0]["environment"] is None and runs[0]["network"] is None,
              "SQLite project starts no sidecar and keeps command/env")
_cmd = next(line for line in Path(__file__).resolve().with_name("Dockerfile.sandbox").read_text().splitlines()
            if line.startswith("CMD "))
check(json.loads(_cmd[4:]) == dr._TEST_COMMAND, "Dockerfile.sandbox CMD is byte-identical to _TEST_COMMAND")

print("\n── Rejected claim ──")
reset_calls(312)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
nodes.tool_issue_set_status = lambda *args, **kwargs: {"success": False, "error": "claim rejected"}
final = compiled.invoke(initial(312), config={"recursion_limit": 60})
check(not calls["workspaces"] and not calls["bootstrap"] and not calls["plan_prompts"]
      and not calls["code_prompts"] and final["failure_reason"],
      "rejected initial claim cannot clone, bootstrap or invoke LLM")

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


# ═════ Scenario 33: separated (monorepo) layout ═════
print("\n── Scenario 33: separated backend/ + frontend/ layout ──")
from pathlib import Path                                 # noqa: E402
import project_layout                                    # noqa: E402
from docker_runner import DockerRunner                   # noqa: E402
from graph.tools import tool_laravel_bootstrap           # noqa: E402


def _put(root, relative, body=""):
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(body)


def _monorepo(root):
    _put(root, "backend/artisan")
    _put(root, "backend/composer.json", '{"require": {"dedoc/scramble": "^0.12"}}')
    _put(root, "backend/routes/api.php", "<?php\n")
    _put(root, "backend/vite.config.js", "export default {};\n")
    _put(root, "frontend/package.json", json.dumps({
        "type": "module", "dependencies": {"vue": "^3.5.0", "primevue": "^4.4.1"}}))
    _put(root, "frontend/playwright.config.js", "// EXISTING\n")


mono = tempfile.mkdtemp(prefix="nesti-mono-")
try:
    _monorepo(mono)
    sep = lambda files: tool_detect_stack(mono, files, "backend", "frontend")["result"]
    r = sep(["backend/app/Http/Controllers/X.php", "backend/routes/api.php"])
    check(r["run_phpunit"] and r["run_openapi"] and not r["run_frontend"],
          "separated: backend controller + api.php → PHPUnit + OpenAPI, no frontend layers")
    _put(mono, "frontend/src/components/X.vue", "<template/>")
    r = sep(["frontend/src/components/X.vue"])
    check(r["run_frontend"] and not r["run_phpunit"] and not r["run_openapi"],
          "separated: frontend .vue → Vitest/Playwright, no PHPUnit")
    _put(mono, "backend/resources/js/X.vue", "<template/>")
    r = sep(["backend/resources/js/X.vue"])
    check(not r["run_frontend"] and r["run_phpunit"],
          "separated: a .vue under backend/ never counts as frontend")

    try:
        DockerRunner.write_files(
            "### DELETE: backend/database/migrations/2024_x.php\n", mono)
        _refused = False
    except ValueError:
        _refused = True
    check(_refused, "write_files refuses to DELETE backend/database/migrations/*")

    boot = tool_laravel_bootstrap(
        os.path.join(mono, "backend"), spa_path=os.path.join(mono, "frontend"))
    check(boot["success"], "bootstrap with spa_path tops up the backend and the SPA")
    check(os.path.isfile(os.path.join(mono, "backend/tests/Feature/OpenApiDocumentationTest.php"))
          and os.path.isfile(os.path.join(mono, "frontend/vitest.config.js")),
          "bootstrap writes the backend OpenAPI test and the SPA vitest config")
    check(open(os.path.join(mono, "frontend/playwright.config.js")).read() == "// EXISTING\n",
          "an existing SPA playwright.config.js stays untouched")
    _pkg = json.load(open(os.path.join(mono, "frontend/package.json")))
    check("vitest" in _pkg["devDependencies"]
          and _pkg["devDependencies"]["@playwright/test"] == "1.50.0"
          and _pkg["dependencies"]["primevue"] == "^4.4.1",
          "SPA package.json gains vitest/@playwright/test 1.50.0 and keeps primevue ^4.4.1")
    check(os.path.isfile(os.path.join(mono, "frontend/vitest.setup.js")),
          "bootstrap writes the absent SPA vitest.setup.js (jsdom polyfills)")
    import hashlib  # noqa: E402
    import graph.tools as _tools  # noqa: E402
    with patch.object(_tools, "_SUPERSEDED_SPA_VITEST_CONFIGS", {hashlib.sha256(b"old").hexdigest()}):
        for body, upgraded in ((b"old", True), (b"custom", False)):
            Path(mono, "frontend/vitest.config.js").write_bytes(body)
            boot = tool_laravel_bootstrap(
                os.path.join(mono, "backend"), spa_path=os.path.join(mono, "frontend"))
            replaced = Path(mono, "frontend/vitest.config.js").read_bytes() != body
            check(boot["success"] and replaced is upgraded
                  and ("frontend/vitest.config.js" in boot["result"]["reason"]) is upgraded,
                  f"an SPA vitest.config.js {body!r} is {'upgraded in place' if upgraded else 'left untouched'}")
finally:
    shutil.rmtree(mono, ignore_errors=True)

print("\n── Backend code prompt carries routing and test conventions ──")
from prompt_builder import build_code_prompt             # noqa: E402
conv = tempfile.mkdtemp(prefix="nesti-conv-")
try:
    _put(conv, "backend/artisan")
    _put(conv, "backend/bootstrap/app.php",
         "<?php\nreturn Application::configure()->withRouting(\n"
         "    api: __DIR__.'/../routes/api.php', apiPrefix: '',\n)->create();\n")
    _put(conv, "backend/routes/api.php",
         "<?php\nforeach (['Admin'] as $d) { require __DIR__.'/domains/'.$d.'.php'; }\n")
    _put(conv, "backend/routes/domains/Admin.php",
         "<?php\nRoute::middleware(['bearer', 'roles:Admin'])->group(fn () => Route::get('/panel', X::class));\n")
    _put(conv, "backend/tests/TestCase.php", "<?php\nabstract class TestCase { function TESTCASE_HELPER() {} }\n")
    _put(conv, "backend/tests/Feature/PanelAdminTest.php",
         "<?php\nclass PanelAdminTest { function test_admin() { $this->withToken(ADMIN_TOKEN_SETUP);"
         " $this->getJson('/panel'); } }\n")
    _put(conv, "backend/tests/Feature/InvoiceExportTest.php",
         "<?php\nclass InvoiceExportTest { function test_export() { $this->getJson('/invoices/export'); } }\n")
    _put(conv, "backend/app/Providers/AppServiceProvider.php", "<?php\nclass AppServiceProvider {}\n")
    _put(conv, "backend/app/Providers/DocsServiceProvider.php",
         "<?php\nScramble::routes(fn ($r) => preg_match('#^(SCRAMBLE_FILTER_ENTRY)(/|$)#', $r->uri()));\n")
    _layout = {"backend": "backend", "frontend": "frontend"}
    _task = "Add a GET /api/status endpoint for admin users only, returning the panel status."
    _ctx = nodes._repo_inventory(conv, _layout, "backend", _task)
    _sys, _user = build_code_prompt({"subject": "status", "description": _task}, "1. route + test",
                                    repo_context=_ctx, scope="backend", layout=_layout)
    check("apiPrefix: ''" in _user and "Current backend/bootstrap/app.php (complete)" in _user,
          "code prompt quotes bootstrap/app.php with its apiPrefix")
    check("Current backend/routes/domains/Admin.php" in _user and "roles:Admin" in _user,
          "code prompt quotes route files loaded from routes/ subdirectories")
    check("TESTCASE_HELPER" in _user and "ADMIN_TOKEN_SETUP" in _user and "/invoices/export" not in _user,
          "code prompt quotes TestCase.php and the most relevant HTTP Feature test only")
    check("served under the /api prefix" not in _sys and "apiPrefix" in _sys,
          "backend standards no longer assume a fixed /api prefix")
    _front = nodes._repo_inventory(conv, _layout, "frontend", _task)
    check("apiPrefix: ''" in _front and "TESTCASE_HELPER" not in _front and "ADMIN_TOKEN_SETUP" not in _front,
          "frontend scope sees the routing prefix but no PHP test conventions")
    check("Current backend/app/Providers/DocsServiceProvider.php (complete)" in _user
          and "SCRAMBLE_FILTER_ENTRY" in _user and "Scramble::routes(" in _sys,
          "backend code prompt quotes the Scramble::routes filter and says to admit new routes")
    check("SCRAMBLE_FILTER_ENTRY" not in _front, "frontend scope does not quote the Scramble filter")
finally:
    shutil.rmtree(conv, ignore_errors=True)

print("\n── Coding prompt: tree-sitter PHP skeletons of reference files ──")
import code_skeleton                                     # noqa: E402
_sk_body = "".join(f"        $step{i} = {i};\n" for i in range(6))
sk = tempfile.mkdtemp(prefix="nesti-skel-")
try:
    _put(sk, "backend/artisan")
    _put(sk, "backend/routes/api.php",
         "<?php\nRoute::get('/orders', [App\\Http\\Controllers\\OrderController::class, 'index']);\n")
    _put(sk, "backend/app/Http/Controllers/OrderController.php",
         "<?php\nclass OrderController\n{\n"
         "    public function index(): array\n    {\n" + _sk_body + "        return ['ELIDED_MARKER'];\n    }\n\n"
         "    public function rules(): array\n    {\n" + _sk_body + "        return ['RULES_MARKER'];\n    }\n}\n")
    _put(sk, "backend/tests/Feature/OrderTest.php",
         "<?php\nclass OrderTest extends TestCase\n{\n"
         "    public function test_lists(): void\n    {\n" + _sk_body
         + "        $this->getJson('/orders?HTTP_MARKER');\n    }\n\n"
         "    private function seed(): void\n    {\n" + _sk_body + "        $x = 'SEED_MARKER';\n    }\n}\n")
    _sk_layout = {"backend": "backend", "frontend": None}
    _sk_controller = "backend/app/Http/Controllers/OrderController.php"
    _sk_before = Path(sk, _sk_controller).read_text()
    try:
        DockerRunner.write_files(f"### FILE: {_sk_controller}\n```php\n<?php\n```\n", sk, [_sk_controller])
        _sk_error = ""
    except ValueError as exc:
        _sk_error = str(exc)
    check("skeleton" in _sk_error and Path(sk, _sk_controller).read_text() == _sk_before,
          "write_files refuses a FILE block for a skeleton-quoted file and leaves it untouched")
    if code_skeleton._parser() is not None:
        _task = "List the orders"
        _plain = nodes._repo_inventory(sk, _sk_layout, "backend", _task)
        check("ELIDED_MARKER" in _plain and "SEED_MARKER" in _plain,
              "without skeletons (plan prompt) reference files stay complete")
        _skel: list[str] = []
        _ctx = nodes._repo_inventory(sk, _sk_layout, "backend", _task, skeletons=_skel)
        check("ELIDED_MARKER" in _ctx and "RULES_MARKER" in _ctx,
              "an API contract file stays complete with skeletons on")
        check("SEED_MARKER" not in _ctx and "HTTP_MARKER" in _ctx and "(skeleton: long method bodies elided" in _ctx,
              "the example Feature test is a skeleton: long helper elided, first HTTP test kept, labelled")
        check(sorted(_skel) == ["backend/tests/Feature/OrderTest.php"],
              f"only the example Feature test is reported, with its prefix (got {_skel})")
        _named: list[str] = []
        _ctx = nodes._repo_inventory(sk, _sk_layout, "backend", "Fix OrderTest.php", skeletons=_named)
        check("SEED_MARKER" in _ctx and _named == [],
              "a Feature test the task names stays complete")
        _put(sk, "backend/app/Domains/Orders/OrderModel.php",
             "<?php\nclass OrderModel\n{\n    public function total(): int\n    {\n"
             + _sk_body + "        return 'DOMAIN_MARKER';\n    }\n}\n")
        _dom: list[str] = []
        _ctx = nodes._repo_inventory(sk, _sk_layout, "backend", _task, skeletons=_dom,
                                     domain={"selected": ["Orders"], "names": ["Orders"], "root": "Domains",
                                             "route_files": [], "foreign_route_files": []})
        check("DOMAIN_MARKER" in _ctx and not any("Domains" in p for p in _dom),
              "a domain file stays complete with skeletons on")
    else:
        print("  (skipped: php grammar not downloaded)")
finally:
    shutil.rmtree(sk, ignore_errors=True)

print("\n── OpenAPI gate: /api-prefixed versus unprefixed (HEAD baseline) ──")
import graph.tools as _gt                                # noqa: E402
from git import Repo as _Repo                            # noqa: E402


def _route(uri, method="GET|HEAD"):
    return {"uri": uri, "method": method, "middleware": ["api"]}


def gate_case(workspace, current, documented, head=(), head_ok=True, baseline=None):
    """Run the real gate with a fake sandbox that writes the dumps it is asked for."""
    runs = []

    def dump(path, routes):
        target = Path(path, _gt._ROUTE_DUMP_REL)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(list(routes)))

    class FakeRunner:
        def run_openapi_export(self, path):
            runs.append(("openapi", path))
            Path(path, "openapi.json").write_text(json.dumps({
                "openapi": "3.1.0", "servers": [{"url": "http://localhost:8000"}],
                "paths": {key: {method: {} for method in methods} for key, methods in documented.items()}}))
            dump(path, current)
            return True, "exported"

        def run_route_list(self, path):
            runs.append(("route-list", path))
            if head_ok:
                dump(path, head)
            return head_ok, "head routes" if head_ok else "HEAD boom"

    with patch.object(_gt, "DockerRunner", FakeRunner):
        result = _gt.tool_openapi_export(workspace, baseline)
    return result["result"], runs


gate_root = tempfile.mkdtemp(prefix="nesti-gate-")
try:
    _repo = _Repo.init(gate_root)
    _put(gate_root, "backend/routes/api.php", "<?php\n")
    _repo.index.add(["backend/routes/api.php"])
    _repo.index.commit("init")
    _ws = os.path.join(gate_root, "backend")

    r, runs = gate_case(_ws, [_route("api/tasks", "POST")], {"/other": ["get"]})
    check(not r["passed"] and r["undocumented"] == ["POST /api/tasks"] and "baseline_routes" not in r
          and [kind for kind, _ in runs] == ["openapi"],
          "prefixed: undocumented /api route fails exactly as before, no HEAD export")
    r, _ = gate_case(_ws, [_route("api/tasks", "POST")], {"/api/tasks": ["post"]})
    check(r["passed"], "prefixed: documented /api route passes")
    r, _ = gate_case(_ws, [_route("api/ping", "HEAD")], {"/other": ["get"]})
    check(not r["passed"] and "no route under /api is registered" in r["output"],
          "prefixed: no checkable /api route keeps the 'no route registered' failure")

    _head = [_route("health/live")]
    _current = [_route("health/live"), _route("test"), {"uri": "docs/api", "method": "GET|HEAD",
                                                        "middleware": ["web"]}]
    r, runs = gate_case(_ws, _current, {"/auth/login": ["post"]}, head=_head)
    check(not r["passed"] and r["undocumented"] == ["GET /test"]
          and r["baseline_routes"] == ["GET health/live"]
          and [kind for kind, _ in runs] == ["openapi", "route-list"]
          and runs[1][1].endswith(os.path.join("head", "backend")),
          "unprefixed: a new undocumented api-group route fails against the HEAD worktree baseline")
    check(len(_repo.git.worktree("list").splitlines()) == 1
          and not _repo.is_dirty(untracked_files=False),
          "the HEAD worktree is removed and the clone is untouched")
    r, runs = gate_case(_ws, _current, {"/test": ["get"]}, head=_head)
    check(r["passed"] and "GET /health/live" not in r["undocumented"],
          "unprefixed: new documented route passes; pre-existing undocumented /health is not re-checked")
    r, _ = gate_case(_ws, _head, {"/auth/login": ["post"]}, head=_head)
    check(r["passed"] and "No new API route" in r["output"],
          "unprefixed: an existing-controller-only change (no new api route) passes")
    r, runs = gate_case(_ws, _current, {"/test": ["get"]}, head_ok=False)
    check(not r["passed"] and "Could not export the HEAD route list" in r["output"]
          and "HEAD boom" in r["output"], "unprefixed: a failed HEAD export fails closed")
    r, runs = gate_case(_ws, _current, {"/auth/login": ["post"]}, baseline=["GET health/live"])
    check(r["undocumented"] == ["GET /test"] and [kind for kind, _ in runs] == ["openapi"],
          "a supplied baseline skips the HEAD export")

    _seen = []

    def _caching_gate(path, baseline_routes=None):
        _seen.append(baseline_routes)
        extra = {} if baseline_routes is not None else {"baseline_routes": ["GET health/live"]}
        return {"success": True, "result": {"passed": True, "output": "", "paths": [],
                                            "undocumented": [], **extra}}
    _gate_state = {"repo_path": gate_root, "layout": {"backend": "backend", "frontend": None}}
    with patch.object(nodes, "tool_openapi_export", _caching_gate):
        _gate_state.update(nodes.node_openapi_test(_gate_state))
        _gate_state.update(nodes.node_openapi_test(_gate_state))
    check(_seen == [None, ["GET health/live"]]
          and _gate_state["openapi_baseline_routes"] == ["GET health/live"],
          "node_openapi_test exports the HEAD baseline once and reuses it")
finally:
    shutil.rmtree(gate_root, ignore_errors=True)

_state_dir = tempfile.mkdtemp(prefix="nesti-state-")
_saved_layout = (project_layout.STATE_DIR, project_layout.LAYOUT_FILE)
project_layout.STATE_DIR = Path(_state_dir)
project_layout.LAYOUT_FILE = Path(_state_dir, "layout.json")
project_layout.LAYOUT_FILE.write_text(json.dumps(
    {"schema": 1, "layout": {"backend": "backend", "frontend": "frontend"}}))
try:
    reset_calls(133)
    patch_tools(docker_outcomes=[True], code_responses=[
        "### FILE: backend/routes/api.php\n```php\n<?php\n```\n\n"
        "### FILE: backend/app/Http/Controllers/X.php\n```php\n<?php\n```\n\n"
        "### FILE: frontend/src/components/X.vue\n```vue\n<template/>\n```\n"], layout=None)

    def mono_clone(target_path):
        os.makedirs(target_path, exist_ok=True)
        calls["workspaces"].append(os.path.dirname(target_path))
        _monorepo(target_path)
        return {"success": True, "result": {"repo_path": target_path, "head_sha": "b" * 40}}
    nodes.tool_gitlab_clone = mono_clone
    f = compiled.invoke(initial(133), config={"recursion_limit": 60})
    _clone = os.path.join(calls["workspaces"][0], "repo")
    _paths = dict(calls["layer_paths"])
    check(f["mr_url"] and f["layout"] == {"backend": "backend", "frontend": "frontend"},
          "monorepo graph run reaches the MR with the saved separated layout")
    check(_paths.get("docker") == os.path.join(_clone, "backend")
          and _paths.get("openapi") == os.path.join(_clone, "backend"),
          "PHPUnit and OpenAPI receive <clone>/backend")
    check(_paths.get("vitest") == os.path.join(_clone, "frontend")
          and _paths.get("playwright") == os.path.join(_clone, "frontend"),
          "Vitest and Playwright receive <clone>/frontend")
    check(calls["bootstrap"] == [(os.path.join(_clone, "backend"), os.path.join(_clone, "frontend"))],
          "node_bootstrap tops up backend/ with the SPA path")
    check(calls["starter"] == [], "an existing SPA is continued, never re-scaffolded")
    check("REPOSITORY LAYOUT (strict)" in calls["code_systems"][0]
          and "primevue ^4.4.1" in calls["code_systems"][0],
          "the coding prompt carries the layout block with installed SPA versions")
finally:
    project_layout.STATE_DIR, project_layout.LAYOUT_FILE = _saved_layout
    shutil.rmtree(_state_dir, ignore_errors=True)

# ═════ Scenario 34: backend domain detection ═════
print("\n── Scenario 34: backend domain detection ──")
import issue_domain  # noqa: E402


def _domain_tree(root):
    _put(root, "artisan")
    _put(root, "composer.json", "{}")
    for d in ("Announcements", "Members"):
        _put(root, f"app/Domains/{d}/Http/Controllers/{d}Controller.php",
             f"<?php\nnamespace App\\Domains\\{d}\\Http\\Controllers;\n// SENTINEL_{d}\n")
        _put(root, f"app/Domains/{d}/Models/X.php", "<?php\n")
        _put(root, f"routes/domains/{d}.php",
             f"<?php\nuse App\\Domains\\{d}\\Http\\Controllers\\{d}Controller;\n"
             f"Route::prefix('{d.lower()}')->group(function () {{\n"
             f"    Route::get('/', [{d}Controller::class, 'index']);\n}});\n")
    _put(root, "routes/api.php",
         "<?php\nuse App\\Http\\Controllers\\TestController;\n"
         "Route::get('/test', [TestController::class, '__invoke']);\n"
         "foreach (['Announcements', 'Members'] as $d) {\n"
         "    require __DIR__.'/domains/'.$d.'.php';\n}\n")


def domain_clone(target_path):
    os.makedirs(target_path, exist_ok=True)
    calls["workspaces"].append(os.path.dirname(target_path))
    _domain_tree(target_path)
    return {"success": True, "result": {"repo_path": target_path, "head_sha": "b" * 40}}


_domain_probe = tempfile.mkdtemp(prefix="nesti-domain-")
try:
    _domain_tree(_domain_probe)
    _cat = issue_domain.domain_catalog(Path(_domain_probe))
    check([d["name"] for d in _cat["domains"]] == ["Announcements", "Members"]
          and _cat["domains"][0]["route_files"] == ["routes/domains/Announcements.php"],
          "domain catalog lists the domains and their route files")
    _dec = issue_domain.detect("Add GET /announcements/active", "", _cat)
    check(_dec.domains == ("Announcements",) and not _dec.ask, "a route under a domain prefix decides it")
    check(issue_domain.detect("Add POST /api/members/{id}/notes", "", _cat).domains == ("Members",),
          "a leading api/ segment is ignored")
    _dec = issue_domain.detect("Add a GET /test endpoint", "", _cat)
    check(_dec.domains == () and _dec.ask and "/test" in _dec.basis,
          "a route outside every domain asks")
    _dec = issue_domain.detect("Domain: Members", "", _cat)
    check(_dec.domains == ("Members",) and _dec.basis == "stated in the issue", "a stated domain decides it")
    _dec = issue_domain.detect("Domain: Members, also the Announcements domain", "", _cat)
    check(_dec.domains == ("Announcements", "Members") and not _dec.ask,
          "two stated domains are both decided without a question")
    _dec = issue_domain.detect("Domain: Members", "Also add GET /announcements/pinned", _cat)
    check(_dec.domains == ("Announcements", "Members") and not _dec.ask
          and _dec.basis == "stated in the issue; route /announcements/pinned",
          "a stated domain plus a route owned by a second domain decides both")
    check(issue_domain.detect("Domain: Members", "Add GET /test", _cat).ask,
          "a stated domain does not hide a route outside every domain")
    _dec = issue_domain.detect("Add GET /announcements/x and GET /members/y", "", _cat)
    check(_dec.domains == ("Announcements", "Members") and not _dec.ask,
          "routes owned by two distinct domains decide both")
    _dec = issue_domain.detect("Show the active announcements", "", _cat)
    check(_dec.domains == () and not _dec.ask, "no route or domain leaves it to the classifier")
    _put(_domain_probe, "routes/domains/Shared.php",
         "<?php\nuse App\\Domains\\Announcements\\Http\\Controllers\\AnnouncementsController;\n"
         "use App\\Domains\\Members\\Http\\Controllers\\MembersController;\n"
         "Route::get('/board', fn () => null);\n")
    _dec = issue_domain.detect("Add GET /board/pinned", "", issue_domain.domain_catalog(Path(_domain_probe)))
    check(_dec.domains == () and _dec.ask and "several domains" in _dec.basis,
          "one route path owned by two domains asks")
    _opts = ["Announcements", "Members"]
    check(issue_domain.parse_answer("2", _opts) == ["Members"]
          and issue_domain.parse_answer("`Announcements` please", _opts) == ["Announcements"]
          and issue_domain.parse_answer("> 1. `Announcements`\n\nMembers", _opts) == ["Members"],
          "answers parse by number or name, ignoring the quoted question")
    check(issue_domain.parse_answer("Members and Announcements", _opts) == _opts
          and issue_domain.parse_answer("1, 2", _opts) == _opts
          and issue_domain.parse_answer("2 and 1", _opts) == _opts,
          "a reply naming two domains, by name or number, selects both")
    check(issue_domain.parse_answer("3", _opts) == [] and issue_domain.parse_answer("1, 3", _opts) == []
          and issue_domain.parse_answer("0", _opts) == [] and issue_domain.parse_answer("no idea", _opts) == [],
          "an out-of-range number or no match is unmatched")
    check(issue_domain.parse_answer("1,2,", _opts) == _opts and issue_domain.parse_answer("2.", _opts) == ["Members"],
          "a trailing comma or period after the numbers still selects")
    check(issue_domain.parse_answer("I tried 2 times, use Members", _opts) == ["Members"]
          and issue_domain.parse_answer("tried 2 times", _opts) == [],
          "prose with a stray digit never selects by number")
    import time as _time  # noqa: E402
    _t0 = _time.perf_counter()
    _slow = issue_domain.parse_answer("".join(f"{i}{' ' * 3000}" for i in range(1, 9)) + "x", _opts)
    check(_slow == [] and _time.perf_counter() - _t0 < 1,
          "a reply with long whitespace gaps parses quickly and stays unmatched")
    _put(_domain_probe, "app/Http/Controllers/TestController.php", "<?php\n// SHARED_API\n")
    _put(_domain_probe, "app/Domains/Billing/Http/Controllers/BillingController.php",
         "<?php\nnamespace App\\Domains\\Billing\\Http\\Controllers;\n// SENTINEL_Billing\n")
    _put(_domain_probe, "routes/domains/Billing.php",
         "<?php\nuse App\\Domains\\Billing\\Http\\Controllers\\BillingController;\n"
         "Route::get('/billing', [BillingController::class, 'index']); // BILLING_ROUTES\n")
    _put(_domain_probe, "routes/api.php",
         "<?php\nuse App\\Http\\Controllers\\TestController;\n"
         "use App\\Domains\\Billing\\Http\\Controllers\\BillingController;\n"
         "Route::get('/test', [TestController::class, '__invoke']);\n"
         "Route::get('/invoices', [BillingController::class, 'index']);\n")
    os.remove(os.path.join(_domain_probe, "routes/domains/Shared.php"))
    _cat3 = issue_domain.domain_catalog(Path(_domain_probe))
    _two = issue_domain.selection(_cat3, ["Members", "Announcements"])
    check(_two["selected"] == ["Announcements", "Members"]
          and _two["foreign_route_files"] == ["routes/domains/Billing.php"],
          "a two-domain selection keeps catalog order and marks the third domain's route file foreign")
    _inv = nodes._repo_inventory(_domain_probe, {"backend": ".", "frontend": None}, "backend",
                                 "Add notes", domain=_two)
    check("SENTINEL_Announcements" in _inv and "SENTINEL_Members" in _inv and "SHARED_API" in _inv
          and "SENTINEL_Billing" not in _inv and "Domains/Billing/" not in _inv and "BILLING_ROUTES" not in _inv,
          "a two-domain selection quotes both domains and shared API files, never the third domain")
    _all = nodes._repo_inventory(_domain_probe, {"backend": ".", "frontend": None}, "backend", "Add notes")
    check("SENTINEL_Billing" in _all and "BILLING_ROUTES" in _all
          and nodes._repo_inventory(_domain_probe, {"backend": ".", "frontend": None}, "backend",
                                    "Add notes", domain=issue_domain.selection(_cat3, [])) == _all,
          "an empty selection filters nothing: the inventory equals the one without a domain")
finally:
    shutil.rmtree(_domain_probe, ignore_errors=True)


def _domain_run(n, subject, answer=None, classify_reply=None, answer_raises=False):
    reset_calls(n)
    patch_tools(docker_outcomes=[True], code_responses=[PHP_CODE])
    nodes.tool_gitlab_clone = domain_clone
    calls["asks"] = []

    def fake_answer(issue_id, options):
        if answer_raises:
            raise AssertionError("domain answer looked up for a frontend issue")
        return {"success": True, "result": answer}

    def fake_ask(issue_id, options):
        calls["asks"].append(options)
        return {"success": True, "result": {"issue_id": issue_id, "options": options}}
    nodes.tool_issue_domain_answer = fake_answer
    nodes.tool_issue_ask_domain = fake_ask
    if classify_reply is not None:
        def fake_plan(sp, up, messages=None):
            if sp.startswith("You decide which backend domain"):
                return classify_reply
            calls["plan_messages"].append(messages)
            calls["plan_prompts"].append(up)
            calls["plan_systems"].append(sp)
            return "1. Objective: implement Hello\n2. Files: src/Hello.php"
        nodes._llm.generate_plan = fake_plan
    return compiled.invoke(initial(n, subject, "Implement the thing."), config={"recursion_limit": 60})


f = _domain_run(3401, "Add a GET /test endpoint")
check(calls["asks"] == [["Announcements", "Members"]]
      and f["failure_reason"].startswith("Paused for a domain question")
      and not calls["bootstrap"] and not calls["plan_prompts"]
      and not any(os.path.exists(w) for w in calls["workspaces"]),
      "an unowned route asks once, pauses and cleans up before bootstrap or planning")
f = _domain_run(3402, "Add GET /announcements/active")
check(not calls["asks"] and f["domain"]["selected"] == ["Announcements"], "a domain route decides without asking")
check(all("This issue belongs to the Announcements domain" in s and "routes/domains/Announcements.php" in s
          for s in (calls["plan_systems"][0], calls["code_systems"][0])),
      "plan and code prompts carry the architecture block for the chosen domain")
check("Current app/Domains/Announcements/Http/Controllers/AnnouncementsController.php (complete)"
      in calls["plan_prompts"][0] and "MembersController.php (complete)" not in calls["plan_prompts"][0],
      "the plan prompt quotes the chosen domain's files only")
_one = '```json\n{"domains": ["Announcements"], "reason": "announcements"}\n```'
f = _domain_run(3403, "Show only active announcements", classify_reply=_one)
check(not calls["asks"] and f["domain"]["selected"] == ["Announcements"], "a single classified domain is accepted")
f = _domain_run(3404, "Show only active announcements",
                classify_reply='{"domains": ["Announcements", "Members"], "reason": "both"}')
check(calls["asks"] and "2 plausible domains" in f["failure_reason"],
      "two plausible classified domains ask")
f = _domain_run(3405, "Add a GET /test endpoint", answer=["Members"])
check(not calls["asks"] and "belongs to the Members domain" in calls["plan_systems"][0],
      "an earlier human answer decides the domain")
f = _domain_run(3406, "Change the login button colour to red", answer_raises=True)
check(f["domain"]["selected"] == [] and not calls["asks"], "a frontend issue skips the domain decision")
f = _domain_run(3407, "Add GET /announcements/x and GET /members/y")
check(not calls["asks"] and f["domain"]["selected"] == ["Announcements", "Members"]
      and "This issue belongs to the Announcements, Members domains" in calls["code_systems"][0]
      and "MembersController.php (complete)" in calls["plan_prompts"][0]
      and "AnnouncementsController.php (complete)" in calls["plan_prompts"][0],
      "routes in two domains decide both; the prompts carry both domains")

http = _IssueHTTP()
http.add_issue(40, ["nesti", "nesti::in-progress"])
issue_domain.ask(http.client(), 40, ["Announcements", "Members"])
check(http.issues[40]["labels"] == ["nesti", "nesti::pause"] and len(http.notes[40]) == 1
      and http.notes[40][0]["body"].startswith(issue_domain.QUESTION)
      and issue_domain.QUESTION_MARKER in http.notes[40][0]["body"],
      "ask posts one verified question and pauses the issue")
check(issue_domain.reconcile(http.client())["waiting"] == [40], "an unanswered question waits")
http.add_note(40, "> 1. `Announcements`\n\nMembers", author=99)
check(issue_domain.reconcile(http.client())["resumed"] == [40]
      and http.issues[40]["labels"] == ["nesti"] and len(http.notes[40]) == 2,
      "a matching reply resumes the issue without a new note")
http.add_note(40, "Run failed", author=15)
check(issue_domain.answer(http.client().list_notes(40), 15, ["Announcements", "Members"]) == ["Members"],
      "the answer survives a later Nesti note")
http2 = _IssueHTTP()
http2.add_issue(41, ["nesti", "nesti::pause"])
http2.add_note(41, issue_domain.format_question(["Announcements", "Members"]), author=15)
http2.add_note(41, "no idea", author=99)
http2.add_issue(42, ["nesti", "nesti::pause"])
http2.add_note(42, "pausing this manually", author=99)
r = issue_domain.reconcile(http2.client())
check(r["asked"] == [41] and len(http2.notes[41]) == 3 and "previous reply" in http2.notes[41][2]["body"]
      and "nesti::pause" in http2.issues[41]["labels"], "an unmatched reply is asked again once")
check(r["resumed"] == r["waiting"] == r["errors"] == []
      and http2.issues[42]["labels"] == ["nesti", "nesti::pause"] and len(http2.notes[42]) == 1,
      "a manual pause is never lifted or commented")

# ═════ Scenario 35: webservice scaffold, .frontend SPA, starter kit, empty repository ═════
print("\n── Scenario 35: starter kit, layouts and empty-repository start ──")
import starter_kit  # noqa: E402

_VUE_PACKAGE = json.dumps({"dependencies": {"vue": "^3.5.0"}})
# Laravel 13 skeleton files, verbatim.
_L13_USER = """<?php

namespace App\\Models;

// use Illuminate\\Contracts\\Auth\\MustVerifyEmail;
use Database\\Factories\\UserFactory;
use Illuminate\\Database\\Eloquent\\Attributes\\Fillable;
use Illuminate\\Database\\Eloquent\\Attributes\\Hidden;
use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;
use Illuminate\\Foundation\\Auth\\User as Authenticatable;
use Illuminate\\Notifications\\Notifiable;

#[Fillable(['name', 'email', 'password'])]
#[Hidden(['password', 'remember_token'])]
class User extends Authenticatable
{
    /** @use HasFactory<UserFactory> */
    use HasFactory, Notifiable;

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
        ];
    }
}
"""
_L13_SEEDER = """<?php

namespace Database\\Seeders;

use App\\Models\\User;
use Illuminate\\Database\\Console\\Seeds\\WithoutModelEvents;
use Illuminate\\Database\\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        // User::factory(10)->create();

        User::factory()->create([
            'name' => 'Test User',
            'email' => 'test@example.com',
        ]);
    }
}
"""
_L13_PHPUNIT = """<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="vendor/autoload.php"
         colors="true"
>
    <testsuites>
        <testsuite name="Feature">
            <directory>tests/Feature</directory>
        </testsuite>
    </testsuites>
    <php>
        <env name="APP_ENV" value="testing"/>
        <env name="CACHE_STORE" value="array"/>
        <env name="DB_CONNECTION" value="sqlite"/>
        <env name="DB_DATABASE" value=":memory:"/>
        <env name="DB_URL" value=""/>
        <env name="SESSION_DRIVER" value="array"/>
    </php>
</phpunit>
"""
_INSTALL_API_ROUTES = """<?php

use Illuminate\\Http\\Request;
use Illuminate\\Support\\Facades\\Route;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');
"""


def _skeleton(root, require=None, migrations=(), routes=None):
    """A Laravel 13 skeleton app (no sandbox needed) at *root*."""
    _put(root, "artisan")
    _put(root, "composer.json", json.dumps({"require": {"php": "^8.4", **(require or {})}}))
    _put(root, "app/Models/User.php", _L13_USER)
    _put(root, "database/seeders/DatabaseSeeder.php", _L13_SEEDER)
    for name, body in migrations:
        _put(root, f"database/migrations/{name}", body)
    if routes is not None:
        _put(root, "routes/api.php", routes)


def _tree_snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}


def _has_route(text, path):
    return re.search(rf"['\"]/?{path}['\"]", text) is not None


_installs = []


def _fake_starter_install(self, app_path, *, install_api, publish_sanctum, publish_permission):
    _installs.append((install_api, publish_sanctum, publish_permission))
    if install_api:
        _put(app_path, "routes/api.php", _INSTALL_API_ROUTES)
        composer_path = Path(app_path, "composer.json")
        composer = json.loads(composer_path.read_text())
        composer["require"]["laravel/sanctum"] = "^4.0"
        composer_path.write_text(json.dumps(composer))
    return True, "installed"


def _starter(root, backend=".", spa=".frontend"):
    _installs.clear()
    with patch.object(dr.docker, "from_env", return_value=None), \
            patch.object(DockerRunner, "run_starter_install", _fake_starter_install):
        return _gt.tool_starter_kit(root, backend, spa)


_PAT = ("2026_01_01_000000_create_personal_access_tokens_table.php", "<?php\n")
_PERMISSION = ("2026_01_01_000001_create_permission_tables.php", "<?php\n")
_CUSTOM_ROLES = ("2026_01_01_000002_create_roles_and_permissions_tables.php",
                 "<?php\nSchema::create('roles', fn ($t) => $t->id());\n"
                 "Schema::create(\"permissions\", fn ($t) => $t->id());\n")
_EXISTING_ROUTES = ("<?php\n\nuse Illuminate\\Support\\Facades\\Route;\n\n"
                    "Route::get('/health', fn () => ['ok' => true]);\n")

with tempfile.TemporaryDirectory(prefix="nesti-s35-") as s35:
    a, b, c, d, e = (os.path.join(s35, n) for n in "abcde")
    _put(a, "artisan")
    _put(a, ".frontend/package.json", _VUE_PACKAGE)
    _put(b, "artisan")
    _put(b, ".frontend/package.json", json.dumps({"dependencies": {"react": "^19.0.0"}}))
    _put(c, "webservice/artisan")
    _put(c, "webservice/composer.json", "{}")
    _put(c, "frontend/package.json", _VUE_PACKAGE)
    _put(d, "webservice/artisan")
    _put(d, "docs/index.md")
    _put(e, "api/artisan")
    _put(e, "api/composer.json", "{}")
    _put(e, "frontend/package.json", _VUE_PACKAGE)
    check(project_layout.deterministic_layout(Path(a)) == {"backend": ".", "frontend": ".frontend"},
          "root artisan + .frontend Vue SPA → ('.', '.frontend')")
    check(project_layout.deterministic_layout(Path(b)) == {"backend": ".", "frontend": None},
          "root artisan + a .frontend without vue → ('.', None)")
    check(project_layout.deterministic_layout(Path(c)) == {"backend": "webservice", "frontend": "frontend"},
          "webservice/artisan + frontend SPA → ('webservice', 'frontend')")
    check(project_layout.deterministic_layout(Path(d)) is None,
          "webservice/artisan beside an extra docs/ folder is not deterministic")
    _saved = (project_layout.STATE_DIR, project_layout.LAYOUT_FILE)
    project_layout.STATE_DIR = Path(s35, "state")
    project_layout.LAYOUT_FILE = project_layout.STATE_DIR / "layout.json"
    try:
        project_layout.save_layout({"schema": 1, "layout": {"backend": ".", "frontend": None}})
        _root_layout = project_layout.clone_layout(Path(a))
        project_layout.save_layout({"schema": 1, "layout": {"backend": "api", "frontend": None}})
        check(_root_layout == {"backend": ".", "frontend": ".frontend"}
              and project_layout.clone_layout(Path(e)) == {"backend": "api", "frontend": "frontend"},
              "clone_layout fills the starter SPA into a saved layout without a frontend")
    finally:
        project_layout.STATE_DIR, project_layout.LAYOUT_FILE = _saved
    try:
        project_layout.validate_layout(Path(a), {"backend": ".", "frontend": ".frontend"})
        _valid = True
    except project_layout.LayoutError:
        _valid = False
    check(_valid, "validate_layout accepts a saved ('.', '.frontend')")

    g = os.path.join(s35, "gates")
    _put(g, "artisan")
    _put(g, "composer.json", "{}")
    _put(g, "app/Models/User.php", "<?php\n")
    _put(g, ".frontend/package.json", _VUE_PACKAGE)
    _put(g, ".frontend/src/App.vue", "<template/>")
    _gate = lambda files: tool_detect_stack(g, files, ".", ".frontend")["result"]  # noqa: E731
    r = _gate([".frontend/src/views/About.vue"])
    check(r["run_frontend"] and not r["run_phpunit"], "root backend: a .frontend change runs the frontend layers only")
    r = _gate(["app/Models/Post.php"])
    check(r["run_phpunit"] and not r["run_frontend"], "root backend: an app/ change runs PHPUnit only")
    r = _gate([".frontend/src/x.vue", "app/Models/Post.php"])
    check(r["run_phpunit"] and r["run_frontend"], "root backend: both sides run every layer")
    _inv = nodes._repo_inventory(g, {"backend": ".", "frontend": ".frontend"})
    check("- app/Models/: User.php" in _inv and "./app" not in _inv and ".frontend/src/App.vue" in _inv,
          "a root backend's inventory lists app/… and .frontend/src/App.vue")

    for name, files, expected in (
        ("spatie", {"composer.json": json.dumps({"require": {"spatie/laravel-permission": "^6.0"}})}, "spatie"),
        ("custom", {"composer.json": "{}", f"database/migrations/{_CUSTOM_ROLES[0]}": _CUSTOM_ROLES[1]}, "custom"),
        ("none", {"composer.json": "{}"}, "none"),
    ):
        for rel, body in files.items():
            _put(os.path.join(s35, "roles", name), rel, body)
        check(starter_kit.role_schema(Path(s35, "roles", name)) == expected, f"role_schema → {expected}")

    _user = Path(s35, "User.php")
    _user.write_text(_L13_USER)
    check(starter_kit.add_model_traits(_user, starter_kit.MODEL_TRAITS["spatie"]), "add_model_traits changes the skeleton User")
    _traited = _user.read_text()
    check("\nuse Laravel\\Sanctum\\HasApiTokens;\n" in _traited
          and "\nuse Spatie\\Permission\\Traits\\HasRoles;\n" in _traited
          and "    use HasRoles, HasApiTokens, HasFactory, Notifiable;\n" in _traited,
          "both trait imports land and the class uses HasRoles, HasApiTokens, HasFactory, Notifiable")
    check(not starter_kit.add_model_traits(_user, starter_kit.MODEL_TRAITS["spatie"])
          and _user.read_text() == _traited, "add_model_traits is idempotent")
    try:
        starter_kit.model_with_traits("<?php\n\nnamespace App\\Models;\n", starter_kit.MODEL_TRAITS["none"])
        _raised = False
    except ValueError:
        _raised = True
    check(_raised, "a model without class User raises ValueError")
    _seeder = Path(s35, "DatabaseSeeder.php")
    _seeder.write_text(_L13_SEEDER)
    _first = starter_kit.register_seeders(_seeder, ["UserSeeder"])
    _seeded = _seeder.read_text()
    check(_first and _seeded.count("UserSeeder::class") == 1
          and not starter_kit.register_seeders(_seeder, ["UserSeeder"]) and _seeder.read_text() == _seeded,
          "register_seeders inserts one call into the skeleton seeder, then is a no-op")

    # tool_starter_kit: none variant on the bare skeleton (install:api runs in the fake sandbox).
    none_app = os.path.join(s35, "none")
    _skeleton(none_app)
    r = _starter(none_app)
    _routes = Path(none_app, "routes/api.php").read_text()
    check(r["success"] and r["result"]["variant"] == "none" and _installs and _installs[0][0],
          "none variant: install:api runs when Sanctum and routes/api.php are missing")
    check(_has_route(_routes, "login") and _has_route(_routes, "users") and not _has_route(_routes, "roles")
          and "Route::get('/user'" not in _routes,
          "none variant: /login and /users routed, no /roles, install:api's /user stub gone")
    check("use HasApiTokens, HasFactory, Notifiable;" in Path(none_app, "app/Models/User.php").read_text()
          and "UserSeeder::class" in Path(none_app, "database/seeders/DatabaseSeeder.php").read_text(),
          "none variant: User gets HasApiTokens and DatabaseSeeder calls UserSeeder")
    _spa_pkg = json.loads(Path(none_app, ".frontend/package.json").read_text())
    check(Path(none_app, ".frontend/src/views/pages/Users.vue").is_file()
          and not Path(none_app, ".frontend/src/views/pages/Roles.vue").exists()
          and _spa_pkg["devDependencies"]["@playwright/test"] == "1.50.0",
          "none variant: the SPA has Users.vue, no Roles.vue, and pins @playwright/test 1.50.0")

    spatie_app = os.path.join(s35, "spatie")
    _skeleton(spatie_app, {"laravel/sanctum": "^4.0", "spatie/laravel-permission": "^6.0"},
              (_PAT, _PERMISSION), _EXISTING_ROUTES)
    r = _starter(spatie_app)
    _routes = Path(spatie_app, "routes/api.php").read_text()
    check(r["success"] and r["result"]["variant"] == "spatie" and _installs == [],
          "spatie variant with Sanctum, routes and both migrations needs no sandbox")
    check("Route::get('/health', fn () => ['ok' => true]);" in _routes and _has_route(_routes, "roles")
          and "HasRoles" in Path(spatie_app, "app/Models/User.php").read_text()
          and Path(spatie_app, ".frontend/src/views/pages/Roles.vue").is_file(),
          "spatie variant keeps the existing route, adds /roles, HasRoles and Roles.vue")

    custom_app = os.path.join(s35, "custom")
    _skeleton(custom_app, {"laravel/sanctum": "^4.0"}, (_PAT, _CUSTOM_ROLES), _EXISTING_ROUTES)
    r = _starter(custom_app)
    check(r["success"] and r["result"]["variant"] == "custom"
          and _has_route(Path(custom_app, "routes/api.php").read_text(), "roles")
          and Path(custom_app, ".frontend/src/views/pages/Roles.vue").is_file(),
          "custom variant routes /roles and adds Roles.vue")

    clash_app = os.path.join(s35, "clash")
    _skeleton(clash_app)
    _put(clash_app, "app/Http/Controllers/Api/AuthController.php", "<?php\n// mine\n")
    _before = _tree_snapshot(clash_app)
    r = _starter(clash_app)
    check(not r["success"] and "AuthController.php" in r["error"] and _tree_snapshot(clash_app) == _before,
          "an existing starter contract file fails before any file or SPA is written")

    kept_app = os.path.join(s35, "kept")
    _skeleton(kept_app)
    _put(kept_app, "database/seeders/UserSeeder.php", "<?php\n// custom demo users\n")
    r = _starter(kept_app)
    check(r["success"]
          and Path(kept_app, "database/seeders/UserSeeder.php").read_text() == "<?php\n// custom demo users\n"
          and Path(kept_app, "database/seeders/DatabaseSeeder.php").read_text() == _L13_SEEDER,
          "an existing UserSeeder is kept byte-identical and DatabaseSeeder stays unchanged")
    check(not _starter(kept_app)["success"], "an existing SPA folder refuses the starter kit")

    pg = os.path.join(s35, "pg")
    _put(pg, ".env.example", "APP_NAME=Laravel\nDB_CONNECTION=pgsql\nDB_HOST=127.0.0.1\nDB_DATABASE=alt\n")
    _put(pg, "phpunit.xml", _L13_PHPUNIT)
    check(_gt._align_phpunit_database(Path(pg)) == "alt_test"
          and dr._pgsql_settings(pg)["DB_DATABASE"] == "alt_test",
          "a pgsql app's phpunit.xml runs on <DB_DATABASE>_test")
    my = os.path.join(s35, "mysql")
    _put(my, ".env.example", "DB_CONNECTION=mysql\nDB_DATABASE=alt\n")
    _put(my, "phpunit.xml", _L13_PHPUNIT)
    check(_gt._align_phpunit_database(Path(my)) == "" and Path(my, "phpunit.xml").read_text() == _L13_PHPUNIT
          and dr._pgsql_settings(my) is None, "a mysql app's phpunit.xml stays byte-identical")
    already = os.path.join(s35, "already")
    _put(already, ".env.example", "DB_CONNECTION=pgsql\nDB_DATABASE=alt\n")
    _put(already, "phpunit.xml", _PG_XML)
    check(_gt._align_phpunit_database(Path(already)) == "" and Path(already, "phpunit.xml").read_text() == _PG_XML,
          "a phpunit.xml already on pgsql is left alone")

    topup = os.path.join(s35, "topup")
    _skeleton(topup)
    _put(topup, "vite.config.js", "import laravel from 'laravel-vite-plugin';\n")
    with patch.object(dr.docker, "from_env", return_value=None), \
            patch.object(DockerRunner, "run_scramble_install", lambda self, path: (True, "")):
        r = tool_laravel_bootstrap(topup)
    check(r["success"] and not Path(topup, "vitest.config.js").exists()
          and Path(topup, "tests/Feature/OpenApiDocumentationTest.php").is_file(),
          "top-up of a root app succeeds and writes no SPA test config into it")

    from gitlab_client import GitLabClient  # noqa: E402
    _bare = _git.Repo.init(Path(s35, "origin.git"), bare=True)
    with patch.dict(os.environ, {"GITLAB_URL": "https://gitlab.test", "GITLAB_TOKEN": "t",
                                 "GITLAB_USE_SSH": "true", "GITLAB_REPO_SSH": str(Path(s35, "origin.git")),
                                 "GITLAB_DEFAULT_BRANCH": "main"}):
        _first_clone = GitLabClient().clone(str(Path(s35, "first")))
        check(_first_clone.active_branch.name == "main" and len(list(_bare.iter_commits("main"))) == 1,
              "an empty repository gets one empty commit on main and the clone sits on main")
        GitLabClient().clone(str(Path(s35, "second")))
        check(len(list(_bare.iter_commits("main"))) == 1, "cloning a non-empty repository adds no commit")

# ═════ G0b: token-less git, redaction, verified push, existing remote branch ═════
print("\n── G0b: token-less git, redaction, verified push, existing remote branch ──")
import base64  # noqa: E402
import gitlab_client  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

_G0B_TOKEN = "glpat-G0bSecretToken"


def _g0b_env(root, ssh):
    """HTTPS mode clones file://<root>/acme/shop.git; SSH mode clones the same bare path directly."""
    return {"GITLAB_URL": f"file://{root}", "GITLAB_TOKEN": _G0B_TOKEN, "GITLAB_PROJECT_PATH": "acme/shop",
            "GITLAB_USE_SSH": str(ssh).lower(), "GITLAB_REPO_SSH": str(Path(root, "acme", "shop.git")),
            "GITLAB_DEFAULT_BRANCH": "main"}


def _g0b_setup(root):
    """An empty bare origin, cloned by GitLabClient (initial commit pushed), on an issue branch."""
    bare = _git.Repo.init(Path(root, "acme", "shop.git"), bare=True, mkdir=True)
    client = gitlab_client.GitLabClient()
    repo = client.clone(str(Path(root, "clone")))
    return bare, client, repo, client.create_branch(repo, 7, "Add thing")


def _g0b_sha(bare, branch):
    return bare.git.for_each_ref("--format=%(objectname)", f"refs/heads/{branch}")


def _g0b_leftover(repo, branch):
    """Push an earlier run's commit to *branch*, then reset the clone back to main."""
    Path(repo.working_tree_dir, "old.txt").write_text("old run")
    repo.git.add(A=True)
    repo.git.commit("-m", "leftover")
    repo.git.push("origin", f"{branch}:{branch}")
    sha = repo.head.commit.hexsha
    repo.git.reset("--hard", "main")
    return sha


def _g0b_mrs(items):
    """A requests.Session.get stand-in answering the open-MR lookup with *items*."""
    response = MagicMock()
    response.json.return_value = items
    return MagicMock(return_value=response)


# G0b item 1 (+ Y6): HTTPS mode keeps the token out of .git/config.
with tempfile.TemporaryDirectory(prefix="nesti-g0b-") as _root, \
        patch.dict(os.environ, {**_g0b_env(_root, ssh=False),
                                "NESTI_GIT_AUTHOR_NAME": "", "NESTI_GIT_AUTHOR_EMAIL": ""}):
    _bare, _client, _repo, _branch = _g0b_setup(_root)
    check(len(list(_bare.iter_commits("main"))) == 1,
          "HTTPS mode: an empty repository still gets its initial commit on main")
    Path(_repo.working_tree_dir, "thing.txt").write_text("thing")
    check(_client.commit_and_push(_repo, _branch, "feat: thing")
          and _g0b_sha(_bare, _branch) == _repo.head.commit.hexsha, "HTTPS mode: the issue branch is pushed")
    check(_repo.remote("origin").url == f"file://{_root}/acme/shop.git"
          and _G0B_TOKEN not in Path(_repo.git_dir, "config").read_text(),
          "HTTPS mode: the remote URL is token-less and .git/config holds no token after clone + push")
    _cfg = _repo.config_reader()
    check((_cfg.get_value("user", "name"), _cfg.get_value("user", "email"))
          == ("AI Developer", "nesti@yourdomain.com"),
          "empty NESTI_GIT_AUTHOR_NAME/EMAIL fall back to AI Developer <nesti@yourdomain.com>")

# G0b item 2: the auth header goes through the per-call environment; git error text is redacted.
import git_auth  # noqa: E402
with patch.dict(os.environ, {"GITLAB_URL": "https://gitlab.test", "GITLAB_TOKEN": _G0B_TOKEN,
                             "GITLAB_USE_SSH": "false"}):
    _gl = gitlab_client.GitLabClient()
_basic = base64.b64encode(f"oauth2:{_G0B_TOKEN}".encode()).decode()
_header = f"Authorization: Basic {_basic}"
check(_gl._git_env == git_auth.env("https://gitlab.test/", _header),
      "GitLab sends install.sh's header (Basic base64(oauth2:<token>)), scoped to the GitLab URL")
check(_git.Git().config("--get-urlmatch", "http.extraHeader", "https://gitlab.test/acme/shop.git",
                        env=_gl._git_env) == _header, "git_auth.env reaches git for the forge URL")
try:
    _git.Git().config("--get-urlmatch", "http.extraHeader", "https://other.test/acme/shop.git", env=_gl._git_env)
    _leaks = True
except _git.GitCommandError:
    _leaks = False
check(not _leaks, "the auth header is never configured for another host")
_masked = git_auth.redact(f"error 1 of 1: 'https://oauth2:{_G0B_TOKEN}@gitlab.test/a.git' '{_header}' "
                          f"{_basic} {_G0B_TOKEN}", *_gl._git_secrets)
check("1" in _basic and _masked == "error 1 of 1: 'https://***@gitlab.test/a.git' '***' *** ***",
      "redact masks URL userinfo, the whole header, the credential and the token; other text stays intact")

# G0b item 3: a rejected push raises instead of logging "Pushed".
with tempfile.TemporaryDirectory(prefix="nesti-g0b-") as _root, \
        patch.dict(os.environ, _g0b_env(_root, ssh=True)):
    _bare, _client, _repo, _branch = _g0b_setup(_root)
    _hook = Path(_bare.git_dir, "hooks", "pre-receive")
    _hook.write_text("#!/bin/sh\nexit 1\n")
    _hook.chmod(0o755)
    Path(_repo.working_tree_dir, "thing.txt").write_text("thing")
    try:
        _client.commit_and_push(_repo, _branch, "feat: thing")
        _raised = False
    except RuntimeError:
        _raised = True
    check(_raised and not _g0b_sha(_bare, _branch), "a push the remote rejects raises")

# G0b item 4a: a leftover remote branch without an open MR is overwritten (leased).
with tempfile.TemporaryDirectory(prefix="nesti-g0b-") as _root, \
        patch.dict(os.environ, {**_g0b_env(_root, ssh=True), "NESTI_GIT_AUTHOR_NAME": "Nesti Bot",
                                "NESTI_GIT_AUTHOR_EMAIL": "bot@example.invalid"}):
    _bare, _client, _repo, _branch = _g0b_setup(_root)
    _old = _g0b_leftover(_repo, _branch)
    Path(_repo.working_tree_dir, "thing.txt").write_text("thing")
    with patch("requests.Session.get", _g0b_mrs([])):
        _client.commit_and_push(_repo, _branch, "feat: thing")
    check(_g0b_sha(_bare, _branch) == _repo.head.commit.hexsha != _old,
          "a leftover remote branch without an open MR is overwritten")
    _author = _bare.commit(_g0b_sha(_bare, _branch)).author
    check((_author.name, _author.email) == ("Nesti Bot", "bot@example.invalid"),
          "NESTI_GIT_AUTHOR_NAME/EMAIL author the pushed commit")

# G0b item 4a': an open MR listed without its link fails closed (no force push).
with tempfile.TemporaryDirectory(prefix="nesti-g0b-") as _root, \
        patch.dict(os.environ, _g0b_env(_root, ssh=True)):
    _bare, _client, _repo, _branch = _g0b_setup(_root)
    _old = _g0b_leftover(_repo, _branch)
    for _n, _mr in enumerate(({"iid": 7}, {"iid": 7, "web_url": None}, {"iid": 7, "web_url": ""})):
        Path(_repo.working_tree_dir, f"thing{_n}.txt").write_text("thing")
        try:
            with patch("requests.Session.get", _g0b_mrs([_mr])):
                _client.commit_and_push(_repo, _branch, "feat: thing")
            _raised = False
        except RuntimeError:
            _raised = True
        check(_raised and _g0b_sha(_bare, _branch) == _old, f"an open MR {_mr} without a web_url stops the push")

# G0b item 4b: an open MR on the branch stops the run before push; the note links it.
with tempfile.TemporaryDirectory(prefix="nesti-g0b-") as _root, \
        patch.dict(os.environ, _g0b_env(_root, ssh=True)):
    _bare, _client, _repo, _branch = _g0b_setup(_root)
    _old = _g0b_leftover(_repo, _branch)
    Path(_repo.working_tree_dir, "thing.txt").write_text("thing")
    _url = "https://gitlab.test/acme/shop/-/merge_requests/7"
    _notes, _opened, _get = [], [], _g0b_mrs([{"web_url": _url}])
    with patch("requests.Session.get", _get), \
            patch.object(nodes, "tool_gitlab_commit_and_push", _gt.tool_gitlab_commit_and_push), \
            patch.object(nodes, "tool_gitlab_open_mr",
                         lambda **kw: _opened.append(kw) or {"success": False, "error": "unexpected"}), \
            patch.object(nodes, "tool_issue_set_status",
                         lambda issue_id, status, note="": _notes.append((status, note)) or {"success": True}):
        nodes.node_commit({"issue_id": 7, "subject": "Add thing", "repo_path": _repo.working_tree_dir,
                           "branch_name": _branch, "base_sha": _repo.heads.main.commit.hexsha,
                           "issue": {"subject": "Add thing", "description": "d"}, "run_id": "g0b"})
    check(_g0b_sha(_bare, _branch) == _old and not _opened, "an open MR on the branch: nothing pushed, no MR opened")
    check(len(_notes) == 1 and _notes[0][0] == "new" and _url in _notes[0][1]
          and "NESTI_FAILED_RUN_V1" in _notes[0][1],
          "the reopen note links the open MR and carries the failed-run marker")
    check(_get.call_args.kwargs["params"] == {"source_branch": _branch, "state": "opened"},
          "the open-MR lookup asks GitLab for open MRs from the issue branch")


def _git_clone(setup):
    """A fake clone: *setup* writes the tree, then one initial commit (empty for greenfield)."""
    def clone(target_path):
        os.makedirs(target_path, exist_ok=True)
        calls["workspaces"].append(os.path.dirname(target_path))
        setup(target_path)
        with _git.Repo.init(target_path) as repo:
            repo.git.add(A=True)
            head = repo.index.commit("Initial commit").hexsha
        return {"success": True, "result": {"repo_path": target_path, "head_sha": head}}
    return clone


def _scaffold_bootstrap(repo_path, spa_path=""):
    calls["bootstrap"].append(repo_path)
    created = not os.path.isfile(os.path.join(repo_path, "artisan"))
    if created:
        for rel, body in (("artisan", ""), ("composer.json", "{}"), ("routes/api.php", "<?php\n"),
                          ("app/Models/User.php", "<?php\n")):
            _put(repo_path, rel, body)
    return {"success": True, "result": {"created": created, "mode": "scaffold" if created else "top-up",
                                        "reason": "scaffolded" if created else "already fully wired",
                                        "output": ""}}


def _starter_run(n, description, setup, code, bootstrap=_scaffold_bootstrap, **kw):
    """A graph run on a git-initialised clone; returns (final, clone, commits seen at push)."""
    reset_calls(n)
    patch_tools(docker_outcomes=[True], code_responses=[code], layout=None, **kw)
    nodes.tool_gitlab_clone = _git_clone(setup)
    nodes.tool_laravel_bootstrap = bootstrap
    commits, push = [], nodes.tool_gitlab_commit_and_push

    def counting_push(repo_path, branch_name, message):
        with _git.Repo(repo_path) as repo:
            commits.append(len(list(repo.iter_commits())))
        return push(repo_path, branch_name, message)
    nodes.tool_gitlab_commit_and_push = counting_push
    final = compiled.invoke(initial(n, "Add an About page", description), config={"recursion_limit": 60})
    return final, os.path.join(calls["workspaces"][0], "repo"), commits


_ABOUT = ("### FILE: {spa}/src/views/About.vue\n```vue\n<template><h1>About</h1></template>\n```\n\n"
          "### FILE: {spa}/e2e/about.spec.js\n```js\n// playwright\n```\n")
_root_laravel = lambda root: (_put(root, "artisan"), _put(root, "composer.json", "{}"))  # noqa: E731

f, _clone, _commits = _starter_run(3501, "Scope: frontend\n\nShow an About page.", lambda root: None,
                                   _ABOUT.format(spa="frontend"))
_paths = dict(calls["layer_paths"])
check(calls["bootstrap"] == [os.path.join(_clone, "webservice")]
      and calls["starter"] == [(_clone, "webservice", "frontend")],
      "greenfield frontend issue: webservice/ scaffold, then the starter kit in frontend/")
check(f["layout"] == {"backend": "webservice", "frontend": "frontend"}
      and {"webservice/artisan", "webservice/routes/api.php", "frontend/src/App.vue"} <= set(f["bootstrap_files"]),
      "greenfield frontend issue: final layout and the committed bootstrap files")
check(_commits == [2], "the clone holds the initial and the bootstrap commit before commit_and_push")
check(_paths.get("docker") == os.path.join(_clone, "webservice")
      and _paths.get("vitest") == _paths.get("playwright") == os.path.join(_clone, "frontend")
      and f["mr_url"], "PHPUnit runs in webservice/, Vitest + Playwright in frontend/, and the MR opens")

f, _clone, _commits = _starter_run(
    3502, "Scope: backend\n\nAdd GET /api/health.", lambda root: None,
    "### FILE: webservice/app/Http/Controllers/HealthController.php\n```php\n<?php\n```\n")
check(not calls["starter"] and f["layout"] == {"backend": "webservice", "frontend": None}
      and calls["vitest"] == 0 and f["mr_url"],
      "greenfield backend issue: no starter kit, no SPA, no Vitest")

f, _clone, _commits = _starter_run(3503, "Scope: frontend\n\nShow an About page.", _root_laravel,
                                   _ABOUT.format(spa=".frontend"))
check(calls["starter"] == [(_clone, ".", ".frontend")] and f["layout"] == {"backend": ".", "frontend": ".frontend"},
      "root Laravel app + frontend issue: the starter kit goes into .frontend/")

f, _clone, _commits = _starter_run(
    3504, "Scope: backend\n\nAdd GET /api/health.", _root_laravel,
    "### FILE: app/Http/Controllers/HealthController.php\n```php\n<?php\n```\n")
check(f["bootstrap_files"] == [] and _commits == [1], "a top-up that changes nothing makes no bootstrap commit")


def _topup_bootstrap(repo_path, spa_path=""):
    """Top-up of an existing app + SPA: wires test harness files into both sides."""
    _put(spa_path, "vitest.config.js", "// nesti\n")
    _put(repo_path, "tests/Feature/OpenApiDocumentationTest.php", "<?php\n")
    return {"success": True, "result": {"created": False, "mode": "top-up",
                                        "reason": "topped up", "output": ""}}


_app_and_spa = lambda root: (_root_laravel(root), _put(root, ".frontend/package.json",  # noqa: E731
                                                       json.dumps({"dependencies": {"vue": "^3.5.0"}})))
f, _clone, _commits = _starter_run(
    3506, "Scope: backend\n\nAdd GET /api/health.", _app_and_spa,
    "### FILE: app/Http/Controllers/HealthController.php\n```php\n<?php\n```\n", bootstrap=_topup_bootstrap)
check(_commits == [2] and f["bootstrap_files"] == [] and f["run_phpunit"] is True
      and f["run_frontend"] is False and calls["vitest"] == calls["playwright"] == 0 and f["mr_url"],
      "top-up SPA test config is committed but a backend-only change runs no Vitest/Playwright")
f, _clone, _commits = _starter_run(3507, "Scope: frontend\n\nShow an About page.", _app_and_spa,
                                   _ABOUT.format(spa=".frontend"), bootstrap=_topup_bootstrap)
check(_commits == [2] and f["run_phpunit"] is False and f["run_frontend"] is True
      and calls["docker"] == 0 and calls["vitest"] == calls["playwright"] == 1 and f["mr_url"],
      "top-up backend test file is committed but a frontend-only change runs no PHPUnit")

# Rule 31: a Laravel app that serves its own frontend is refused, never processed.
with tempfile.TemporaryDirectory(prefix="nesti-website-") as _web:
    def _website(name, files):
        for rel, body in files.items():
            _put(os.path.join(_web, name), rel, body)
        return Path(_web, name)

    def _refused(call):
        try:
            call()
        except project_layout.LayoutError as exc:
            return project_layout.UNSUPPORTED_WEBSITE in str(exc)
        return False

    _vue_site = _website("vue", {"artisan": "", "composer.json": "{}",
                                 "vite.config.js": "import vue from '@vitejs/plugin-vue';\n"})
    check(_refused(lambda: project_layout.deterministic_layout(_vue_site)),
          "a root Laravel app whose Vite build uses @vitejs/plugin-vue is refused")
    _livewire = _website("livewire", {"artisan": "", "composer.json": json.dumps(
        {"require": {"livewire/livewire": "^3.0"}})})
    check(_refused(lambda: project_layout.deterministic_layout(_livewire)),
          "a root Laravel app requiring livewire/livewire is refused")
    check(_refused(lambda: project_layout.validate_layout(_vue_site, {"backend": ".", "frontend": None})),
          "validate_layout refuses a saved record whose root app serves its own frontend")
    _inertia = _website("inertia", {"backend/artisan": "", "backend/composer.json": json.dumps(
        {"require": {"inertiajs/inertia-laravel": "^2.0"}})})
    check(_refused(lambda: project_layout.validate_layout(_inertia, {"backend": "backend", "frontend": None})),
          "validate_layout refuses an Inertia backend folder")
    _skeleton_site = _website("skeleton", {"artisan": "", "composer.json": "{}", "vite.config.js": (
        "import laravel from 'laravel-vite-plugin';\nimport tailwindcss from '@tailwindcss/vite';\n")})
    check(project_layout.deterministic_layout(_skeleton_site) == {"backend": ".", "frontend": None},
          "the Laravel skeleton's vite.config.js (laravel-vite-plugin + tailwind) is API-only")

reset_calls(3505)
patch_tools(docker_outcomes=[True], code_responses=[VUE_CODE], layout=None, laravel_repo=True)
_api_clone = nodes.tool_gitlab_clone


def _website_clone(target_path):
    result = _api_clone(target_path)
    _put(target_path, "vite.config.js", "import vue from '@vitejs/plugin-vue';\n")
    return result


nodes.tool_gitlab_clone = _website_clone
_layout_error = ""
try:
    compiled.invoke(initial(3505), config={"recursion_limit": 60})
except RuntimeError as exc:
    _layout_error = str(exc)
check(_layout_error.startswith("Project layout:") and "not supported" in _layout_error
      and calls["bootstrap"] == [] and not any(os.path.exists(w) for w in calls["workspaces"]),
      "a clone that serves its own frontend fails before bootstrap and leaves no workspace")

# ═════ Scenario 13: TaskEngine thin wrapper ═════
print("\n── Scenario 13: TaskEngine.run_once() ──")
import task_engine  # noqa: E402
reset_calls(111)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
task_engine.tool_issue_list_pending = lambda: {
    "success": True,
    "result": [{"id": 111, "subject": "Wrapper test", "description": "d"}]}
task_engine.tool_issue_set_status = nodes.tool_issue_set_status
task_engine.tool_issue_reconcile_domain_questions = lambda: {
    "success": True, "result": {"resumed": [], "asked": [], "waiting": [], "errors": []}}
engine = task_engine.TaskEngine()
check(engine.run_once() is True, "run_once returns True when MR opened")
check(calls["docker"] == 1, "graph executed via wrapper")
task_engine.tool_issue_list_pending = lambda: {"success": True, "result": []}
check(engine.run_once() is False, "run_once returns False when no pending issues")

# ═════ Duplicate-poller warning (heartbeat in a GitLab CI/CD variable) ═════
print("\n── Duplicate-poller heartbeat ──")
from unittest.mock import MagicMock  # noqa: E402
_slot: dict = {"value": None}


def _swap(value):
    previous, _slot["value"] = _slot["value"], value
    return {"success": True, "result": {"previous": previous}}


_alerts: list = []
_clock = [1000.0]
_real_swap, _real_notify = task_engine.tool_issue_swap_poll_heartbeat, task_engine.telegram_notify
task_engine.tool_issue_swap_poll_heartbeat = _swap
task_engine.telegram_notify = _alerts.append


def _poll(engine, step=30.0):
    _clock[0] += step
    with patch("task_engine.time.time", return_value=_clock[0]):
        return engine.run_once()


try:
    _a, _b = task_engine.TaskEngine(poll_interval=60), task_engine.TaskEngine(poll_interval=60)
    for _engine in (_a, _b, _a):
        _poll(_engine)
    check(_alerts == [], "a first foreign heartbeat (possibly a restarted predecessor) is not alerted")
    _poll(_b)
    check(len(_alerts) == 1 and "Multiple Nesti instances are running for the same project "
          "gitlab.test/ai/hello-world" in _alerts[0],
          "the second consecutive foreign heartbeat within one poll interval alerts")
    _poll(_a)
    _poll(_b)
    check(len(_alerts) == 2, "each poller alerts once per streak, not on every poll")
    _slot["value"] = json.dumps({"instance": _a._instance, "t": _clock[0]})
    _c = task_engine.TaskEngine(poll_interval=60)
    _poll(_c, 20)
    _poll(_c, 60)
    check(len(_alerts) == 2, "a restarted instance seeing its predecessor once, then itself, stays quiet")
    _d = task_engine.TaskEngine(poll_interval=60)
    for _ in range(2):
        _slot["value"] = json.dumps({"instance": "other-host", "t": _clock[0]})
        _poll(_d, 61)
    check(len(_alerts) == 2, "a heartbeat older than the poll interval is not a live poller")

    task_engine.tool_issue_swap_poll_heartbeat = lambda value: {"success": False, "error": "403"}
    _e = task_engine.TaskEngine(poll_interval=60)
    with patch("task_engine.logger") as _log:
        _results = [_e.run_once(), _e.run_once()]
    _heartbeat_warnings = [c for c in _log.warning.call_args_list
                           if str(c.args[0]).startswith("Poll heartbeat unavailable")]
    check(_results == [False, False] and len(_heartbeat_warnings) == 1,
          "an unavailable heartbeat warns once and never blocks polling")

    def _must_not_swap(value):
        raise AssertionError("single run swapped the heartbeat")
    task_engine.tool_issue_swap_poll_heartbeat = _must_not_swap
    check(task_engine.TaskEngine().run_once() is False,
          "a single run (poll_interval 0) never touches the heartbeat")
finally:
    task_engine.tool_issue_swap_poll_heartbeat = _real_swap
    task_engine.telegram_notify = _real_notify

_hb = gic.GitLabIssuesClient()
_hb.session = MagicMock()
_hb.session.get.return_value.status_code = 404
_first = _hb.swap_poll_heartbeat("x")
check(_first is None and not _hb.session.put.called
      and _hb.session.post.call_args.kwargs["json"]["key"] == "NESTI_POLL_HEARTBEAT"
      and _hb.session.post.call_args.kwargs["json"]["value"] == "x",
      "a missing heartbeat variable is created and reports no previous poller")
_hb.session.get.return_value.status_code = 200
_hb.session.get.return_value.json.return_value = {"value": "x"}
check(_hb.swap_poll_heartbeat("y") == "x"
      and _hb.session.put.call_args.kwargs["json"] == {"value": "y"}
      and _hb.session.post.call_count == 1,
      "an existing heartbeat is overwritten and its previous value returned")

# ═════ MCP: each client connection acts on its own GitLab project ═════
print("\n── MCP client project binding ──")
import forge  # noqa: E402
import gitlab_client  # noqa: E402
import graph.tools as _bind_tools  # noqa: E402

_remotes = {
    "https://gitlab.com/acme/shop.git": "acme/shop",
    "https://oauth2:SECRET@gitlab.com/acme/shop": "acme/shop",
    "git@gitlab.com:group/sub/proj.git": "group/sub/proj",
    "ssh://git@gitlab.com:2222/group/proj.git": "group/proj",
}
check(all(forge.project_from_remote(r, "https://gitlab.com") == p
          for r, p in _remotes.items())
      and forge.project_from_remote(
          "https://example.com/gitlab/g/p.git", "https://example.com/gitlab") == "g/p",
      "https, credentialed, scp, ssh-with-port and sub-path remotes resolve to namespace/project")
_bad = []
for _remote in ("", "https://gitlab.com/shop", "https://u:SECRET@github.com/x/y.git"):
    try:
        forge.project_from_remote(_remote, "https://gitlab.com")
    except ValueError as exc:
        _bad.append(str(exc))
check(len(_bad) == 3 and "github.com" in _bad[2] and not any("SECRET" in m for m in _bad),
      "empty, namespace-less and foreign-host remotes are refused without echoing credentials")
try:
    forge.bind_client("git@gitlab.test:Group/Proj.git")
    check(forge.path() == "Group/Proj"
          and forge.identity() == "gitlab.test/group/proj"
          and gic.GitLabIssuesClient().project_path == "Group/Proj",
          "a bound client acts on its remote's project, not GITLAB_PROJECT_PATH")
    with patch("forge.requests.get") as _get:
        _get.return_value.json.return_value = {"default_branch": "develop"}
        check(gitlab_client.GitLabClient().default_branch == "develop",
              "a bound client targets its project's GitLab default branch")
    with patch("project_layout.load_layout",
               return_value={"gitlab_project": "gitlab.test/other/proj"}):
        _layout = _bind_tools.tool_project_layout()
    with patch("project_layout.load_layout",
               return_value={"gitlab_project": "gitlab.test/group/proj"}):
        _own = _bind_tools.tool_project_layout()
    check(not _layout["success"] and "gitlab.test/other/proj" in _layout["error"]
          and "gitlab.test/group/proj" in _layout["error"] and _own["success"],
          "project_layout serves only the layout recorded for the client's project")
    forge.bind_client("")
    _refused = _bind_tools.tool_issue_list_pending()
    check(not _refused["success"] and "nesti mcp" in _refused["error"],
          "a client without a resolvable project is refused, never served .env's project")
    _globbed = []
    for _remote in ("https://gitlab.test/acme/*", "git@gitlab.test:acme/[ab].git"):
        forge.bind_client(_remote)
        with patch("graph.tools.get_semantic_memory") as _memory:
            _globbed.append((_bind_tools.tool_memory_forget_episodes(1, "r")["success"],
                             _memory.called))
    check(_globbed == [(False, False), (False, False)],
          "a wildcard remote is refused before Redis, so it cannot delete other projects' episodes")
finally:
    forge._bound = None

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

print("\n── Output token configuration ──")
import subprocess
import sys

token_config = subprocess.run(
    [sys.executable, "-c",
     "import json, llm_client; print(json.dumps(llm_client._DEFAULT_MAX_TOKENS))"],
    env={**os.environ, "DEFAULT_MAX_TOKENS": "16000"},
    capture_output=True, text=True, check=True,
)
check(json.loads(token_config.stdout) == 16000,
      "configured output tokens are a JSON number, not a rejected API string")

print("\n── Ponytail level ──")
_ponytail_probe = ("import prompt_builder as p; print(all(f'Use {p._PONYTAIL_LEVEL.upper()} for both'"
                   " in f('fullstack', '', {'backend': '.', 'frontend': None})"
                   " for f in (p._planning_system_prompt, p._coding_system_prompt)), p._PONYTAIL_LEVEL)")
for _value, _level in ((None, "ultra"), ("", "ultra"), ("lite", "lite"), (" FULL ", "full"), ("ultra", "ultra")):
    _env = {k: v for k, v in os.environ.items() if k != "NESTI_PONYTAIL_LEVEL"}
    if _value is not None:
        _env["NESTI_PONYTAIL_LEVEL"] = _value
    _run = subprocess.run([sys.executable, "-c", _ponytail_probe], env=_env,
                          capture_output=True, text=True)
    check(_run.stdout.split() == ["True", _level],
          f"NESTI_PONYTAIL_LEVEL={_value!r} puts {_level.upper()} into the plan and code prompts")
_run = subprocess.run([sys.executable, "-c", "import prompt_builder"],
                      env={**os.environ, "NESTI_PONYTAIL_LEVEL": "bogus"}, capture_output=True, text=True)
check(_run.returncode != 0 and "Invalid NESTI_PONYTAIL_LEVEL" in _run.stderr,
      "invalid NESTI_PONYTAIL_LEVEL fails the prompt_builder import")

print(f"\nALL {passed_checks} CHECKS PASSED ✅")
