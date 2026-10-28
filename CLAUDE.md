# Nesti – Claude Project Rules

Nesti supports OMP-led development with shared-project discovery, architecture
and MCP tools, and independently processes opted-in English GitLab issues
(`GITLAB_ISSUE_LABEL`, default `nesti`) through its LangGraph pipeline to Merge
Requests. Its development stack is **Laravel API + a separate Vue/PrimeVue SPA**
(Laravel 13 / PrimeVue 5 defaults); existing projects retain their installed
versions and conventions. Planning/coding uses a consumer-first LLM cascade,
with applicable PHPUnit → OpenAPI → Vitest → Playwright gates in ephemeral
Docker sandboxes. `nesti-mcp` exposes tools, not an LLM runtime.

`NESTI_PROJECT_PATH` identifies the shared project directory, which may contain
separate backend/frontend directories. A configured frontend must be a
standalone SPA, never embedded in or overlapping the Laravel backend. Startup
and `nesti /boost` discover a missing/stale layout through a logged-in consumer
and persist its selection and actual attribution. Boost publishes managed OMP
rules under that project's root `.omp`; `nesti /arch` and MCP read the same
architecture evidence. These commands do not commit, push or rewrite app code.

Area references live in `.omp/rules/` (kept out of the repository) and are
listed in the rulebook: read `rule://<name>` before changing files its globs
name. User-facing overview: `README.md`.

---

## Module Map

```
main.py, task_engine.py      memory/layout/Boost initialization → issue selection → graph.invoke()
graph/state.py               IssueState, the data contract between nodes
graph/tools.py               tool_* functions returning {"success": bool, ...}
graph/nodes.py               nodes; each returns a partial IssueState
graph/edges.py, builder.py   one router per test layer; compiled `graph`
mcp_server/                  FastMCP stdio server; tools/{issues,gitlab,docker,skills,memory,oauth,project}.py
llm_client.py                provider cascade — the only module that calls LLMs
prompt_builder.py            plan + code prompts composed per task scope, FILE-block output format
issue_scope.py               backend/frontend/fullstack task scope + documentation-request check
e2e_fixtures.py              manifest/report and trusted dependency metadata contracts
issue_dependencies.py        durable pause/child/merge/release workflow; no LLM
issue_escalations.py         journaled assisted-issue creation/completion/handoff; no LLM
project_context.py           verified GitLab identity, project namespace, persisted API/SPA layout
project_architecture.py      pruned evidence, Composer roots, snapshots and project-rule loading
project_boost.py             isolated official Boost discovery and owned OMP-rule publication
architecture_view.py         D2-rendered local architecture view
conversation_store.py        Redis history (ai-dev:issue:{namespace}:{id}:messages)
docker_runner.py             PHP/Boost sandboxes, OpenAPI, bootstrap, layout-aware FILE/DELETE writer
frontend_runner.py           Vitest + Playwright sandboxes
gitlab_issues_client.py      issue intake + label lock; gitlab_client.py: repo + MR
skill_catalog.py             offline corpus selection; skill_loader.py: issue URLs
embedding.py, vector_store.py, semantic_cache.py   vector memory
reranker.py                  opt-in CPU rerank of retrieved docs (NESTI_RERANKER_ENABLED);
                             deps in requirements-reranker.txt (orchestrator image only)
layer_output.py              condenses sandbox output to its meaningful tail
telegram_notifier.py         fire-and-forget alerts
scripts/                     oauth.py (`nesti` CLI), fetch_skills.py, index_skills.py,
                             preflight.py, seed_live_issues.py, e2e_fixtures.php, boost_bridge.php,
                             prepare_reranker.py (build-time model artifact),
                             evaluate_reranker.py + reranker_evaluation.py (offline quality gate)
skills/, templates/laravel/  vendored doc corpus (primevue/laravel/practices),
                             bootstrap templates
test_graph_smoke.py          offline regression net (.venv/bin/python test_graph_smoke.py)
test_project_*.py            layout, architecture, Boost, memory and clean-clone regressions
test_issue_escalations.py, test_mcp_project.py, test_startup.py   service/startup contracts
test_live_laravel.py         opt-in real-container proof (Docker + network)
```

---

## Absolute Rules — Never Violate

1. **Schema changes go into NEW migrations** under `database/migrations`. Never
   edit, rename, or delete a migration that already exists in the repository.
2. **Every migration implements both `up()` and `down()`**; `down()` reverses
   `up()` exactly.
3. **Use the Schema builder / Blueprint API only.** No raw DDL (`DB::statement`
   with `CREATE`, `ALTER`, `DROP`): the test suite runs on SQLite and
   vendor-specific SQL breaks it.
