"""
semantic_cache.py – Redis-backed short-term vector memory (Phase 8).

Two vector indices on Redis 8's built-in query engine (``FT.CREATE``):

* **Solution cache** (``nesti_solution_idx``, keys ``nesti:memory:solution:<iid>``)
  One row per successfully merged issue: subject, stack, MR URL and the plan
  that produced it.  Written by ``node_commit``, read by ``node_plan`` —
  tomorrow's issue sees how a similar one was solved yesterday.
  TTL ``NESTI_SOLUTION_TTL_DAYS`` (default 90).

* **Episodic memory** (``nesti_episode_idx``, keys
  ``nesti:memory:episode:<iid>:<attempt>:<layer>``)
  One row per failed attempt of the issue in flight.  Written by
  ``node_on_layer_failure``, read by ``node_code``.  The attempt that just
  failed is already verbatim in the conversation history, so recall returns
  only the *older* attempts.  TTL ``CONVERSATION_TTL_DAYS``; dropped with
  the conversation when the issue finishes.

Both indices embed through ``embedding.get_embedder()``, the same model as the
Qdrant document memory.

Resilience:
    Nothing here raises.  Redis unreachable, a pre-8 Redis without the query
    engine, or an unavailable embedder all make ``available`` False; reads
    then return ``[]`` and writes return ``False``.  Each cause is logged once.
"""

import array
import logging
import os
import re
import time

import redis
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.query import Query

try:  # redis-py >= 6 renamed the module; 5.x only ships the camel-case name.
    from redis.commands.search.index_definition import IndexDefinition, IndexType
except ImportError:  # pragma: no cover - depends on the installed redis-py
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from conversation_store import ConversationStore
from embedding import get_embedder
from layer_output import condense

logger = logging.getLogger(__name__)

SOLUTION_INDEX: str = "nesti_solution_idx"
SOLUTION_PREFIX: str = "nesti:memory:solution:"
EPISODE_INDEX: str = "nesti_episode_idx"
EPISODE_PREFIX: str = "nesti:memory:episode:"
_PLAN_STORE_LIMIT: int = 6_000      # chars of plan persisted per solution
_EPISODE_OUTPUT_LIMIT: int = 1_200  # chars of *condensed* layer output persisted

_DEFAULT_REDIS_URL = "redis://nesti-redis:6379/0"
_SOCKET_CONNECT_TIMEOUT = 3  # seconds, same as ConversationStore
_DEFAULT_SOLUTION_TTL_DAYS = 90
_DEFAULT_SOLUTION_MIN_SCORE = 0.80
_DEFAULT_EPISODE_MIN_SCORE = 0.60
_KNN_LIMIT_CAP = 10

_SOLUTION_FIELDS = ("issue_id", "subject", "plan", "mr_url", "stack", "score")
_EPISODE_FIELDS = ("issue_id", "attempt", "layer", "summary", "score")


