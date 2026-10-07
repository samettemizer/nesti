# Nesti — autonomous developer

## Goal

A self-contained orchestrator that reads GitLab issues, generates a Laravel 13 +
PrimeVue 5 implementation through a cascading LLM pipeline, validates it across
four test layers in Docker sandboxes, and opens GitLab Merge Requests — without
a human writing a single line of code.

---

## How it works

```
GitLab issue (labelled, opt-in)
  → claim issue            independently verified lock, or stop before cloning
  → bootstrap             scaffold or top-up the Laravel app
  → load skills            vendored corpus + URLs from the issue
  → decide scope           [backend | frontend | fullstack]  issue text, confirmed by the planner
  → generate plan          [Local LLM → DeepSeek → Claude Sonnet]
  → generate code          [Local LLM → DeepSeek → Claude Sonnet]
  → detect layers          from the files the change touched
  → run the applicable test layers, sequential gates:
        PHPUnit → OpenAPI → Vitest → Playwright
  → all green: commit + push + GitLab MR (body: Closes #<iid>) + close issue
  → red layer: escalate provider, retry (shared budget: MAX_CODE_RETRIES + 1)
  → verified missing E2E fixture: pause, open one backend dependency, wait for its MR merge
  → all retries exhausted: remove lock label, comment failure, return to pending
```

Test layers follow the files the attempt wrote — not the repository, not the
scope. A PHP-only change runs PHPUnit (→ OpenAPI when it touches the `/api`
surface); a **frontend-only change skips PHPUnit** and runs Vitest →
Playwright, also in a Laravel repository; a change touching both sides
(a Blade view or `routes/web.php` counts as both) runs all four; a change
touching neither side (a README only) runs PHPUnit, so nothing reaches commit
untested. A repository with no PHP at all always runs Vitest → Playwright.
Vue-only issues are ordinary work.

The **scope** (`backend`, `frontend`, `fullstack`) is decided offline from the
issue text, then confirmed or corrected by the planner on line 1 of its plan.
It narrows the prompts and reference documents to the side the issue is about;
it never gates a test layer. When a layer outside the scope fails, the retry
widens the scope to `fullstack`. Uncertain issues land on `fullstack`, the
prompt every issue received before scopes existed. An issue can pin its scope
with a `Scope: frontend` line. Every run logs one line:

```
SCOPE: frontend · GitLab issue #42 · issue text: frontend (frontend signals: button, colour) · planner: frontend
```

```bash
docker-compose logs -f nesti-orchestrator | grep 'SCOPE:'
```

### Documentation files

`README.md`, `CHANGELOG.md` and anything under `docs/` change only when the
issue asks for it — name the file. Otherwise the prompt forbids touching them,
even when a plan or a past solution lists them; the `/api` contract is
documented by Scramble from the code. The scaffold bootstrap no longer copies
Laravel's skeleton `README.md` over the project's, and a retry that drops a
committed file restores its original content instead of deleting it.

Conversation history is stored in Redis per issue. When tests fail and the
pipeline retries, the model sees its previous attempt and the failure output.
Retries prune stale files: a file the previous attempt created and the new
attempt does not re-emit is deleted, and a committed file it edited is
restored from `HEAD`, so a renamed migration cannot leave two
`create_<table>_table` migrations behind.

---

## Issue Intake (GitLab Issues)

Intake is **opt-in by label**. Only open issues carrying the label configured
in `GITLAB_ISSUE_LABEL` (default `nesti`) are picked up.

GitLab issues have only `opened` and `closed`; intake state lives in labels
and trusted dependency notes:

| State       | Condition |
|-------------|-----------|
| **pending** | open, has `<label>`, neither control label, no active or malformed dependency record |
| **in progress** | open, has `<label>::in-progress` (the lock Nesti owns) |
| **paused** | open, has `<label>::pause` or an active dependency record |
| **done** | closed |

Scoped labels (the `::` form) are mutually exclusive within their scope in
GitLab, which is what makes the lock single-valued. Every mutation is verified
by reading the issue back; a lock or unlock that did not apply is a loud error.

**Success:** Nesti removes the lock label, closes the issue, and comments the
MR URL. The MR description starts with `Closes #<iid>`, so issue and MR are
natively cross-linked.