4. **Never call `migrate:fresh`, `migrate:reset`, `db:wipe`, or truncate
   tables** from application code, seeders, or tests. Test and demo data comes
   from model factories (`database/factories`) and seeders
   (`database/seeders`) with Faker — never from hand-written `INSERT`
   statements. Keep models in sync with the schema: `$fillable`, `$casts`,
   relationships, `HasFactory`.
5. **Every code change must be accompanied by a test in its own layer** —
   PHPUnit for PHP, the OpenAPI gate for `/api` routes, Vitest + Playwright for
   Vue. A frontend-only change needs no PHPUnit test; a backend-only change
   needs no Vitest or Playwright test. OpenAPI follows registered API routes
   and HTTP classes under Composer source roots, conservatively including
   unresolved routing; it is not limited to `routes/api.php` or `app/Http`.
   No change reaches `commit` without at least one layer having run green.
6. **Never add direct LLM API calls outside `llm_client.py`.**
7. **Never make `telegram_notifier.py` raise exceptions** — always fire-and-forget.
8. **Sandbox containers must never survive their run.** `docker_runner.py` and
   `frontend_runner.py` both detach, `wait(timeout=…)`, read logs, and remove
   the container in a `finally` block. Keep the `finally` removal and keep the
   timeout enforceable — do not "simplify" either runner to a blocking
   `containers.run(remove=True)`, which cannot take a run-duration timeout.
9. **Every function in `graph/tools.py` must return `{"success": bool, ...}`.**
10. **Never store secrets in code** — all credentials come from `.env`.
11. **`node_cleanup` must always run** — it is the final node in every path.
12. **Nodes return partial state dicts only** — never mutate state directly.
13. **MCP tool wrappers in `mcp_server/tools/` must remain thin** — delegation
    and JSON serialisation only; no business logic.
14. **Never move the tools import above `app = FastMCP("nesti")`** in
    `mcp_server/server.py`, and never remove the `__main__`
    canonical-delegation guard.
15. **MCP tools must return JSON-serialisable dicts only** — never dataclass
    instances or other rich objects across the transport boundary.
16. **Container and image names use the `nesti-` prefix** — `ai-developer`,
    `ai-dev-redis`, and `hello-world-sandbox` must never be reintroduced as
    container/image names. Existing `ai-dev:issue:` and `ai-dev:oauth:` Redis
    key prefixes are retained.
17. **Never force PHPUnit on a stack that cannot run it.** `run_phpunit` is the
    single gate and is change-aware: False for a `"vue"` stack and for a
    frontend-only change while the frontend layers run; True whenever the
    frontend layers do not run. Hard-wiring `detect_stack → phpunit_test`
    sends every frontend-only issue to permanent failure.
18. **Never scan the workspace without pruning** `node_modules` and `vendor`
    (see `rule://frontend-testing`) — a bare `rglob("*.vue")` misdetects installed
    dependencies as project source from the second attempt onward.
19. **Sandbox installs must tolerate both a missing and a stale lockfile** —
    keep `npm ci || npm install` (and the no-lockfile branch) in both frontend
    Dockerfiles. The workspace is mounted read-write, so retries inherit the
    previous attempt's lockfile.
20. **Never let Vitest see `e2e/`** — keep the `--exclude 'e2e/**'` flag in the
    Node sandbox CMD *and* the `exclude` entry in the generated
    `vitest.config.js`. Vitest's default glob matches Playwright specs.
21. **`@playwright/test` is pinned exactly, never with a caret**, and its
    version and the E2E image's base tag change together.
