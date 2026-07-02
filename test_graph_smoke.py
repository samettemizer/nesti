"""
test_graph_smoke.py – verifies the Phase 2 LangGraph pipeline against the
acceptance checklist, with all external services (Redmine, GitLab, Docker,
LLM providers) monkeypatched at the node/tool seam.

Run:  python test_graph_smoke.py
"""

import logging
import os
import shutil

# ── Environment before any project import ────────────────────────────────────
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ["LOCAL_LLM_ENABLED"] = "false"
os.environ["HERMES3_LLM_ENABLED"] = "false"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"   # unreachable → memory fallback
os.environ["MAX_CODE_RETRIES"] = "2"                 # → max_attempts = 3
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
os.environ.pop("TELEGRAM_CHAT_ID", None)
os.environ.pop("DEEPSEEK_API_KEY", None)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "DEBUG"),
                    format="%(levelname)s %(name)s – %(message)s")

import graph.nodes as nodes                      # noqa: E402
from graph.builder import graph as compiled     # noqa: E402
from graph.edges import route_after_test, route_after_plan  # noqa: E402

GOOD_CODE = (
    "Implementation below.\n\n"
    "### FILE: src/Hello.php\n```php\n<?php\necho 'hello';\n```\n\n"
    "### FILE: tests/HelloTest.php\n```php\n<?php\n// phpunit test\n```\n"
)
NO_BLOCKS = "Here is a prose description of the change instead of files."

calls: dict = {}


def reset_calls(issue_id: int) -> None:
    calls.clear()
    calls.update({
        "issue_id": issue_id, "redmine": [], "docker": 0, "escalate": 0,
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
        "test_output": "", "test_passed": False,
        "mr_url": "", "failure_reason": "", "error": "",
    }


def patch_tools(docker_outcomes, code_responses, plan_exc=None, code_exc_first=False):
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

    def fake_docker(workspace_path):
        calls["docker"] += 1
        passed = docker_outcomes[min(calls["docker"] - 1, len(docker_outcomes) - 1)]
        out = "OK (2 tests, 4 assertions)" if passed else "PHPUnit FAILURES!\n1) HelloTest::testHello"
        return {"success": True, "result": {"passed": passed, "output": out}}
    nodes.tool_docker_run_tests = fake_docker

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
    final = compiled.invoke(initial(issue_id), config={"recursion_limit": 50})
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

# ═════ Scenario 5: nodes/edges testable in isolation (total=False state) ═════
print("\n── Scenario 5: isolated node/edge tests with partial state ──")
r = nodes.node_test({})   # empty state – every field optional
check(r == {"test_passed": False,
            "test_output": nodes._NO_FILE_BLOCKS_OUTPUT}, "node_test runs on empty state")
check(route_after_test({"test_passed": True}) == "commit", "edge: pass → commit")
check(route_after_test({"test_passed": False, "attempt": 1, "max_attempts": 3})
      == "on_test_failure", "edge: fail + retries → on_test_failure")
check(route_after_test({"test_passed": False, "attempt": 3, "max_attempts": 3})
      == "failure", "edge: fail + exhausted → failure")
check(route_after_plan({"plan": "do X"}) == "code", "edge: plan → code")
check(route_after_plan({}) == "failure", "edge: empty plan → failure")
r = nodes.node_cleanup({})
check(r == {}, "node_cleanup safe with no workspace")

# ═════ Scenario 6: TaskEngine thin wrapper ═════
print("\n── Scenario 6: TaskEngine.run_once() ──")
import task_engine  # noqa: E402
reset_calls(105)
patch_tools(docker_outcomes=[True], code_responses=[GOOD_CODE])
task_engine.tool_redmine_list_pending = lambda: {
    "success": True,
    "result": [{"id": 105, "subject": "Wrapper test", "description": "d"}]}
task_engine.tool_redmine_set_status = nodes.tool_redmine_set_status
engine = task_engine.TaskEngine()
check(engine.run_once() is True, "run_once returns True when MR opened")
check(f is not None and calls["docker"] == 1, "graph executed via wrapper")
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
check(not imported & {"RedmineClient", "GitLabClient", "DockerRunner",
                      "redmine_client", "gitlab_client", "docker_runner", "llm_client"},
      "task_engine.py has no direct client imports")
check("from graph.builder import graph" in src, "task_engine imports graph.builder.graph")
node_names = set(compiled.get_graph().nodes)
check({"setup", "load_skills", "plan", "code", "test", "on_test_failure",
       "commit", "failure", "cleanup"} <= node_names, "all 9 nodes registered")
import graph.tools as tools_mod
import inspect
tool_fns = [f for n, f in inspect.getmembers(tools_mod, inspect.isfunction)
            if n.startswith("tool_")]
check(len(tool_fns) == 9, "9 MCP tool functions defined")
check("langgraph" not in inspect.getsource(tools_mod), "tools.py has no LangGraph imports")

print(f"\nALL {passed_checks} CHECKS PASSED ✅")
