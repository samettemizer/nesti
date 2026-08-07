"""
test_graph_smoke.py – verifies the LangGraph pipeline against the acceptance
checklists of Phase 2 (core loop) and Phase 4 (layered frontend testing), with
all external services (Redmine, GitLab, Docker, LLM providers) monkeypatched
at the node/tool seam.

``tool_detect_stack`` is deliberately NOT patched: the fake clone is a real
temporary directory and the fake coder writes real files into it, so stack
detection is exercised for real against each scenario's file tree.

Run:  python test_graph_smoke.py
"""

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
    route_after_vitest, route_after_playwright,
)
from graph.tools import tool_detect_stack        # noqa: E402

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
GOOD_CODE = PHP_CODE          # Phase 2 scenarios stay backend-only
NO_BLOCKS = "Here is a prose description of the change instead of files."

calls: dict = {}


def reset_calls(issue_id: int) -> None:
    calls.clear()
    calls.update({
        "issue_id": issue_id, "redmine": [], "docker": 0, "escalate": 0,
        "vitest": 0, "playwright": 0,
        "pushes": [], "mrs": [], "history_at_commit": None, "workspaces": [],
    })


def initial(issue_id: int) -> dict:
    return {
        "issue": {"id": issue_id, "subject": f"Test issue {issue_id}",
                  "description": "Implement the thing."},
        "issue_id": issue_id, "subject": f"Test issue {issue_id}",
        "skills": [], "plan": "", "code_response": "", "repo_path": "",
        "branch_name": "", "workspace": "", "messages": [],
        "attempt": 0, "max_attempts": 3, "files_written": False,
        "has_vue_files": False, "stack": "php", "run_phpunit": True,
        "test_output": "", "test_passed": False,
        "vitest_passed": False, "vitest_output": "",
        "playwright_passed": False, "playwright_output": "",
        "mr_url": "", "failure_reason": "", "error": "",
    }


def patch_tools(docker_outcomes, code_responses, plan_exc=None, code_exc_first=False,
                vitest_outcomes=(True,), playwright_outcomes=(True,)):
    """Install fakes on graph.nodes (node functions resolve names at call time)."""

    def fake_set_status(issue_id, status, note=""):
        calls["redmine"].append((issue_id, status, note))
        return {"success": True, "result": {"issue_id": issue_id, "status": status}}
    nodes.tool_redmine_set_status = fake_set_status

    def fake_clone(target_path):
        os.makedirs(target_path, exist_ok=True)
        calls["workspaces"].append(os.path.dirname(target_path))
        return {"success": True, "result": {"repo_path": target_path}}
    nodes.tool_gitlab_clone = fake_clone

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

    def _layered(key, outcomes, pass_out, fail_out):
        def fake(workspace_path):
            calls[key] += 1
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
statuses = [(s, n) for _, s, n in calls["redmine"]]
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
reopen = [(s, n) for _, s, n in calls["redmine"] if s == "new"]
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
reopen = [(s, n) for _, s, n in calls["redmine"] if s == "new"]
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
reopen = [(s, n) for _, s, n in calls["redmine"] if s == "new"]
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
reopen = [(s, n) for _, s, n in calls["redmine"] if s == "new"]
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
reopen = [(s, n) for _, s, n in calls["redmine"] if s == "new"]
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

# ═════ Scenario 12: nodes/edges testable in isolation (total=False state) ═════
print("\n── Scenario 12: isolated node/edge tests with partial state ──")
r = nodes.node_test({})   # empty state – every field optional
check(r == {"test_passed": False,
            "test_output": nodes._NO_FILE_BLOCKS_OUTPUT}, "node_test runs on empty state")
check(nodes.node_detect_stack({}) ==
      {"has_vue_files": False, "stack": "unknown", "run_phpunit": True},
      "node_detect_stack defers to the files_written guard on empty state")
check(route_after_detect_stack({"run_phpunit": True}) == "phpunit_test",
      "edge: php-bearing stack → phpunit_test")