**Failure (retries exhausted):** Nesti removes the lock label and comments the
failure, returning the issue to the pending pool so it can be retried.

Human closures and opt-outs are never reversed. A manual pause is not removed
by dependency reconciliation. `"new"` status refuses paused or unresolved
dependency issues; it only unlocks an issue still open and opted in.

Issue numbers are the project-scoped `iid` (what `#7` means in the project UI).

See [`ISSUE_GUIDELINE.md`](ISSUE_GUIDELINE.md) for the full issue format and
examples. Any HTTP/HTTPS URL in the issue subject or description is fetched
automatically and injected into the planning prompt as context.

---

## Laravel 13 + PrimeVue 5 Role

The planner and coder operate as a **Laravel 13 architect + PrimeVue 5 frontend
architect**. Database work is allowed and expected:

- New migrations under `database/migrations` (both `up()` and `down()`).
- Model factories (`database/factories`) and seeders (`database/seeders`) with
  Faker — never hand-written `INSERT` statements.
- Schema builder / Blueprint API only — no raw DDL, because the test suite runs
  on SQLite and vendor-specific SQL breaks it.
- Never `migrate:fresh`, `migrate:reset`, `db:wipe`, or truncate tables.
- Never edit, rename, or delete an existing migration.

### Bootstrap node

A `bootstrap` graph node runs right after `setup`:

| Repository state | Mode | Behaviour |
|------------------|------|-----------|
| No `artisan`, no `composer.json` | **scaffold** | `composer create-project` + `php artisan install:api` + `composer require dedoc/scramble`, then all templates from `templates/laravel/` |
| `artisan` present | **top-up** | Writes only the missing `vitest.config.js`, `playwright.config.js`, `tests/Feature/OpenApiDocumentationTest.php` + missing `package.json` keys |
| `composer.json` without `artisan` | **refused** | Returns `success=False` — scaffolding over a foreign PHP app would destroy it |

---

## OpenAPI Layer