22. **Sandbox base images are pinned and coupled.** `Dockerfile.sandbox` is
    `php:8.3-cli` (Laravel 13's floor is `^8.3`), `Dockerfile.sandbox.node` is
    `node:22-alpine` (`vitest@5` requires Node `^22.12`; `node:20-alpine` is
    too old), and `Dockerfile.sandbox.e2e` is
    `mcr.microsoft.com/playwright:v1.50.0-noble` **plus** an explicit Node 22
    install — the image itself ships Node 20, which `vite`/`vitest` refuse.
    Noble rather than jammy because Ubuntu 24.04 carries `php8.3-cli`.
23. **Every `/api` route must stay fully documented, including custom route files.** `tool_openapi_export`
    compares `php artisan scramble:export` output against
    `php artisan route:list --json` and fails the attempt when any `/api` route
    is missing. `scramble:analyze` is advisory only (`|| echo`) — it exits
    non-zero on any unresolved type anywhere in the application, so gating on
    it would strand every issue. Never loosen the comparison to make a run
    pass; tighten the coding prompt instead.
24. **`templates/laravel/**` is only applied wholesale to a repository Nesti
    scaffolded itself.** The legacy greenfield `scaffold` path writes all nine
    templates; it is not a layout policy for configured shared projects.
    Existing Laravel apps use `top-up`: install absent Scramble and add absent
    OpenAPI test coverage; frontend test configs are considered only when Vue
    exists and a matching JS/TS config is absent. Do not replace app entries,
    routes, themes or dependencies, or add frontend scaffolding to an API-only
    backend. A `composer.json` without `artisan` is refused.
25. **`skills/primevue/`, `skills/laravel/` and `skills/registry.json` are
    generated only by `scripts/fetch_skills.py`** and are committed. Never
    hand-edit a vendored document and never fetch documentation at run time:
    `skill_catalog.select_skills` is deterministic and offline.
    `skills/practices/` is the one hand-maintained tier: Nesti adaptations of
    upstream engineering skills (provenance and licence in each front matter,
    licence texts in `skills/practices/licenses/`) that shape the code Nesti
    writes — PHP/Laravel, Vue/PrimeVue or the four test layers; nothing else
    earns a place there. After editing one, re-index it with
    `scripts/fetch_skills.py --only practices`. The only run-time fetch left
    is the issue's own URL skills via `skill_loader`.
26. **Never report a guessed `remaining`/`limit` from
    `ConsumerProvider.get_usage()`** — `None` is the correct answer when a
    provider has no quota API, and `node_on_layer_failure`'s quota check
    depends on that honesty to avoid firing (or missing) alerts off
    fabricated numbers.
27. **Consumer subscriptions are consumed before any per-token API.** The
    consumer tier is the head of both chains; `DEEPSEEK_API_KEY` /
    `ANTHROPIC_API_KEY` are the overflow. Never re-order the chains so a
    billed API runs while a logged-in subscription is still usable, and
    never put OAuth-token handling back into `AnthropicLLMClient` — that
    made the API-key tier unreachable whenever a `claude` session existed.
28. **Provider availability is re-checked before every attempt.** Build the
    consumer clients unconditionally and let `available` decide; snapshotting
    login state at construction strands `nesti /provider login|logout` behind
    a container restart, because `graph/nodes.py` holds one module-level
    `LLMClient`.
29. **The task scope shapes prompts only — never a test gate.** Layers follow
    the files the change touched (`run_phpunit` / `run_openapi` /
    `run_frontend`), not the repository and not the scope. An uncertain scope
    is `fullstack`; a narrow scope is widened to `fullstack` when a layer
    outside it fails. `node_plan` emits exactly one `SCOPE:` log line per run.
30. **README.md, CHANGELOG.md and `docs/` stay out of a change** unless
    `issue_scope.documentation_request` finds the issue asking for them.
    `_prune_stale_files` restores committed files (`git checkout HEAD --`),
    never deletes them, and the scaffold never copies the skeleton README.
31. **A missing fixture needs exit 78 plus a valid declared sandbox report.**
    Never infer it from timeout text, locators, mocks or an empty response.
    Broken seeders and API/contract errors remain ordinary failures.
32. **Dependency truth lives in trusted GitLab notes, not Redis history.**
    Keep intent → verified pause → submitted → one child POST ordering.
    No parent LLM/retry while held; release only after a qualifying related MR
    actually merges on the recorded project/target.
33. **Wire a feature into the existing served SPA entry chain.** Preserve
    installed PrimeVue/plugins/theme and root architecture; register before
    mount. Never create an unused entry or move the SPA into Laravel.
34. **A rejected claim stops before clone/bootstrap/LLM.** Cleanup is the
    terminal path; never log an unapplied lock and continue.
35. **Keep project, Git, backend and SPA roots distinct.** `repo_path` is the
    cloned backend, `git_root` owns Git operations and repository-relative
    FILE/DELETE paths, and `frontend_path` owns frontend sandboxes. Missing,
    overlapping, escaping or symlinked selected roots fail before bootstrap.
36. **Only startup and `/boost` may discover a layout.** For a containing
    project, validate the consumer's JSON against safe directory/manifest
    markers and the verified Git worktree before saving `layout.json`.
    Layout selection is consumer-only; ordinary Boost inference retains the
    full cascade. `/arch` and MCP never invoke discovery or an LLM.
37. **Boost may publish only its owned root-level `.omp` rules and manifest.**
    Run pinned Laravel Boost in a disposable copy, with network disabled for
    the bridge. Preserve user rules/source/Composer files; use ownership
    hashes, a project lock and recoverable publication journal. Current source
    and human rules outrank inferred conventions; safety/test rules still apply.
38. **Escalation mutations require verified ownership and read-back.** Reuse
    the operation UUID; two reported rejections create one unlabeled issue.
    Approved round three requires verified runtime-model attribution before
    closure; failed round three requires verified handoff evidence before
    opt-in. Never replay an ambiguous POST or apply the rejected local patch.
39. **Private memory is project-namespaced.** Missing identity disables it;
    Qdrant docs remain shared. Cached solutions record MR opening, not verified
    merge. Never recover legacy issue history by guessing its project.

---

## Key Module Contracts

| Caller | Callee | Contract |
|--------|--------|----------|
| `task_engine.py` | `graph.builder.graph` | `graph.invoke(initial_state)` → final `IssueState` dict |
| `graph/nodes.py` | `graph/tools.py` | Returns `{"success": bool, ...}` — always |
| `graph/nodes.py` | `llm_client.py` | `generate_plan/code(system, user, messages=None)` → `str` |
| `graph/nodes.py` | `issue_scope.py` | `classify_issue()` / `declared_scope()` never raise; scope ∈ `backend`\|`frontend`\|`fullstack` |
| `graph/nodes.py` | `prompt_builder.py` | `build_plan_prompt(..., scope, scope_evidence)` / `build_code_prompt(..., scope)` → `(system, user)` |
| `graph/nodes.py` | `conversation_store.py` | `append()` → updated `list[dict]` |
| `graph/nodes.py` | `docker_runner.py` | `write_files()` → `(bool, list[str])` |
| `graph/nodes.py` | `docker_runner.py` | `run_tests()` → `(bool, str)` |
| `graph/tools.py` | `docker_runner.py` | `run_openapi_export()` / `run_bootstrap()` / `run_scramble_install()` → `(bool, str)` |
| `graph/tools.py` | `frontend_runner.py` | `run_vitest()` → `(bool, str)`; `run_playwright()` → `{"passed": bool, "output": str, "fixture_request": dict\|None}` |
| `graph/tools.py` | `gitlab_issues_client.py` | `lock/close/reopen/pause/resume_issue()` → `bool`, verified by independent GET |
| `graph/tools.py` | `issue_dependencies.py` | `pause_for_fixture(...)` → paused/ineligible/error; `reconcile()` → resumed/waiting/errors; no LLM |
| `graph/tools.py` | `skill_catalog.py` | `select_skills()` never raises, returns `list[Skill]` |
| `mcp_server/tools/*.py` | `graph/tools.py` | pass-through `{"success": bool, ...}` — no reshaping |
| `mcp_server/tools/skills.py` | `skill_loader.py` / `skill_catalog.py` | returns JSON-serialisable dicts (never `Skill` dataclasses) |
| MCP clients (stdio) | `mcp_server/server.py` | tools registered at import; served via `app.run_stdio_async()` |
| `skill_loader.py` | callers | `load_skills(issue)` never raises, returns `list[Skill]` |
| `telegram_notifier.py` | callers | `notify(msg)` never raises |
| `graph/tools.py` | `scripts/oauth.py` | `TokenStore` — degrades to in-memory on a Redis outage, never raises; `fetch_usage(store, name, token_data)` renews + persists credentials before `get_usage()` |
| `graph/nodes.py` | `graph/tools.py` | `tool_quota_check()` → `{"success": bool, "result": {<provider>: {"remaining": int\|None, ...}}}` |
| `llm_client.py` | `scripts/oauth.py` | `PROVIDERS[key].fresh_credentials(token_data)` → usable `token_data`; caller persists it when it differs |
| `llm_client.py` | callers | `BaseLLMClient.available` → `bool`, cheap and side-effect free; consulted before every attempt |
| `graph/tools.py` | `vector_store.py` / `semantic_cache.py` | memory tools degrade gracefully (`success=True`, empty list or `stored=False`) when memory unavailable; `success=False` only on genuine exception |
| startup / `/boost` | `project_context.py` | `configured_project_root(discover=True)` → validated backend `Path`; persist containing-project layout |
| architecture / pipeline / escalation | `project_context.py` | `inspect_project(backend)` → verified project/Git/backend/SPA identity; no LLM |
| startup / CLI | `project_boost.py` | `boost_project(backend, force=False)` → completed/skipped/conflicts; other failures raise |
| CLI / MCP / pipeline | `project_architecture.py` | shared structural snapshot and evidence-validated rules; no project-code execution |
| `graph/tools.py` | `issue_escalations.py` | history/create/complete/handoff → JSON `{success, result}` or `{success: False, error, code?}` |

---

## Code Style

- Python 3.12+, type hints on all public functions
- `str | None` union syntax (not `Optional[str]`)
- `logger = logging.getLogger(__name__)` in every module
- Constants at module level in `UPPER_SNAKE_CASE`
- Private helpers prefixed with `_`
- Docstrings on all public classes and functions
- No bare `except:` — always `except Exception as exc:`
- PSR-12 for all generated PHP code
- Vue 3 Composition API with `<script setup>` for all generated Vue code —
  never `@vue/compat`, never the Options API unless the project already uses it
