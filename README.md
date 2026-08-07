# Nesti — autonomous developer

## Goal

A self-contained orchestrator that reads Redmine issues, generates code through
a cascading LLM pipeline, validates it in a Docker sandbox, and opens GitLab
Merge Requests

---

## How it works

```
Redmine issue
  → fetch skill docs from URLs in issue (optional)
  → generate plan       [Hermes-3 → DeepSeek → Claude Sonnet]
  → generate code       [Qwen3 → DeepSeek → Claude Sonnet]
  → detect stack        [php | vue | fullstack]
  → run the applicable test layers, in order, each in its own container:
        PHPUnit  →  Vitest  →  Playwright
  → pass: commit + push + GitLab MR + close issue
  → fail: escalate provider, retry (up to MAX_CODE_RETRIES)
  → all retries exhausted: reopen issue with failure note
```

Stack detection is automatic — the issue never declares it. A backend change
runs PHPUnit only; a **frontend-only change skips PHPUnit entirely** and runs
Vitest and Playwright; a change touching both runs all three. Not every website
task has a backend part, so Vue-only issues are ordinary work here.

Conversation history is stored in Redis per issue. When tests fail and the
pipeline retries, the model sees its previous attempt and the failure output.

---

## Example Topology

| Service         | Addr                            | Role                              |
|-----------------|---------------------------------|-----------------------------------|
| GitLab          | `https://gitlab.yourdomain.com` | Repository + merge requests       |
| Redmine         | `192.168.100.1:3000`            | Issue intake                      |
| Qwen3:30b       | `192.168.100.2:11434`           | Primary coder (optional, local)   |
| MariaDB         | `192.168.100.3:3306`            | Schema reference (read-only)      |
| Hermes-3        | `192.168.100.4:11434`           | Primary planner (optional, local) |
| Redis           | `nesti-redis:6379`              | Conversation history              |
| Nesti MCP       | stdio via `docker exec`         | Tools for Claude Code / IDEs      |
| DeepSeek API    | `api.deepseek.com`              | Mid-tier paid fallback            |
| Claude (Sonnet) | `api.anthropic.com`             | Last-resort fallback              |

Local LLM providers (Hermes-3, Qwen3) are disable by default (`HERMES3_LLM_ENABLED=false`, `LOCAL_LLM_ENABLED=false`) as they require dedicated strong GPU/hardware.

---

## Installation

**1. Clone and configure**
```bash
cp .env.example .env
# Edit .env — at minimum: ANTHROPIC_API_KEY, REDMINE_*, GITLAB_*
```

**2. Build the sandbox images** (one per test layer)
```bash
docker build -t nesti-sandbox-php  -f Dockerfile.sandbox      .
docker build -t nesti-sandbox-node -f Dockerfile.sandbox.node .
docker build -t nesti-sandbox-e2e  -f Dockerfile.sandbox.e2e  .
```
Only `nesti-sandbox-php` is needed for backend-only projects; build the other
two to enable Vue.js testing.

**3. Start**
```bash
docker-compose up --build -d
docker-compose logs -f nesti-orchestrator
```

This starts three containers: `nesti-orchestrator`, `nesti-redis`, and
`nesti-mcp`. Redis starts automatically as a dependency and persists
conversation history across restarts via the named `nesti_redis_data` volume.

**4. Connect the MCP server (optional)**
```bash
# Claude Code CLI:
claude mcp add nesti docker exec -i nesti-mcp python -m mcp_server.server

# Verify:
claude mcp list
```
VS Code users: the bundled `.vscode/mcp.json` registers the same server for
the Claude extension automatically.

---

## Skill Documentation

Any HTTP/HTTPS URL in a Redmine issue subject or description is fetched
automatically and injected into the planning prompt as context.

See [`ISSUE_GUIDELINE.md`](ISSUE_GUIDELINE.md) for full issue
format and examples.

---

## Architecture

