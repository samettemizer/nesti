"""
graph/state.py – the state object that flows through every LangGraph node.

Design notes
────────────
• ``total=False`` makes every key optional, which is how a TypedDict expresses
  "every field has a default": nodes can be unit-tested with a partial state
  and must read optional fields via ``state.get(...)``.  TaskEngine always
  supplies the full initial state at runtime.

• ``messages`` deliberately does NOT use LangGraph's ``add_messages`` reducer.
  ConversationStore (Phase 1) is the source of truth for the per-issue
  history: every node that touches the conversation calls the store and
  returns the *complete* updated list.  Plain last-write-wins replacement is
  therefore the correct merge semantic — an append-reducer would duplicate
  every turn on each node update.

• ``files_written`` is a small extension over the Phase 2 spec: node_code
  records whether the LLM response contained parseable ``### FILE:`` blocks.
  Without it, a response with no FILE blocks would send an untouched clone
  into the sandbox, the baseline test suite would pass, and the pipeline
  would open an empty "successful" Merge Request.  node_test short-circuits
  to a failure when this flag is False, preserving the Phase 1
  no-FILE-blocks retry-with-feedback behaviour.

• ``run_phpunit`` (Phase 4) is stored next to the descriptive ``stack`` label
  because the two answer different questions.  ``stack`` says what the code
  *is*; ``run_phpunit`` says whether the backend layer can be executed at all.
  A frontend-only repository has no composer.json, so forcing the PHP layer on
  it would fail every attempt and end in permanent failure — keeping the flag
  explicit is what makes Vue-only issues reachable.

• The Phase 5 flags follow the same "descriptive label vs. routing gate"
  split.  ``is_laravel`` says what the repository *is*; ``run_openapi`` says
  whether the OpenAPI layer applies to *this attempt* — it needs a Laravel
  app, a routes/api.php, and a code change that actually touched the API
  surface.  ``written_files`` exists to answer that last question: without the
  repo-relative paths from the previous node_code run, every attempt would
  re-export the document even for a pure CSS change.
"""

from typing import TypedDict


class IssueState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    issue: dict                        # normalised GitLab issue (id/subject/description)
    issue_id: int
    subject: str

    # ── Derived in nodes ───────────────────────────────────────────────────
    skills: list                       # Skill objects from skill_loader
    plan: str                          # planner output
    code_response: str                 # latest coder output
    repo_path: str                     # local clone path
    branch_name: str                   # git branch
    workspace: str                     # tempdir path

    # ── Conversation ───────────────────────────────────────────────────────
    messages: list[dict]               # growing per-issue history (from ConversationStore)

    # ── Stack detection (Phase 4) ──────────────────────────────────────────
    has_vue_files: bool                # True if the workspace contains .vue files
    stack: str                         # "php" | "vue" | "fullstack" | "unknown"
    run_phpunit: bool                  # False only for the "vue" stack

    # ── Laravel detection / bootstrap (Phase 5) ────────────────────────────
    is_laravel: bool                   # repository contains artisan
    bootstrapped: bool                 # True when this run scaffolded the skeleton
    has_api_routes: bool               # routes/api.php exists
    run_openapi: bool                  # OpenAPI layer applies to this attempt

    # ── Test / retry state ─────────────────────────────────────────────────
    attempt: int                       # current attempt index (incremented by node_code)
    max_attempts: int                  # from MAX_CODE_RETRIES + 1
    files_written: bool                # True if the last code response yielded FILE blocks
    written_files: list[str]           # repo-relative paths written by the last node_code
    test_output: str                   # last PHPUnit output
    test_passed: bool

    # ── OpenAPI layer results (Phase 5) ────────────────────────────────────
    openapi_passed: bool
    openapi_output: str
    openapi_paths: list[str]           # paths present in the exported document

    # ── Frontend test results (Phase 4) ────────────────────────────────────
    vitest_passed: bool
    vitest_output: str
    playwright_passed: bool
    playwright_output: str

    # ── Terminal flags ─────────────────────────────────────────────────────
    mr_url: str                        # set when MR is opened
    failure_reason: str                # set when all attempts exhausted
    error: str                         # set on unexpected exception
