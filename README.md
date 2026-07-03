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
  → unit tests          [in Docker container]
  → pass: commit + push + GitLab MR + close issue
  → fail: escalate provider, retry (up to MAX_CODE_RETRIES)
  → all retries exhausted: reopen issue with failure note
```

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
| Redis           | `ai-dev-redis:6379`             | Conversation history              |
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

**2. Build the app sandbox image**
```bash
docker build -t hello-world-sandbox -f Dockerfile.sandbox .
```

**3. Start**
```bash
docker-compose up --build -d
docker-compose logs -f ai-developer
```

Redis starts automatically as a dependency and persists conversation history
across restarts via a named Docker volume.

---

## Skill Documentation

Any HTTP/HTTPS URL in a Redmine issue subject or description is fetched
automatically and injected into the planning prompt as context.

See [`REDMINE_ISSUE_GUIDELINE.md`](REDMINE_ISSUE_GUIDELINE.md) for full issue
format and examples.

---

## Architecture

```
main.py                    ← CLI entry point (--loop / single-run)
task_engine.py             ← invokes the LangGraph pipeline
graph/
  state.py                 ← IssueState TypedDict
  tools.py                 ← atomic tool functions (Redmine, GitLab, Docker)
  nodes.py                 ← LangGraph nodes
  edges.py                 ← conditional routing
  builder.py               ← compiled StateGraph
conversation_store.py      ← Redis-backed per-issue message history
llm_client.py              ← provider cascade with multi-turn support
prompt_builder.py          ← system + user prompt construction
skill_loader.py            ← URL extraction + markdown fetching
redmine_client.py          ← issue intake and status management
gitlab_client.py           ← clone, branch, commit, push, MR
docker_runner.py           ← Unit test sandbox execution
telegram_notifier.py       ← failure alerts (optional)
```

---

## Configuration

See `.env.example` for all variables. Key ones:

| Variable | Required | Default |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | **Yes** | — |
| `DEEPSEEK_API_KEY` | Recommended | — |
| `REDMINE_URL` + `REDMINE_API_KEY` | **Yes** | — |
| `GITLAB_URL` + `GITLAB_TOKEN` | **Yes** | — |
| `REDIS_URL` | No | `redis://ai-dev-redis:6379/0` |
| `HERMES3_LLM_URL` | No | — |
| `LOCAL_LLM_URL` | No | — |
| `MAX_CODE_RETRIES` | No | `2` |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | No | — |

---

## License

MIT
