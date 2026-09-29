# Nesti – Claude Project Rules

Nesti is an autonomous orchestrator: a developer opens an English GitLab issue
with the opt-in label (`GITLAB_ISSUE_LABEL`, default `nesti`) and the LangGraph
pipeline drives it to a **Laravel 13 + PrimeVue 5** Merge Request — planning and
coding through a consumer-first LLM cascade, then gating on PHPUnit → OpenAPI →
Vitest → Playwright in ephemeral Docker sandboxes. `nesti-mcp` exposes the same
tool layer to MCP clients alongside the orchestrator and makes no LLM calls. An
issue may be backend, frontend or both; Nesti is not a PHP-only orchestrator.

Area references live in `.omp/rules/` (kept out of the repository) and are
listed in the rulebook: read `rule://<name>` before changing files its globs
name. User-facing overview: `README.md`.

---

## Module Map

```
main.py, task_engine.py      entry point (--loop / single run) → graph.invoke()
graph/state.py               IssueState, the data contract between nodes
graph/tools.py               tool_* functions returning {"success": bool, ...}
graph/nodes.py               nodes; each returns a partial IssueState
graph/edges.py, builder.py   one router per test layer; compiled `graph`
mcp_server/                  FastMCP stdio server; tools/{issues,gitlab,docker,skills,memory,oauth}.py
llm_client.py                provider cascade — the only module that calls LLMs
prompt_builder.py            plan + code prompts, FILE-block output format
conversation_store.py        Redis per-issue history (ai-dev:issue:{id}:messages)
docker_runner.py             PHP sandbox, OpenAPI export, bootstrap, FILE-block writer
frontend_runner.py           Vitest + Playwright sandboxes
gitlab_issues_client.py      issue intake + label lock; gitlab_client.py: repo + MR
skill_catalog.py             offline corpus selection; skill_loader.py: issue URLs
embedding.py, vector_store.py, semantic_cache.py   Phase 8 vector memory
layer_output.py              condenses sandbox output to its meaningful tail
telegram_notifier.py         fire-and-forget alerts
scripts/                     oauth.py (`nesti` CLI), fetch_skills.py, index_skills.py,
                             preflight.py, seed_live_issues.py
skills/, templates/laravel/  vendored doc corpus, bootstrap templates
test_graph_smoke.py          offline regression net (.venv/bin/python test_graph_smoke.py)
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
   needs no Vitest or Playwright test; a change that does not touch
   `routes/api.php`, `app/Http/Controllers`, `app/Http/Resources` or
   `app/Http/Requests` does not run the OpenAPI layer. No change reaches
   `commit` without at least one layer having run green.
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
    `ai-dev-redis`, and `hello-world-sandbox` must never be reintroduced (the
    `ai-dev:issue:` Redis key prefix is the one deliberate exception).
17. **Never force PHPUnit on a stack that cannot run it.** `run_phpunit` is the
    single gate; a `"vue"` stack skips the PHP layer. Hard-wiring
    `detect_stack → phpunit_test` sends every frontend-only issue to permanent
    failure.
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
23. **`routes/api.php` must stay fully documented.** `tool_openapi_export`
    compares `php artisan scramble:export` output against
    `php artisan route:list --json` and fails the attempt when any `/api` route
    is missing. `scramble:analyze` is advisory only (`|| echo`) — it exits
    non-zero on any unresolved type anywhere in the application, so gating on
    it would strand every issue. Never loosen the comparison to make a run
    pass; tighten the coding prompt instead.
24. **`templates/laravel/**` is only applied wholesale to a repository Nesti
    scaffolded itself.** `tool_laravel_bootstrap` writes all nine templates in
    `scaffold` mode (greenfield: no `artisan`, no `composer.json`); in `top-up`
    mode it writes only the absent `vitest.config.js`,
    `playwright.config.js` and `tests/Feature/OpenApiDocumentationTest.php`
    and never touches `vite.config.js`, `resources/js/app.js`,
    `resources/views/**` or `routes/**`. A `composer.json` without `artisan` is
    refused outright — scaffolding over a foreign PHP app would destroy it.
25. **`skills/` is generated only by `scripts/fetch_skills.py`** and is
    committed. Never hand-edit a vendored document and never fetch
    documentation at run time: `skill_catalog.select_skills` is deterministic
    and offline. The only run-time fetch left is the issue's own URL skills via
    `skill_loader`.
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

---

## Key Module Contracts

| Caller | Callee | Contract |
|--------|--------|----------|
| `task_engine.py` | `graph.builder.graph` | `graph.invoke(initial_state)` → final `IssueState` dict |
| `graph/nodes.py` | `graph/tools.py` | Returns `{"success": bool, ...}` — always |
| `graph/nodes.py` | `llm_client.py` | `generate_plan/code(system, user, messages=None)` → `str` |
| `graph/nodes.py` | `conversation_store.py` | `append()` → updated `list[dict]` |
| `graph/nodes.py` | `docker_runner.py` | `write_files()` → `(bool, list[str])` |
| `graph/nodes.py` | `docker_runner.py` | `run_tests()` → `(bool, str)` |
| `graph/tools.py` | `docker_runner.py` | `run_openapi_export()` / `run_bootstrap()` / `run_scramble_install()` → `(bool, str)` |
| `graph/tools.py` | `frontend_runner.py` | `run_vitest()` / `run_playwright()` → `(bool, str)` — never raise |
| `graph/tools.py` | `gitlab_issues_client.py` | `lock/close/reopen_issue()` → `bool`, verified against a read-back |
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