check(route_after_detect_stack({"run_phpunit": False, "stack": "vue"}) == "vitest_test",
      "edge: vue stack → vitest_test (PHPUnit bypassed)")
check(route_after_detect_stack({}) == "phpunit_test", "edge: default → phpunit_test")
check(route_after_phpunit({"test_passed": True}) == "commit", "edge: pass, no vue → commit")
check(route_after_phpunit({"test_passed": True, "has_vue_files": True}) == "vitest_test",
      "edge: pass + vue → vitest_test")
check(route_after_phpunit({"test_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_test_failure", "edge: fail + retries → on_test_failure")
check(route_after_phpunit({"test_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: fail + exhausted → failure")
check(route_after_vitest({"vitest_passed": True}) == "playwright_test",
      "edge: vitest pass → playwright_test")
check(route_after_vitest({"vitest_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_frontend_test_failure", "edge: vitest fail + retries → escalation")
check(route_after_vitest({"vitest_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: vitest fail + exhausted → failure")
check(route_after_playwright({"playwright_passed": True}) == "commit",
      "edge: playwright pass → commit")
check(route_after_playwright({"playwright_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_frontend_test_failure", "edge: playwright fail + retries → escalation")
check(route_after_playwright({"playwright_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: playwright fail + exhausted → failure")
check(route_after_plan({"plan": "do X"}) == "code", "edge: plan → code")
check(route_after_plan({}) == "failure", "edge: empty plan → failure")
r = nodes.node_cleanup({})
check(r == {}, "node_cleanup safe with no workspace")

# ═════ Scenario 13: TaskEngine thin wrapper ═════
print("\n── Scenario 13: TaskEngine.run_once() ──")
import task_engine  # noqa: E402
reset_calls(111)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
task_engine.tool_redmine_list_pending = lambda: {
    "success": True,
    "result": [{"id": 111, "subject": "Wrapper test", "description": "d"}]}
task_engine.tool_redmine_set_status = nodes.tool_redmine_set_status
engine = task_engine.TaskEngine()
check(engine.run_once() is True, "run_once returns True when MR opened")
check(calls["docker"] == 1, "graph executed via wrapper")
task_engine.tool_redmine_list_pending = lambda: {"success": True, "result": []}
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
check(not imported & {"RedmineClient", "GitLabClient", "DockerRunner", "FrontendRunner",
                      "redmine_client", "gitlab_client", "docker_runner",
                      "frontend_runner", "llm_client"},
      "task_engine.py has no direct client imports")
check("from graph.builder import graph" in src, "task_engine imports graph.builder.graph")
node_names = set(compiled.get_graph().nodes)
check({"setup", "load_skills", "plan", "code", "detect_stack", "phpunit_test",
       "on_test_failure", "vitest_test", "playwright_test",
       "on_frontend_test_failure", "commit", "failure", "cleanup"} <= node_names,
      "all 13 nodes registered")
import graph.tools as tools_mod
import inspect
tool_fns = [f for n, f in inspect.getmembers(tools_mod, inspect.isfunction)
            if n.startswith("tool_")]
check(len(tool_fns) == 12, "12 MCP tool functions defined")
check("langgraph" not in inspect.getsource(tools_mod), "tools.py has no LangGraph imports")

env_example = open(".env.example").read()
for var in ("DOCKER_SANDBOX_PHP_IMAGE", "DOCKER_SANDBOX_NODE_IMAGE",
            "DOCKER_SANDBOX_E2E_IMAGE"):
    check(var in env_example, f"{var} present in .env.example")
check("DOCKER_SANDBOX_IMAGE=" not in env_example,
      "legacy DOCKER_SANDBOX_IMAGE removed from .env.example")
runner_src = open("docker_runner.py").read()
check("DOCKER_SANDBOX_PHP_IMAGE" in runner_src and "DOCKER_SANDBOX_IMAGE\"" not in runner_src,
      "docker_runner.py reads DOCKER_SANDBOX_PHP_IMAGE")

print(f"\nALL {passed_checks} CHECKS PASSED ✅")
