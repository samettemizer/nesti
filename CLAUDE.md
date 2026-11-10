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
mcp_server/                  FastMCP stdio server; tools/{issues,gitlab,docker,skills,memory,oauth,project,stats}.py
llm_client.py                provider cascade — the only module that calls LLMs
prompt_builder.py            plan + code prompts composed per task scope, FILE-block output format
issue_scope.py               backend/frontend/fullstack task scope + documentation-request check
issue_domain.py              domain-split backend: owning domains from stated names/routes, LLM classify via the
                             passed client, GitLab domain question/answer + reconcile; never imports graph.*
conversation_store.py        Redis per-issue history (ai-dev:issue:{id}:messages)
docker_runner.py             PHP sandbox (+ postgres:15 sidecar when phpunit.xml declares pgsql),
                             OpenAPI export, bootstrap, Boost application facts, FILE-block writer
frontend_runner.py           Vitest + Playwright sandboxes
gitlab_issues_client.py      issue intake + label lock; gitlab_client.py: repo + MR
gitlab_project.py            acted-on GitLab project: .env (orchestrator) or the MCP client's git remote;
                             identity() scopes every per-issue Redis key
skill_catalog.py             offline corpus selection; skill_loader.py: issue URLs
embedding.py, vector_store.py, semantic_cache.py   vector memory
reranker.py                  opt-in CPU rerank of retrieved docs (NESTI_RERANKER_ENABLED);
                             deps in requirements-reranker.txt (orchestrator image only)
layer_output.py              condenses sandbox output to its meaningful tail
code_skeleton.py             tree-sitter PHP skeleton of the unnamed example Feature test for the coding prompt (NESTI_TREE_SITTER_ENABLED)
telegram_notifier.py         fire-and-forget alerts
project_layout.py            NESTI_PROJECT_PATH backend/SPA layout → state/layout.json; clone_layout for the pipeline
project_boost.py             `nesti /boost`: Laravel Boost infer-conventions → <project>/.omp rules + skills
architecture_view.py         `nesti /arch`: offline Plotly page state/architecture.html
stats/                       usage events (LLM attempts + tool runs) → Redis nesti:stats:events; view.py: page render + `nesti /stats` (prints the URL);
                             server.py: `nesti-stats` live page on 127.0.0.1:8790; report.py: JSON summary behind the `stats_summary` MCP tool
scripts/                     oauth.py (`nesti` CLI), nesti (host launcher), fetch_skills.py, index_skills.py,
                             preflight.py, seed_live_issues.py,
                             prepare_reranker.py (build-time model artifact),
                             evaluate_reranker.py + reranker_evaluation.py (offline quality gate)
skills/, templates/          vendored doc corpus (primevue/laravel/practices),
                             bootstrap templates (laravel/, spa/), boost/ SPA discovery skill
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
   needs no Vitest or Playwright test; a change that touches none of
   `routes/api.php`, a route file under `routes/<dir>/`, or an
   `Http/Controllers`, `Http/Resources` or `Http/Requests` folder anywhere
   under `app/` (domains included) does not run the OpenAPI layer. No change
   reaches `commit` without at least one layer having run green.
