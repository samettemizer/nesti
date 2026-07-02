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
"""

from typing import TypedDict


class IssueState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    issue: dict                        # raw Redmine issue dict
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

    # ── Test / retry state ─────────────────────────────────────────────────
    attempt: int                       # current attempt index (incremented by node_code)
    max_attempts: int                  # from MAX_CODE_RETRIES + 1
    files_written: bool                # True if the last code response yielded FILE blocks
    test_output: str                   # last PHPUnit output
    test_passed: bool

    # ── Terminal flags ─────────────────────────────────────────────────────
    mr_url: str                        # set when MR is opened
    failure_reason: str                # set when all attempts exhausted
    error: str                         # set on unexpected exception