def _s(value) -> str:
    """Decode a Redis reply field (bytes under decode_responses=False)."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return "" if value is None else str(value)


def _to_blob(vector: list[float]) -> bytes:
    """FLOAT32 little-endian bytes, the layout the Redis VECTOR field expects."""
    return array.array("f", vector).tobytes()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, str(default))
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid %s=%r – using default %s.", name, raw, default)
        return default


def _solution_ttl_seconds() -> int:
    raw = os.environ.get("NESTI_SOLUTION_TTL_DAYS", str(_DEFAULT_SOLUTION_TTL_DAYS))
    try:
        days = int(raw)
    except ValueError:
        logger.warning(
            "Invalid NESTI_SOLUTION_TTL_DAYS=%r – using default of %d day(s).",
            raw,
            _DEFAULT_SOLUTION_TTL_DAYS,
        )
        days = _DEFAULT_SOLUTION_TTL_DAYS
    return max(days, 1) * 86_400


def _layer_slug(layer: str) -> str:
    """``"Playwright (E2E tests)"`` → ``"playwright-e2e-tests"``."""
    return re.sub(r"[^a-z0-9]+", "-", (layer or "unknown").lower()).strip("-") or "unknown"


class SemanticMemory:
    """Solution cache + episodic memory on Redis 8's vector search."""

    def __init__(self) -> None:
        self._url: str = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        self._ok: bool = False
        self._engine: bool = False
        self._redis = None

        embedder = get_embedder()
        if not embedder.enabled:
            logger.info("Semantic memory disabled (NESTI_MEMORY_ENABLED=false).")
            return

        try:
            # Its own connection: ConversationStore decodes every reply as UTF-8,
            # which is the wrong contract for a store that holds binary vectors.
            self._redis = redis.from_url(
                self._url,
                decode_responses=False,
                socket_connect_timeout=_SOCKET_CONNECT_TIMEOUT,
            )
            self._redis.ping()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Semantic memory: Redis unavailable (%s): %s – solution cache and "
                "episodic memory disabled.",
                self._url,
                exc,
            )
            self._redis = None
            return

        self._ok = self._ensure_indices()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when Redis has the query engine, both indices exist and embedding works."""
        return self._ok and get_embedder().available

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Availability plus document counts; a count is ``None`` when unreadable."""
        return {
            "available": self.available,
            "url": self._url,
            "solutions": self._num_docs(SOLUTION_INDEX),
            "episodes": self._num_docs(EPISODE_INDEX),
            "engine": "redis-query-engine" if self._engine else "unavailable",
        }

    # ------------------------------------------------------------------
    # Solution cache
    # ------------------------------------------------------------------

    def remember_solution(
        self,
        issue_id: int,
        subject: str,
        description: str,
        plan: str,
        stack: str,
        mr_url: str,
    ) -> bool:
        """Store (or overwrite) the solution of one merged issue."""
        if not self.available:
            return False
        try:
            vector = get_embedder().embed_documents([f"{subject}\n{description}"])
            if not vector:
                return False
            key = f"{SOLUTION_PREFIX}{issue_id}"
            pipe = self._redis.pipeline(transaction=True)
            pipe.hset(
                key,
                mapping={
                    "issue_id": int(issue_id),
                    "subject": subject or "",
                    "stack": stack or "unknown",
                    "mr_url": mr_url or "",
                    "plan": (plan or "")[:_PLAN_STORE_LIMIT],
                    "created_at": int(time.time()),
                    "embedding": _to_blob(vector[0]),
                },
            )
            pipe.expire(key, _solution_ttl_seconds())
            pipe.execute()
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to store solution for issue #%s: %s", issue_id, exc)
            return False

    def find_similar_solutions(self, text: str, limit: int = 2) -> list[dict]:
        """Merged issues similar to *text*, most similar first, above the score floor."""
        if not text or not text.strip() or limit <= 0 or not self.available:
            return []
        rows = self._knn(SOLUTION_INDEX, "*", text, limit, _SOLUTION_FIELDS)
        floor = _env_float("NESTI_SOLUTION_MIN_SCORE", _DEFAULT_SOLUTION_MIN_SCORE)
        results: list[dict] = []
        for doc, similarity in rows:
            if similarity < floor:
                continue
            results.append(
                {
                    "issue_id": int(float(_s(getattr(doc, "issue_id", 0)) or 0)),
                    "subject": _s(getattr(doc, "subject", "")),
                    "plan": _s(getattr(doc, "plan", "")),
                    "mr_url": _s(getattr(doc, "mr_url", "")),
                    "stack": _s(getattr(doc, "stack", "")),
                    "similarity": round(similarity, 3),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Episodic memory
    # ------------------------------------------------------------------

    def remember_failure(self, issue_id: int, attempt: int, layer: str, output: str) -> bool:
        """Store one failed attempt of *issue_id* (condensed layer output)."""
        if not self.available:
            return False
        try:
            summary = condense(output or "", _EPISODE_OUTPUT_LIMIT)
            vector = get_embedder().embed_documents([f"{layer} failure: {summary}"])
            if not vector:
                return False
            key = f"{EPISODE_PREFIX}{issue_id}:{attempt}:{_layer_slug(layer)}"
            pipe = self._redis.pipeline(transaction=True)
            pipe.hset(
                key,
                mapping={
                    "issue_id": int(issue_id),
                    "attempt": int(attempt),
                    "layer": layer or "unknown",
                    "summary": summary,
                    "created_at": int(time.time()),
                    "embedding": _to_blob(vector[0]),
                },
            )
            pipe.expire(key, ConversationStore._resolve_ttl_seconds())
            pipe.execute()
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to store episodic memory for issue #%s attempt %s: %s",
                issue_id,
                attempt,
                exc,
            )
            return False

    def recall_failures(
        self, issue_id: int, text: str, attempt: int, limit: int = 2
    ) -> list[dict]:
        """
        Older failed attempts of *issue_id* similar to *text*.

        ``attempt`` is the attempt ABOUT to run.  Attempt ``attempt - 1`` just
        failed and its output is already verbatim in the conversation history
        (``ConversationStore.append_test_failure``), so only attempts up to
        ``attempt - 2`` are searched; before attempt 3 there is nothing older.
        """
        if attempt <= 2 or not text or not text.strip() or limit <= 0:
            return []
        if not self.available:
            return []
        issue = int(issue_id)
        prefilter = f"(@issue_id:[{issue} {issue}] @attempt:[-inf {int(attempt) - 2}])"
        rows = self._knn(EPISODE_INDEX, prefilter, text, limit, _EPISODE_FIELDS)
        floor = _env_float("NESTI_EPISODE_MIN_SCORE", _DEFAULT_EPISODE_MIN_SCORE)
        results: list[dict] = []
        for doc, similarity in rows:
            if similarity < floor:
                continue
            results.append(
                {
                    "issue_id": int(float(_s(getattr(doc, "issue_id", 0)) or 0)),
                    "attempt": int(float(_s(getattr(doc, "attempt", 0)) or 0)),
                    "layer": _s(getattr(doc, "layer", "")),
                    "summary": _s(getattr(doc, "summary", "")),
                    "similarity": round(similarity, 3),
                }
            )
        return results

    def forget_episodes(self, issue_id: int) -> int:
        """Delete every episode of *issue_id*; return how many were removed."""
        if self._redis is None or not self._ok:
            return 0
        try:
            # Issue-scoped pattern bounded by max_attempts × 4 layers: a handful
            # of keys, never a database-wide scan in practice.
            keys = self._redis.keys(f"{EPISODE_PREFIX}{int(issue_id)}:*")
            return int(self._redis.delete(*keys)) if keys else 0
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to forget episodes for issue #%s: %s", issue_id, exc)
            return 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_indices(self) -> bool:
        """Create both indices; ``Index already exists`` counts as success."""
        try:
            schemas = self._index_schemas(get_embedder().dim)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Semantic memory schema could not be built: %s", exc)
            return False
        for name, prefix, fields in schemas:
            try:
                self._redis.ft(name).create_index(
                    fields,
                    definition=IndexDefinition(prefix=[prefix], index_type=IndexType.HASH),
                )
            except redis.exceptions.ResponseError as exc:
                message = str(exc).lower()
                if "index already exists" in message:
                    continue
                if "unknown command" in message:
                    logger.warning(
                        "Redis at %s has no query engine (FT.CREATE) – semantic memory "
                        "disabled. Redis 8+ is required; docker-compose.yml ships "
                        "redis:8-alpine.",
                        self._url,
                    )
                    return False
                logger.warning("Semantic memory index %s could not be created: %s", name, exc)
                return False
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Semantic memory index %s could not be created: %s", name, exc)
                return False
        self._engine = True
        logger.info(
            "Semantic memory ready on %s (indices %s, %s; %d dims).",
            self._url,
            SOLUTION_INDEX,
            EPISODE_INDEX,
            get_embedder().dim,
        )
        return True

    @staticmethod
    def _index_schemas(dim: int) -> tuple:
        """
        ``(index, key prefix, fields)`` for both indices.

        Only filterable fields are declared.  ``mr_url``, ``plan`` and
        ``summary`` are stored in the same hash and returned by ``RETURN``
        without being indexed — redis-py refuses a non-indexed, non-sortable
        schema field outright.
        """
        vector = VectorField(
            "embedding",
            "FLAT",  # hundreds of rows at most: a flat scan is exact and cheapest
            {"TYPE": "FLOAT32", "DIM": dim, "DISTANCE_METRIC": "COSINE"},
        )
        return (
            (
                SOLUTION_INDEX,
                SOLUTION_PREFIX,
                (
                    NumericField("issue_id"),
                    TextField("subject"),
                    TagField("stack"),
                    NumericField("created_at"),
                    vector,
                ),
            ),
            (
                EPISODE_INDEX,
                EPISODE_PREFIX,
                (
                    NumericField("issue_id"),
                    NumericField("attempt"),
                    TagField("layer"),
                    NumericField("created_at"),
                    vector,
                ),
            ),
        )

    def _knn(
        self, index: str, prefilter: str, text: str, limit: int, fields: tuple[str, ...]
    ) -> list[tuple[object, float]]:
        """Run one KNN query; return ``(doc, cosine similarity)`` pairs, best first."""
        vector = get_embedder().embed_query(text)
        if not vector:
            return []
        k = max(1, min(int(limit), _KNN_LIMIT_CAP))
        try:
            query = (
                Query(f"{prefilter}=>[KNN {k} @embedding $vec AS score]")
                .sort_by("score")  # ascending distance = most similar first
                .return_fields(*fields)
                .paging(0, k)
                .dialect(2)
            )
            result = self._redis.ft(index).search(
                query, query_params={"vec": _to_blob(vector)}
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Semantic memory query on %s failed: %s", index, exc)
            return []
        rows: list[tuple[object, float]] = []
        for doc in result.docs:
            try:
                # Redis reports COSINE *distance*; similarity is its complement.
                similarity = 1.0 - float(_s(getattr(doc, "score", "1")))
            except ValueError:
                continue
            rows.append((doc, similarity))
        return rows

    def _num_docs(self, index: str) -> int | None:
        if self._redis is None or not self._engine:
            return None
        try:
            info = self._redis.ft(index).info()
            return int(float(_s(info.get("num_docs"))))
        except Exception:  # pylint: disable=broad-except
            return None


_SEMANTIC_MEMORY: SemanticMemory | None = None


def get_semantic_memory() -> SemanticMemory:
    """Return the process-wide SemanticMemory, constructing it on first use."""
    global _SEMANTIC_MEMORY
    if _SEMANTIC_MEMORY is None:
        _SEMANTIC_MEMORY = SemanticMemory()
    return _SEMANTIC_MEMORY