6. **Never add direct LLM API calls outside `llm_client.py`.**
7. **Never make `telegram_notifier.py` raise exceptions** — always fire-and-forget.
8. **Sandbox containers must never survive their run.** `docker_runner.py` and
   `frontend_runner.py` both detach, `wait(timeout=…)`, read logs, and remove
   the container in a `finally` block. Keep the `finally` removal and keep the
   timeout enforceable — do not "simplify" either runner to a blocking
   `containers.run(remove=True)`, which cannot take a run-duration timeout.
   A pgsql PHPUnit run's `nesti-pg-*` sidecar (with its volume) and
   `nesti-run-*` network are removed in the same way, on every path. Both
   frontend sandboxes install npm dependencies into an anonymous volume at
   `/app/node_modules` (never the host workspace — a `noexec` host mount
   breaks esbuild); `remove(force=True, v=True)` deletes it with the container.
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
    single gate and is change-aware: `run_phpunit` is False for a change that
    touched only the SPA folder while the frontend layers run, and True
    whenever the frontend layers do not run. Hard-wiring `detect_stack → phpunit_test`
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
    `php:8.4-cli` with `pdo_pgsql bcmath gd intl pcntl` (managed projects may
    require `^8.4`; composer's platform check fails on 8.3), and its CMD
    stays byte-identical to `docker_runner._TEST_COMMAND`. The PHPUnit
    PostgreSQL sidecar is pinned to `postgres:15` (`docker_runner._POSTGRES_IMAGE`). `Dockerfile.sandbox.node` is
    `node:22-alpine` (`vitest@5` requires Node `^22.12`; `node:20-alpine` is
    too old), and `Dockerfile.sandbox.e2e` is
    `mcr.microsoft.com/playwright:v1.50.0-noble` **plus** an explicit Node 22
    install — the image itself ships Node 20, which `vite`/`vitest` refuse.
    Noble is the Playwright 1.50 base tag; the E2E image runs no PHP.
23. **The API surface must stay fully documented.** `tool_openapi_export`
    compares `php artisan scramble:export` output against
    `php artisan route:list --json`. A project with routes under `/api` fails
    the attempt when any `/api` route is missing. A project whose `apiPrefix`
    is not `api` fails when an `api`-group route the change *added* is missing:
    the clone's HEAD route list (a detached worktree, `run_route_list`) is the
    baseline, exported at most once per run and cached in
    `openapi_baseline_routes`; routes already registered at HEAD are not
    re-checked, and a failed HEAD export fails the attempt (never a silent
    pass). `scramble:analyze` is advisory only (`|| echo`) — it exits
    non-zero on any unresolved type anywhere in the application, so gating on
    it would strand every issue. Never loosen the comparison to make a run
    pass; tighten the coding prompt instead.
24. **`templates/laravel/**` is only applied wholesale to a repository Nesti
    scaffolded itself:** scaffold mode (no `artisan`, no `composer.json`) writes
    `_SCAFFOLD_TEMPLATES`, the spatie seed data and an absent README.md; top-up
    writes only an absent `tests/Feature/OpenApiDocumentationTest.php` into the
    backend and absent `vitest.config.js`, `vitest.setup.js`,
    `playwright.config.js` into the SPA (an unmodified earlier Nesti
    `vitest.config.js` is upgraded in place), never `routes/**`. A
    `composer.json` without `artisan` is refused outright.
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
31. **Nesti works only on a separated SPA and an API-only Laravel backend.** A
    Laravel app that serves its own frontend — a backend `vite.config.*` using
    `@vitejs/plugin-vue`, `@vitejs/plugin-react` or `@sveltejs/vite-plugin-svelte`,
    or a backend `composer.json` requiring `inertiajs/inertia-laravel` or
    `livewire/livewire` — is refused by `project_layout` (`LayoutError`; polling
    stays disabled at startup), and the greenfield scaffold never produces one.
    Never reintroduce integrated-layout paths: Blade/in-DOM prompt rules, Vue
    test wiring in the Laravel root, PHP in the E2E image.
32. **Application facts shape prompts only.** Before planning a
    backend/fullstack issue, `tool_app_facts` runs Laravel Boost's
    `ApplicationInfo` and `DatabaseSchema` (summary) through
    `boost:execute-tool` in the PHP sandbox against a throwaway migrated
    database, only when the backend already requires `laravel/boost`. Never
    composer-require Boost into the clone, never spend an LLM call on it, never
    gate on it; a failed export leaves the section out. `node_plan` logs
    exactly one `APP FACTS:` line per run.
33. **Wire a feature into the existing SPA.** Register a new page in the SPA's
    existing router (and its layout menu when it has one), call the API through
    its existing HTTP client, and keep every plugin, theme and component
    registration in `src/main.*`.
34. **A rejected claim stops before clone/bootstrap/LLM.** Cleanup is the
    terminal path; never log an unapplied lock and continue.
35. **Usage recording never changes behaviour.** The `stats` hooks never
    raise into callers and never alter a tool's return value or an attempt's
    exception. They record only counters, model/provider names, durations and
    error text, never prompts or responses. New code for statistics goes into
    `stats/`; existing modules keep one-line hooks only.
36. **A domain-split backend gets its owning domains before planning.** When
    `project_layout._scan_backend` sets `domain_root`, `node_detect_domain`
    (setup → bootstrap) decides: earlier GitLab answer → every stated domain
    plus every domain owning a named route (a route path owned by no domain or
    by several domains asks, even when domains are stated) → planner
    classification, accepted only when exactly one domain is plausible.
    Otherwise it posts one `Which domain is this request for?`
    note (`NESTI_DOMAIN_QUESTION_V1` marker), adds `nesti::pause`, and the run
    goes to cleanup before bootstrap and coding. Reconcile lifts a pause only
    when Nesti's latest note is that question and a human reply names one or
    more options (by name, or a bare list of numbers); each unmatched reply gets
    the question again (one re-ask per reply); manual pauses are never lifted.
    Greenfield backends, backends without a domain root (`domain_catalog()` is
    `None`) and frontend-scope issues are never asked.
    The domains shape prompts only, never a gate: the architecture block names
    only the chosen domains, their files are quoted, and unchosen domains' files
    stay out of the inventory listings, API contracts and `routes/<dir>/` quotes
    (shared files outside every domain stay). `node_detect_domain` logs exactly
    one `DOMAIN:` line per run, domains comma-joined.

---

## Key Module Contracts

| Caller | Callee | Contract |
|--------|--------|----------|
| `task_engine.py` | `graph.builder.graph` | `graph.invoke(initial_state)` → final `IssueState` dict |
| `graph/nodes.py` | `graph/tools.py` | Returns `{"success": bool, ...}` — always |
| `graph/nodes.py` | `llm_client.py` | `generate_plan/code(system, user, messages=None)` → `str` |
| `graph/nodes.py` | `issue_scope.py` | `classify_issue()` / `declared_scope()` never raise; scope ∈ `backend`\|`frontend`\|`fullstack` |
| `graph/nodes.py` | `issue_domain.py` | `domain_catalog()` → `dict`, `None` without a domain architecture; `detect()` → `DomainDecision(domains: tuple, ask, basis)`; `classify(..., llm)` → `(list[str], str)`, never raises; `selection(catalog, names)` → `{root, layers, names, selected, route_files, foreign_route_files}` |
| `graph/nodes.py` | `prompt_builder.py` | `build_plan_prompt(..., scope, scope_evidence)` / `build_code_prompt(..., scope)` → `(system, user)` |
| `graph/nodes.py` | `conversation_store.py` | `append()` → updated `list[dict]` |
| `graph/nodes.py` | `docker_runner.py` | `write_files()` → `(bool, list[str])` |
| `graph/nodes.py` | `docker_runner.py` | `run_tests()` → `(bool, str)` |
| `graph/nodes.py` | `graph/tools.py` | `tool_app_facts(backend_path)` → `{"success", "result": {"facts": str, "tables": int, "reason": str}}`; empty facts when skipped |
| `graph/tools.py` | `docker_runner.py` | `run_app_facts()` → `(bool, str)` |
| `graph/tools.py` | `docker_runner.py` | `run_openapi_export()` / `run_bootstrap()` / `run_scramble_install()` → `(bool, str)` |
| `graph/tools.py` | `frontend_runner.py` | `run_vitest()` / `run_playwright()` → `(bool, str)` |
| `graph/tools.py` | `gitlab_issues_client.py` | `lock/close/reopen/pause/resume_issue()` → `bool`, verified by independent GET; `post_note()` (via `issue_domain`) → note id, read back by GET, raises on failure |
| `graph/tools.py` | `issue_domain.py` | `answer()` → `list[str]` (`[]` = no answer); `ask()` posts the question + pauses, raises `RuntimeError` when the pause is unverified; `reconcile()` → `{resumed, asked, waiting, errors}` |
| `task_engine.py` | `graph/tools.py` | `tool_issue_reconcile_domain_questions()` before `tool_issue_list_pending()`; failure logged, never aborts the poll |
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
| `llm_client.py` | `stats` | `with stats.llm_request(role, provider)` per cascade attempt; `_log_usage` → `stats.usage(raw)` |
| `graph/tools.py` | `stats` | `stats.instrument(globals())`; result unchanged; recorded only inside a run |
| `task_engine.py` | `stats` | `begin(issue_id, subject)` before `graph.invoke`, `end()` in `finally` |
| `scripts/oauth.py` | `stats.view` | `cli_stats(args)` → probes the `nesti-stats` server, prints `http://127.0.0.1:8790/`; exit code 0, 1 when the server is down |
| `mcp_server/tools/stats.py` | `stats.report` | `summary(since_hours, project)` → `{"success": bool, "result"\|"error"}`; never raises; `cost_usd` `None` when nothing is priced |

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