```
main.py                    ← CLI entry point (--loop / single-run)
task_engine.py             ← invokes the LangGraph pipeline
graph/
  state.py                 ← IssueState TypedDict
  tools.py                 ← atomic tool functions (Redmine, GitLab, sandboxes)
  nodes.py                 ← LangGraph nodes
  edges.py                 ← conditional routing, one router per test layer
  builder.py               ← compiled StateGraph
mcp_server/
  server.py                ← MCP stdio server (FastMCP), Phase 3
  tools/                   ← Redmine, GitLab, sandbox, skill MCP tools
  Dockerfile               ← standalone nesti-mcp container
conversation_store.py      ← Redis-backed per-issue message history
llm_client.py              ← provider cascade with multi-turn support
prompt_builder.py          ← system + user prompt construction
skill_loader.py            ← URL extraction + markdown fetching
redmine_client.py          ← issue intake and status management
gitlab_client.py           ← clone, branch, commit, push, MR
docker_runner.py           ← PHPUnit sandbox execution + FILE-block writing
frontend_runner.py         ← Vitest + Playwright sandbox execution
telegram_notifier.py       ← failure alerts (optional)
```

---

## Frontend Testing

When generated code contains `.vue` files, two extra layers run automatically:

| Layer | Image | What it covers |
|-------|-------|----------------|
| Vitest + Vue Test Utils | `nesti-sandbox-node` | Component units: props, events, computed values, slots |
| Playwright | `nesti-sandbox-e2e` | Full user flows in headless Chromium |

The generated `package.json` must include `vitest`, `@vue/test-utils`,
`@vitejs/plugin-vue`, and `@playwright/test` as dev dependencies plus `test`,
`build`, and `preview` scripts — the coding prompt enforces this. Component
tests go in `__tests__/`, E2E specs in `e2e/`.

Two constraints are easy to miss when editing these images by hand:
`@playwright/test` is pinned **exactly** (a caret resolves past the browsers
baked into `nesti-sandbox-e2e`), and `vitest.config.js` must exclude `e2e/**`
so Vitest does not try to collect the Playwright specs.

Set `NESTI_STACK` to `php`, `vue`, or `fullstack` to pin the detection if your
repository layout misleads it; the default `auto` is right for most projects.

---

## MCP Server (Phase 3)

`nesti-mcp` exposes all twelve `graph/tools.py` functions plus an extra skill
tool over the Model Context Protocol (stdio transport) — 13 tools in total. Any
MCP-compatible client — Claude Code CLI, VS Code Claude extension, Cursor — can
drive the same Redmine/GitLab/Docker toolchain the orchestrator uses, e.g.:

```
@nesti redmine_list_pending
@nesti detect_stack /tmp/ai-dev-241-xyz/repo
@nesti docker_run_phpunit /tmp/ai-dev-241-xyz/repo
@nesti docker_run_vitest /tmp/ai-dev-241-xyz/repo
@nesti docker_run_playwright /tmp/ai-dev-241-xyz/repo
```

The MCP server runs alongside the orchestrator; it does not replace it.
Every tool returns the uniform `{"success": bool, ...}` shape.

---

## Configuration

See `.env.example` for all variables. Key ones:

| Variable | Required | Default |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | **Yes** | — |
| `DEEPSEEK_API_KEY` | Recommended | — |
| `REDMINE_URL` + `REDMINE_API_KEY` | **Yes** | — |
| `GITLAB_URL` + `GITLAB_TOKEN` | **Yes** | — |
| `REDIS_URL` | No | `redis://nesti-redis:6379/0` |
| `HERMES3_LLM_URL` | No | — |
| `LOCAL_LLM_URL` | No | — |
| `MAX_CODE_RETRIES` | No | `2` |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | No | — |
| `DOCKER_SANDBOX_PHP_IMAGE` | No | `nesti-sandbox-php` |
| `DOCKER_SANDBOX_NODE_IMAGE` | No | `nesti-sandbox-node` |
| `DOCKER_SANDBOX_E2E_IMAGE` | No | `nesti-sandbox-e2e` |
| `DOCKER_SANDBOX_TIMEOUT` | No | `180` |
| `NESTI_STACK` | No | `auto` |

---

## License

MIT
