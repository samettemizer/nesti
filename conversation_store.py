"""
conversation_store.py – Redis-backed per-issue conversation history.

Key schema:
    ai-dev:issue:{issue_id}:messages  →  JSON list of {"role": ..., "content": ...}

TTL: CONVERSATION_TTL_DAYS (default 7). Reset on every write so active
issues never expire mid-flight.

Resilience:
    If Redis is unreachable at init time the store degrades gracefully to an
    in-memory dict, so the orchestrator keeps working in a stateless-ish mode
    (history survives within a single process run, but not across restarts).
    Every individual operation is also wrapped defensively: a Redis hiccup
    mid-run is logged and swallowed rather than crashing the pipeline.
"""

import json
import logging
import os

import redis

logger = logging.getLogger(__name__)

_DEFAULT_REDIS_URL = "redis://ai-dev-redis:6379/0"
_DEFAULT_TTL_DAYS = 7
_SOCKET_CONNECT_TIMEOUT = 3  # seconds
_KEY_PREFIX = "ai-dev:issue:"
_TEST_FAILURE_OUTPUT_LIMIT = 2000  # chars of PHPUnit output fed back to the model


class ConversationStore:
    """
    Per-issue conversation history persisted in Redis, with an in-memory
    fallback when Redis cannot be reached.

    The public API always returns/accepts ``list[dict]`` message lists of the
    form ``[{"role": "user" | "assistant", "content": "..."}]`` and never
    raises – callers can treat it as fire-safe.
    """

    def __init__(self) -> None:
        redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        self._ttl_seconds: int = self._resolve_ttl_seconds()

        # Always present so the in-memory path can never hit AttributeError,
        # even if we later flip _available.
        self._memory: dict[str, str] = {}

        try:
            self._redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=_SOCKET_CONNECT_TIMEOUT,
            )
            self._redis.ping()
            self._available = True
            logger.info(
                "ConversationStore connected to Redis (%s); TTL=%d day(s).",
                redis_url,
                self._ttl_seconds // 86_400,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Redis unavailable (%s) – falling back to in-memory store. "
                "Conversation history will NOT survive restarts (degraded mode).",
                exc,
            )
            self._redis = None
            self._available = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when a live Redis connection backs the store."""
        return self._available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, issue_id: int) -> list[dict]:
        """Return the stored message list, or [] if no history exists."""
        key = self._key(issue_id)
        try:
            raw = self._redis.get(key) if self._available else self._memory.get(key)
            if not raw:
                return []
            messages = json.loads(raw)
            if not isinstance(messages, list):
                logger.warning("Corrupt history at %s (not a list) – ignoring.", key)
                return []
            return messages
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to load history for issue #%s: %s", issue_id, exc)
            return []

    def save(self, issue_id: int, messages: list[dict]) -> None:
        """Persist the full message list. Resets TTL on every write."""
        key = self._key(issue_id)
        try:
            payload = json.dumps(messages, ensure_ascii=False)
            if self._available:
                self._redis.set(key, payload, ex=self._ttl_seconds)
            else:
                self._memory[key] = payload
            logger.debug(
                "Saved %d message(s) for issue #%s (%d chars).",
                len(messages),
                issue_id,
                len(payload),
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to save history for issue #%s: %s", issue_id, exc)

    def append(self, issue_id: int, role: str, content: str) -> list[dict]:
        """Append one message, persist, and return the updated list."""
        messages = self.load(issue_id)
        messages.append({"role": role, "content": content})
        self.save(issue_id, messages)
        logger.debug(
            "Appended '%s' turn to issue #%s (history now %d message(s)).",
            role,
            issue_id,
            len(messages),
        )
        return messages

    def append_test_failure(self, issue_id: int, test_output: str) -> list[dict]:
        """
        Append a user-role message describing the test failure.

        This is what makes the LLM aware of WHY the previous attempt failed:
        the corrective turn is added to the shared history so the next
        generate_code() call sees the prior attempt and its failure reason.
        """
        content = (
            "The code you generated was tested and the tests FAILED.\n"
            "Test output:\n"
            "---\n"
            f"{test_output[:_TEST_FAILURE_OUTPUT_LIMIT]}\n"
            "---\n"
            "Please analyse the failure, correct the implementation, and produce "
            "all affected files again using the FILE format."
        )
        return self.append(issue_id, "user", content)

    def delete(self, issue_id: int) -> None:
        """Remove the conversation. Called after a successful MR or permanent failure."""
        key = self._key(issue_id)
        try:
            if self._available:
                self._redis.delete(key)
            else:
                self._memory.pop(key, None)
            logger.debug("Deleted conversation history for issue #%s.", issue_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to delete history for issue #%s: %s", issue_id, exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _key(self, issue_id: int) -> str:
        return f"{_KEY_PREFIX}{issue_id}:messages"

    @staticmethod
    def _resolve_ttl_seconds() -> int:
        """Read CONVERSATION_TTL_DAYS from env, clamped to at least one day."""
        raw = os.environ.get("CONVERSATION_TTL_DAYS", str(_DEFAULT_TTL_DAYS))
        try:
            days = int(raw)
        except ValueError:
            logger.warning(
                "Invalid CONVERSATION_TTL_DAYS=%r – using default of %d day(s).",
                raw,
                _DEFAULT_TTL_DAYS,
            )
            days = _DEFAULT_TTL_DAYS
        return max(days, 1) * 86_400