The OpenAPI test layer uses [Scramble](https://scramble.dedoc.co/) to validate
that every `/api` route is documented:

1. `php artisan scramble:export --path=openapi.json` — exports the document.
2. `php artisan route:list --json` — lists registered routes.
3. The layer compares the two and **fails the attempt when any `/api` route is
   missing** from the exported document.

`openapi.json` is a committed deliverable (not git-ignored).
`scramble:analyze` is advisory only — it exits non-zero on any unresolved type
anywhere in the application, so the layer runs it with `|| echo` and never
gates on it.

The layer runs only when the attempt touched `routes/api.php`,
`app/Http/Controllers`, `app/Http/Resources`, or `app/Http/Requests`. A pure
`.vue` or migration-only change does not pay for a Scramble export.

---

## Vendored Skill Corpus

The `skills/` directory holds a vendored, offline documentation corpus:

| Category | Count | Source |
|----------|-------|--------|
| PrimeVue 5 component docs | 92 | `primevue.dev/llms` |
| PrimeVue 5 guide pages | 15 | `primevue.dev/llms` |
| Laravel topic docs | 66 | `laravel/docs` 13.x |
| Practice docs | 4 | curated, see below |

`primevue/`, `laravel/` and `registry.json` are generated **only** by
`scripts/fetch_skills.py` and committed to the repository. Never hand-edit a
vendored document.

The practice tier (`skills/practices/`) is the exception: Nesti-maintained
adaptations of upstream engineering skills that shape the code Nesti writes —
test-driven development for the PHPUnit / Vitest / Playwright gates, Laravel +
Vue application security, and visual/UI direction on PrimeVue 5. Each carries
its provenance and licence in its front matter (licence texts in
`skills/practices/licenses/`). After editing one, re-index it offline:

```bash
python scripts/fetch_skills.py --only practices
```

`skill_catalog.py` selects docs **deterministically and offline** per issue by
alias and trigger matching — e.g. "Dropdown" maps to the PrimeVue 5 `Select`
doc, "OrgChart" maps to `organizationchart`, "migration" maps to the Laravel
migrations topic. Each document is capped at 7 000 chars before the
prompt-level budget. Practice docs rank last and are capped at one per prompt:
API documentation always outranks general guidance.

The only run-time fetch left is URLs the issue itself contains, handled by
`skill_loader.py`.

---

## Hierarchical Vector Memory

Semantic retrieval on top of the keyword skill catalog, in two tiers that share
one embedder (`embedding.py`: `BAAI/bge-small-en-v1.5`, 384 dims, fastembed on
the CPU — offline, no API cost, weights baked into the images):

| Tier | Store | Contents | Written by | Read by |
|------|-------|----------|------------|---------|
| Long-term docs | Qdrant (`nesti-qdrant`, collection `nesti_docs`) | the `skills/` corpus, chunked and embedded | `scripts/index_skills.py` | `plan`, `code` (filtered by the issue's scope) |
| Solution cache | Redis 8 query engine (`nesti_solution_idx`) | subject, stack, MR URL and plan of every merged issue; TTL 90 days | `commit` | `plan` |
| Episodic memory | Redis 8 query engine (`nesti_episode_idx`) | condensed output of each failed attempt of the issue in flight | `on_layer_failure` | `code` (older attempts only) |

The vector index reaches passages past the catalog's 7 000-char cap and
documents whose name the issue never mentions; chunks the catalog already
injected are dropped. Hits below the cosine floors (`NESTI_SOLUTION_MIN_SCORE`
0.80, `NESTI_EPISODE_MIN_SCORE` 0.60) are never injected. Episodes are deleted
when their issue finishes.

Memory is optional and never raises: an unreachable Qdrant, a pre-8 Redis or a
missing embedder degrades retrieval to "no results", and
`NESTI_MEMORY_ENABLED=false` runs the pipeline exactly as before. Index the
corpus with Redis/Qdrant available before starting the poller, and after
`fetch_skills.py`; changing the embedding model requires `--recreate`:

```bash
docker-compose run --rm --no-deps --entrypoint python nesti-orchestrator scripts/index_skills.py
```

The seven `memory_*` MCP tools expose the same stores.

---

## Frontend Testing

When the change touches the frontend in a repository with Vue, two extra layers
run (rules in [How it works](#how-it-works)):

| Layer | Image | Base | What it covers |
|-------|-------|------|----------------|
| Vitest + Vue Test Utils | `nesti-sandbox-node` | `node:22-alpine` | Component units: props, events, computed values, slots |
| Playwright | `nesti-sandbox-e2e` | `mcr.microsoft.com/playwright:v1.50.0-noble` + Node 22 | Full user flows in headless Chromium against `php artisan serve` on a migrated + seeded database |

The PHPUnit sandbox (`nesti-sandbox-php`) uses `php:8.3-cli` as its base.

**`@playwright/test` is pinned exactly `1.50.0`** — never with a caret. The pin
and the E2E image's base tag are one coupled setting; changing either without the
other breaks the layer.

`vitest.config.js` must exclude `e2e/**` so Vitest does not try to collect the
Playwright specs — Vitest's default include glob matches `e2e/*.spec.js` and
dies with a Playwright error. The Node sandbox CMD also passes
`--exclude 'e2e/**'`.

For Laravel, the E2E sandbox exports `APP_ENV=testing` and pins SQLite to the
recreated workspace `database/database.sqlite`. After Composer/config setup,
the image-owned `scripts/e2e_fixtures.php` runs migrations, default seeding and
declared fixture preparation. Only then do the build and browser tests run.
The helper refuses a declared model using another database before migrating
or seeding. Scope never controls data preparation.

Set `NESTI_STACK` to `php`, `vue`, or `fullstack` to pin the detection if your
repository layout misleads it; the default `auto` is right for most projects.

### Served-page integration

A component test does not prove the component is served. Follow the existing
route → Blade view → Vite entry → Vue root. For an in-DOM root, preserve
PrimeVue/Aura/plugins, register the feature before `app.mount('#app')`, and
place its explicit kebab-case tag in the served Blade view. An unused
`App.vue` is not a page. Preserve an existing SFC-root architecture.

## Fixture dependencies

An optional committed `e2e/nesti-fixtures.json` declares a hard nonempty
real-data prerequisite for an existing unauthenticated GET collection:

```json
{"version":1,"fixtures":[{"endpoint":"/api/tasks","model":"App\\Models\\Task","seeder":"Database\\Seeders\\TaskSeeder"}]}
```

The UTF-8 manifest is limited to 32 KiB and 16 unique requirements, with
exact fields and local `/api/...` paths. Empty states, mocked tests and specs
that create data through existing UI/API routes need no manifest. A retry
must re-emit a still-required manifest or deliberately emit `fixtures: []`;
normal stale-file pruning is unchanged.

The helper probes the real HTTP kernel after default seeding. A nonempty
collection is already satisfied; otherwise it requires an empty model table
and an endpoint SELECT on that table, then runs an existing declared seeder
once. Default-seeded rows are not duplicated. This is test setup, not a
silent change to production `DatabaseSeeder`.

Only a seeder whose class **and** conventional PHP file are absent can
produce exit 78 and a matching bounded atomic report at
`/nesti-results/fixtures.json`. The browser never started: the verdict is
`Playwright BLOCKED`, not FAILED or PASSED. Timeouts, HTTP/auth/JSON errors,
unconfirmed mapping, existing filtered-out rows, broken/no-op/throwing
seeders and unrelated seed errors remain ordinary failures.

For an unchanged HEAD-backed API/model and no coder-authored backend files,
Nesti saves trusted intent in GitLab, verifies `nesti::pause`, and creates
one English `Scope: backend` issue. Declare the applicable existing seeder,
or the conventional missing `<Model>Seeder` in JSON without adding or
registering a nonexistent class in the frontend parent. New backend work
must ship its own factory/seeder and uses the normal retry path instead.

Dependency truth is the latest non-system
`NESTI_FIXTURE_DEPENDENCIES_V1` note authored by the configured token's user
(`GET /user`). A canonical key binds project, parent IID, target branch and
requirement; the child carries `NESTI_FIXTURE_CHILD_V1` ownership metadata.
Redis history is not dependency state. Intent/submission/link/merge/release
writes are read back independently; foreign or malformed metadata cannot
release a parent, and stale writes are refused.

Every poll reconciles before selecting work. A closed child or an open MR is
not completion: an independently read related MR must start with exactly
`Closes #<child>`, be merged with `merged_at`, and target the recorded project
and configured `GITLAB_DEFAULT_BRANCH`. Only all merged items release the
parent; normal setup then claims it. No parent LLM/escalation/commit runs
while waiting. Later reconciliation never clears a released parent's live
lock or a later manual pause. A merged-but-still-unsatisfied requirement
blocks for an operator without opening a second child.

### Operator recovery

Stop the poller first (`docker-compose stop nesti-orchestrator`), restore
GitLab access and use the same automation identity. Notes, labels, issue
creation and related/detail MR reads must be permitted. A new token for the
same user is safe; changing users requires explicit migration of trusted
notes/child ownership, never a silent trust fallback.

- **Unknown child POST outcome:** enumerate all issues, including closed and
  unlabelled, and check trusted exact-key ownership markers. Reconcile one
  found child. Only after establishing no request remains in flight and no
  child exists may an operator read `get_fixture_state`, reset that item's
  `creation_submitted=false`, `state="creating"`, `reason=""`, and write it
  with `save_fixture_state`. The next poll makes one POST; elapsed time alone
  is not evidence that creation failed.
- **Blocked existing child corrected by a later MR:** explicitly set its
  item to `waiting` and clear its reason through the verified state methods.
  Normal MR merge verification still applies. Ambiguous ownership must be
  resolved before changing state.
- **Pause/stale lock with no durable record:** verify no child or open/merged
  closing MR exists, then use `resume_issue` and clear only that parent's
  conversation and episodes. Ordinary crash recovery refuses the hold;
  reconciliation cannot reconstruct evidence never saved.
- **Configured target changed:** keep the hold and explicitly migrate the
  record after reviewing the target/MR. Do not manually strip labels to
  bypass a durable record.

Use a one-off application container with `--entrypoint python` while the
poller is stopped; dependency mutations are deliberately not exposed by MCP.
Restart only after independently verifying the intended note and labels.


---

## Example Topology

| Service | Addr | Role |
|---------|------|------|
| GitLab | `https://gitlab.yourdomain.com` | Repository + merge requests + issue intake |
| Local LLM (optional) | your Ollama host | Local planner / coder tiers |
| Redis 8 | `nesti-redis:6379` | Conversation history, OAuth sessions, solution + episode cache |
| Qdrant | `nesti-qdrant:6333` | Long-term document memory (vector index) |
| Nesti MCP | stdio via `docker exec` | Tools for Claude Code / IDEs |
| DeepSeek API | `api.deepseek.com` | Mid-tier paid fallback |
| Claude (Sonnet) | `api.anthropic.com` | Last-resort fallback |

The optional local LLM tiers are disabled by default because they require dedicated strong GPU/hardware.

---

## Architecture

```
main.py                    <- CLI entry point (--loop / single-run)
task_engine.py             <- invokes the LangGraph pipeline
graph/
  state.py                 <- IssueState TypedDict
  tools.py                 <- atomic issue/GitLab/sandbox/skill/memory/quota functions
  nodes.py                 <- LangGraph nodes
  edges.py                 <- conditional routing, one router per test layer
  builder.py               <- compiled StateGraph
mcp_server/
  server.py                <- MCP stdio server (FastMCP), 25 tools
  tools/                   <- issues, GitLab, sandbox, skill, memory, quota MCP tools
  Dockerfile               <- standalone nesti-mcp container
conversation_store.py      <- Redis-backed per-issue message history
llm_client.py              <- provider cascade with multi-turn support
issue_scope.py             <- backend/frontend/fullstack scope of an issue + documentation-request check
e2e_fixtures.py            <- manifest, sandbox-report and durable dependency contracts
issue_dependencies.py      <- verified pause/child/merge/release workflow, no LLM
prompt_builder.py          <- scope-composed system + user prompts with a TASK SCOPE block
skill_loader.py            <- URL extraction + markdown fetching from issue text
skill_catalog.py           <- deterministic offline skill selection from vendored corpus
embedding.py               <- shared fastembed embedder for both memory tiers
vector_store.py            <- Qdrant document memory (long-term)
semantic_cache.py          <- Redis 8 solution cache + episodic memory (short-term)
gitlab_issues_client.py    <- issue intake and lifecycle (label-based locking)
gitlab_client.py           <- clone, branch, commit, push, MR
docker_runner.py           <- PHPUnit sandbox execution + FILE-block writing
frontend_runner.py         <- Vitest + Playwright sandbox execution
telegram_notifier.py       <- failure alerts (optional)
skills/                    <- vendored PrimeVue + Laravel documentation corpus
templates/laravel/         <- bootstrap templates (vite.config.js, routes, views, tests)
scripts/
  fetch_skills.py          <- regenerates the vendored corpus in skills/
  index_skills.py          <- chunks + embeds skills/ into Qdrant
  oauth.py                 <- `nesti` CLI: provider login / logout + /usage
  preflight.py             <- pre-run config + lifecycle + Docker verification
  seed_live_issues.py      <- creates demo issues with the opt-in label
  e2e_fixtures.php          <- image-owned isolated Laravel fixture preparation
test_graph_smoke.py        <- offline smoke tests for the LangGraph pipeline
test_live_laravel.py       <- opt-in integration tests (Docker + network)
```

Supporting files:
```
Dockerfile                 <- orchestrator container (Python 3.12-slim)
Dockerfile.sandbox         <- PHPUnit sandbox (php:8.3-cli + Composer)
Dockerfile.sandbox.node    <- Vitest sandbox (node:22-alpine)
Dockerfile.sandbox.e2e     <- Playwright sandbox (playwright:v1.50.0-noble + Node 22)
docker-compose.yml         <- nesti-orchestrator + nesti-redis + nesti-mcp + nesti-qdrant
.vscode/mcp.json.example   <- registers the nesti MCP server for VS Code Claude extension
.env / .env.example        <- all configuration (shared by orchestrator and MCP server)
ISSUE_GUIDELINE.md         <- how to write effective GitLab issues
```

---

## Installation

**1. Clone and configure**
```bash
cp .env.example .env
# Edit .env — at minimum: GITLAB_URL, GITLAB_TOKEN,
#   GITLAB_PROJECT_PATH, GITLAB_ISSUE_LABEL, plus an enabled API key
#   or a consumer subscription login.
```

**2. Build the sandbox images** (one per test layer)
```bash
docker build -t nesti-sandbox-php  -f Dockerfile.sandbox      .
docker build -t nesti-sandbox-node -f Dockerfile.sandbox.node .
docker build -t nesti-sandbox-e2e  -f Dockerfile.sandbox.e2e  .
```
Only `nesti-sandbox-php` is needed for backend-only projects; build the other
two to enable Vue.js testing.

**3. Verify the skill corpus**

The `skills/` directory ships committed. If you need to regenerate it:
```bash
python scripts/fetch_skills.py
```

**4. Run preflight checks**
```bash
python scripts/preflight.py
```
Verifies config, the GitLab Issues lifecycle (creates a throwaway probe issue
and drives lock → unlock → close), the GitLab repo, Anthropic, Redis
(warn-only), Docker + the three sandbox images, and the vendored corpus.

**5. Build, index, then start**
```bash
docker-compose build nesti-orchestrator nesti-mcp
docker-compose up -d nesti-redis nesti-qdrant
docker-compose run --rm --no-deps --entrypoint python nesti-orchestrator scripts/index_skills.py
docker-compose up --build -d
docker-compose logs -f nesti-orchestrator
```

This starts four containers: `nesti-orchestrator`, `nesti-redis`,
`nesti-mcp` and `nesti-qdrant`. Redis and Qdrant persist across restarts via
the named `nesti_redis_data` and `nesti_qdrant_data` volumes.

When a practice instruction changes, **index before starting the poller**:

```bash
docker-compose stop nesti-orchestrator
docker-compose build nesti-orchestrator nesti-mcp
docker-compose up -d nesti-redis nesti-qdrant
docker-compose run --rm --no-deps --entrypoint python nesti-orchestrator scripts/index_skills.py --only practices
docker-compose up --build -d
```

Verify `DocumentMemory.indexed_doc_hashes()["practices/frontend-design.md"]`
matches SHA-256 of the deployed file. An indexing failure with memory enabled
must not restart polling with stale instructions. Skip indexing only when
`NESTI_MEMORY_ENABLED=false` was already the operator's configuration.

**6. Connect the MCP server (optional)**
```bash
# Claude Code CLI:
claude mcp add nesti docker exec -i nesti-mcp python -m mcp_server.server

# Verify:
claude mcp list
```
VS Code users: the bundled `.vscode/mcp.json` registers the same server for
the Claude extension automatically.

---

## MCP Server

`nesti-mcp` exposes the public issue/GitLab/Docker/skill/memory/quota layer —
**25 tools** — over the Model Context Protocol (stdio transport).
Any MCP-compatible client — Claude Code CLI, VS Code Claude extension, Cursor —
can drive the same GitLab/Docker toolchain the orchestrator uses, e.g.:

```
@nesti issue_list_pending
@nesti detect_stack /tmp/ai-dev-241-xyz/repo
@nesti laravel_bootstrap /tmp/ai-dev-241-xyz/repo
@nesti docker_run_phpunit /tmp/ai-dev-241-xyz/repo
@nesti openapi_export /tmp/ai-dev-241-xyz/repo
@nesti docker_run_vitest /tmp/ai-dev-241-xyz/repo
@nesti docker_run_playwright /tmp/ai-dev-241-xyz/repo
@nesti skill_catalog_select "task management with DataTable"
```

The MCP server runs alongside the orchestrator; it does not replace it.
Every tool returns the uniform `{"success": bool, ...}` shape.
`docker_run_playwright` returns `{"passed", "output", "fixture_request"}`;
Vitest retains its tuple contract internally. The two dependency mutation
tools remain graph-internal, preserving the single polling writer.

Dependency: `mcp>=1.0.0,<2`. The MCP SDK renamed `FastMCP` to `MCPServer` in
2.x and changed the decorator API; the server stays on the 1.x line.

---

## Consumer Subscriptions & Quota

`scripts/oauth.py` is the container's `nesti` command. It logs consumer
subscriptions in and out (`nesti /provider login|logout <name>` for `claude`,
`antigravity`, `chatgpt-plus`, `copilot`) and shows their remaining quota:

```bash
docker exec -it nesti-orchestrator nesti /usage
```

```
Claude 7 Day
███░░░░░░░░░░░░░░░░░░░░░  89%  1d23h
Claude 5 Hour
██░░░░░░░░░░░░░░░░░░░░░░  90%  4h11m
Antigravity Gemini Pro
███████░░░░░░░░░░░░░░░░░  69%  6d2h
Antigravity Claude
░░░░░░░░░░░░░░░░░░░░░░░░ 100%  6d23h
```

The bar is the used share, the percentage what is left, the last column the
time until that window resets (coloured on a TTY unless `NO_COLOR` is set).

| Provider | Source | Shown |
|----------|--------|-------|
| `claude` | `api.anthropic.com/api/oauth/usage` | 7 Day, 5 Hour (+ Sonnet / Opus weekly when the plan has them) |
| `antigravity` | Cloud Code `v1internal:fetchAvailableModels` (`User-Agent: antigravity`) | Gemini Pro, Gemini Flash, Claude, GPT-OSS — agent-selectable models only |
| `copilot` | GitHub premium-request billing API | requests used this month; no remaining figure |
| `chatgpt-plus` | `chatgpt.com/backend-api/wham/usage` | 7 Day, 5 Hour (only returned windows) |

ChatGPT Plus inference uses the signed-in subscription through the Codex backend,
with `NESTI_CHATGPT_MODEL=gpt-6.1-sol`. Its usage endpoint is internal, not a
stable public API; missing quota windows remain unknown rather than guessed.

Every read goes through `fetch_usage()`: an access token near expiry is renewed
and saved to Redis *before* the usage call. Anthropic rotates the refresh token
and revokes the old access token on each renewal, so an unsaved renewal logs the
subscription out. The pipeline reads the same numbers (`tool_quota_check`, MCP
`quota_check`) on every test-layer failure and sends a Telegram warning when the
most depleted window drops below 10 %.

---

## Configuration

See `.env.example` for all variables. Key ones:

| Variable | Required | Default |
|----------|----------|---------|
| `DEEPSEEK_API_ENABLED` | No | `true` |
| `DEEPSEEK_API_KEY` | When DeepSeek API is enabled | — |
| `ANTHROPIC_API_ENABLED` | No | `false` |
| `ANTHROPIC_API_KEY` | When Anthropic API is enabled | — |
| `GITLAB_URL` + `GITLAB_TOKEN` | **Yes** | — |
| `GITLAB_PROJECT_PATH` | **Yes** | — |
| `GITLAB_ISSUE_LABEL` | No | `nesti` |
| `REDIS_URL` | No | `redis://nesti-redis:6379/0` |
| `NESTI_MEMORY_ENABLED` | No | `true` |
| `QDRANT_URL` | No | `http://nesti-qdrant:6333` |
| `HERMES3_LLM_ENABLED` | No | `false` |
| `HERMES3_LLM_URL` | No | — |
| `LOCAL_LLM_ENABLED` | No | `false` |
| `LOCAL_LLM_URL` | No | — |
| `MAX_CODE_RETRIES` | No | `2` |
| `NESTI_LARAVEL_VERSION` | No | `^13.0` |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | No | — |
| `DOCKER_SANDBOX_PHP_IMAGE` | No | `nesti-sandbox-php` |
| `DOCKER_SANDBOX_NODE_IMAGE` | No | `nesti-sandbox-node` |
| `DOCKER_SANDBOX_E2E_IMAGE` | No | `nesti-sandbox-e2e` |
| `DOCKER_SANDBOX_TIMEOUT` | No | `900` |
| `DOCKER_SANDBOX_BOOTSTRAP_TIMEOUT` | No | `1800` |
| `NESTI_STACK` | No | `auto` |
| `INCLUDE_SKILLS_IN_CODE_PROMPT` | No | `0` |

Paid API clients require both their enable flag and an API key. A false flag
prevents planner, coder, escalation and fallback calls even when the key is
present; availability is checked before each attempt. Anthropic's billed API
is opt-in and does not control a Claude consumer subscription.
`NESTI_CONSUMER_PRIORITY` selects the consumer providers independently. To use
only ChatGPT Plus with DeepSeek fallback, set it to `chatgpt-plus`, keep both
local-model flags false, enable DeepSeek and disable Anthropic. Editing `.env`
changes the next container's configuration, not an already-running process.

---

## Verification

**Offline smoke tests** (no Docker, no network):
```bash
python test_graph_smoke.py
# Behavior regressions: graph gates, fixture protocol, durable recovery and target checkout
```

**Live integration tests** (needs Docker + network):
```bash
python test_live_laravel.py
# Includes the real empty/seeded/missing/broken fixture matrix, SQLite isolation,
# real-page row matching, and existing PHP/OpenAPI/Vitest gates.
```

---

## License

MIT
