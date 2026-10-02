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
  → bootstrap             scaffold or top-up the Laravel app
  → load skills            vendored corpus + URLs from the issue
  → generate plan          [Local LLM → DeepSeek → Claude Sonnet]
  → generate code          [Local LLM → DeepSeek → Claude Sonnet]
  → detect stack           [php | vue | fullstack]
  → run the applicable test layers, sequential gates:
        PHPUnit → OpenAPI → Vitest → Playwright
  → all green: commit + push + GitLab MR (body: Closes #<iid>) + close issue
  → red layer: escalate provider, retry (shared budget: MAX_CODE_RETRIES + 1)
  → all retries exhausted: remove lock label, comment failure, return to pending
```

Stack detection is automatic — the issue never declares it. A backend change
runs PHPUnit and the OpenAPI gate; a **frontend-only change skips PHPUnit
entirely** and runs Vitest and Playwright; a change touching both runs all four.
Vue-only issues are ordinary work.

Conversation history is stored in Redis per issue. When tests fail and the
pipeline retries, the model sees its previous attempt and the failure output.
Retries prune stale files: a file the previous attempt wrote and the new
attempt does not re-emit is deleted, so a renamed migration cannot leave two
`create_<table>_table` migrations behind.

---

## Issue Intake (GitLab Issues)

Intake is **opt-in by label**. Only open issues carrying the label configured
in `GITLAB_ISSUE_LABEL` (default `nesti`) are picked up.

GitLab issues have only `opened` and `closed`, so the three-state intake model
lives in labels:

| State       | Condition |
|-------------|-----------|
| **pending** | open, has `<label>`, does NOT have `<label>::in-progress` |
| **in progress** | open, has `<label>::in-progress` (the lock Nesti owns) |
| **done** | closed |

Scoped labels (the `::` form) are mutually exclusive within their scope in
GitLab, which is what makes the lock single-valued. Every mutation is verified
by reading the issue back; a lock or unlock that did not apply is a loud error.

**Success:** Nesti removes the lock label, closes the issue, and comments the
MR URL. The MR description starts with `Closes #<iid>`, so issue and MR are
natively cross-linked.

**Failure (retries exhausted):** Nesti removes the lock label and comments the
failure, returning the issue to the pending pool so it can be retried.

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

Generated **only** by `scripts/fetch_skills.py` and committed to the
repository. Never hand-edit a vendored document.

The practice tier is a hand-picked whitelist (`PRACTICE_SOURCES` in
`scripts/fetch_skills.py`) of cross-cutting engineering documents that shape
the code Nesti writes — test-driven development, application security, and
visual/UI direction. Each entry is flattened into one markdown file with a
Nesti front matter block and re-vendored offline from a local skill library:

```bash
python scripts/fetch_skills.py --only practices --practices-src ~/my-skills
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
| Long-term docs | Qdrant (`nesti-qdrant`, collection `nesti_docs`) | the `skills/` corpus, chunked and embedded | `scripts/index_skills.py` | `plan`, `code` (filtered by detected stack) |
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
corpus once after `docker-compose up` (and after `fetch_skills.py`); changing
the embedding model requires `--recreate`:

```bash
docker exec nesti-orchestrator python scripts/index_skills.py
```

The seven `memory_*` MCP tools expose the same stores.

---

## Frontend Testing

When generated code contains `.vue` files, two extra layers run automatically:

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

For a Laravel repo the E2E sandbox runs `composer install`, sets up the database
(`php artisan migrate --force --seed`), `npm run build`, then
`npx playwright test` with `php artisan serve` as the web server on
`http://127.0.0.1:8000`.

Set `NESTI_STACK` to `php`, `vue`, or `fullstack` to pin the detection if your
repository layout misleads it; the default `auto` is right for most projects.

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
  tools.py                 <- 24 atomic tool functions (issues, GitLab, sandboxes, skills, memory, quota)
  nodes.py                 <- LangGraph nodes
  edges.py                 <- conditional routing, one router per test layer
  builder.py               <- compiled StateGraph (14 nodes)
mcp_server/
  server.py                <- MCP stdio server (FastMCP), 25 tools
  tools/                   <- issues, GitLab, sandbox, skill, memory, quota MCP tools
  Dockerfile               <- standalone nesti-mcp container
conversation_store.py      <- Redis-backed per-issue message history
llm_client.py              <- provider cascade with multi-turn support
prompt_builder.py          <- system + user prompt construction (Laravel 13 + PrimeVue 5 role)
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
# Edit .env — at minimum: ANTHROPIC_API_KEY, GITLAB_URL, GITLAB_TOKEN,
#   GITLAB_PROJECT_PATH, GITLAB_ISSUE_LABEL
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

**5. Start**
```bash
docker-compose up --build -d
docker-compose logs -f nesti-orchestrator
```

This starts four containers: `nesti-orchestrator`, `nesti-redis`,
`nesti-mcp` and `nesti-qdrant`. Redis and Qdrant persist across restarts via
the named `nesti_redis_data` and `nesti_qdrant_data` volumes. Index the skill
corpus once afterwards (see [Hierarchical Vector Memory](#hierarchical-vector-memory)).

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

`nesti-mcp` exposes all 24 `graph/tools.py` functions plus one extra skill
tool over the Model Context Protocol (stdio transport) — **25 tools** in total.
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
| `chatgpt-plus` | — | `usage unknown`; no quota source is implemented |

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
| `ANTHROPIC_API_KEY` | **Yes** | — |
| `DEEPSEEK_API_KEY` | Recommended | — |
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

---

## Verification

**Offline smoke tests** (no Docker, no network):
```bash
python test_graph_smoke.py
# 318 checks — covers every node, every routing edge, the full state machine
```

**Live integration tests** (needs Docker + network):
```bash
python test_live_laravel.py
# Proves all 8 real-container steps: greenfield scaffold, migration,
# php artisan test green, openapi.json with /api/tasks, a deliberately
# undocumented route reported as undocumented, Vitest green, Playwright
# green against php artisan serve.
```

---

## License

MIT
