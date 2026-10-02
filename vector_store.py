"""
vector_store.py – Qdrant-backed long-term document memory (Phase 8).

The whole vendored ``skills/`` corpus is chunked and embedded once by
``scripts/index_skills.py`` into one Qdrant collection (default
``nesti_docs``).  At plan and code time ``DocumentMemory.search`` retrieves the
passages most similar to the issue, optionally narrowed by a ``stack`` payload
filter (``php`` → Laravel topics, ``vue`` → PrimeVue components).  The curated
practice corpus carries a third ``stack`` value (``practice``) and rides along
in every search on a hard-capped lane of its own, so cross-cutting guidance can
never displace the API documentation an issue actually needs.

This complements ``skill_catalog``: the catalog injects whole documents whose
alias/trigger appears literally in the issue text and truncates each at 7 000
chars; the vector index reaches past that cap and finds documents whose name
the issue never mentions.

Resilience:
    Nothing here raises.  A missing Qdrant, a missing collection or an
    unavailable embedder makes ``available`` False and ``search`` return
    ``[]``.  Availability is re-probed after a failure, so a Qdrant restart
    recovers without restarting the orchestrator.
"""

import logging
import os

from embedding import get_embedder

logger = logging.getLogger(__name__)

DOCS_COLLECTION_DEFAULT: str = "nesti_docs"
_DEFAULT_QDRANT_URL: str = "http://nesti-qdrant:6333"
_SEARCH_LIMIT_CAP: int = 20
_CLIENT_TIMEOUT: int = 10          # seconds
_SCROLL_PAGE: int = 512
_UPSERT_BATCH: int = 128
_FILTERABLE_STACKS: tuple[str, ...] = ("php", "vue")
PRACTICE_STACK: str = "practice"
# At most ``limit // _PRACTICE_SHARE`` practice chunks per search: the official
# documentation keeps three quarters of every result set.  The floor is what
# keeps the lane honest — below it the slots simply go unused.
_PRACTICE_SHARE: int = 4
_PRACTICE_MIN_SCORE: float = 0.70
_PAYLOAD_INDEX_FIELDS: tuple[str, ...] = ("stack", "source", "doc_path")


class DocumentMemory:
    """
    One Qdrant collection of embedded documentation chunks.

    Every chunk's payload carries ``doc_path``, ``doc_title``, ``doc_url``,
    ``doc_hash``, ``source``, ``stack``, ``version``, ``heading``,
    ``chunk_index`` and ``text``.
    """

    def __init__(self) -> None:
        self._url: str = os.environ.get("QDRANT_URL", _DEFAULT_QDRANT_URL).strip() or (
            _DEFAULT_QDRANT_URL
        )
        self._collection: str = (
            os.environ.get("QDRANT_DOCS_COLLECTION", DOCS_COLLECTION_DEFAULT).strip()
            or DOCS_COLLECTION_DEFAULT
        )
        self._collection_known: bool = False
        self._error: str = ""
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=self._url,
                api_key=os.environ.get("QDRANT_API_KEY") or None,
                timeout=_CLIENT_TIMEOUT,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._error = f"{type(exc).__name__}: {exc}"
            logger.warning("Qdrant client unavailable (%s): %s", self._url, self._error)
            self._client = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True when Qdrant answers, the collection exists and the embedder works."""
        return (
            self._client is not None
            and get_embedder().available
            and self._collection_ok()
        )

    @property
    def url(self) -> str:
        """The configured Qdrant URL."""
        return self._url

    @property
    def collection(self) -> str:
        """The configured collection name."""
        return self._collection

    @property
    def error(self) -> str:
        """The most recent connection/collection error, or ``""``."""
        return self._error

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """
        Report availability and size.  ``points`` is ``None`` — never a guessed
        number — when the count cannot be read.
        """
        embedder = get_embedder()
        available = self.available
        points: int | None = None
        if self._client is not None and self._collection_known:
            try:
                points = int(
                    self._client.count(collection_name=self._collection, exact=True).count
                )
            except Exception as exc:  # pylint: disable=broad-except
                self._error = f"{type(exc).__name__}: {exc}"
                points = None
        return {
            "available": available,
            "url": self._url,
            "collection": self._collection,
            "points": points,
            "model": embedder.model_name,
            "dim": embedder.dim,
            "error": self._error or embedder.error,
        }

    def search(self, text: str, stack: str = "", limit: int = 6) -> list[dict]:
        """
        Return the chunks most similar to *text* (best first within each lane).

        ``stack`` ``"php"`` or ``"vue"`` narrows the documentation search with a
        payload filter.  Any other value (``""``, ``"fullstack"``, ``"unknown"``)
        searches BOTH stacks and interleaves their results, so neither side
        can crowd the other out: PrimeVue makes up ~85 % of the corpus, and an
        unbalanced search for a backend issue that merely says "toggle"
        returns twenty ToggleSwitch passages and no Laravel ones.

        The ``practice`` corpus is cross-cutting, so it is never selected by
        ``stack`` — it rides along as an extra lane holding at most
        ``limit // _PRACTICE_SHARE`` slots, and drops out entirely below that
        threshold.  That lane is also the only one with a relevance floor: the
        stack lanes are already narrowed to documentation the issue's stack
        needs, whereas some practice passage is weakly similar to *every* issue
        and would otherwise spend its slots on noise.
        """
        if not text or not text.strip() or limit <= 0:
            return []
        if not self.available:
            return []
        vector = get_embedder().embed_query(text)
        if not vector:
            return []
        limit = min(limit, _SEARCH_LIMIT_CAP)
        try:
            if stack in _FILTERABLE_STACKS:
                lanes = [self._query(vector, stack, limit)]
            else:
                lanes = [self._query(vector, name, limit) for name in _FILTERABLE_STACKS]
            practice_slots = limit // _PRACTICE_SHARE
            if practice_slots:
                lanes.append([
                    hit for hit in self._query(vector, PRACTICE_STACK, practice_slots)
                    if hit["score"] >= _PRACTICE_MIN_SCORE
                ])
            return _interleave(lanes, limit)
        except Exception as exc:  # pylint: disable=broad-except
            self._collection_known = False
            logger.warning("Qdrant search failed (%s): %s", self._url, exc)
            return []

    def _query(self, vector: list[float], stack: str, limit: int) -> list[dict]:
        """One filtered KNN query; raises on a Qdrant error (caller catches)."""
        from qdrant_client import models

        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            with_payload=True,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="stack", match=models.MatchValue(value=stack))]
            ),
        )
        hits: list[dict] = []
        for point in response.points:
            payload = point.payload or {}
            hits.append(
                {
                    "doc_title": str(payload.get("doc_title", "")),
                    "doc_url": str(payload.get("doc_url", "")),
                    "doc_path": str(payload.get("doc_path", "")),
                    "source": str(payload.get("source", "")),
                    "stack": str(payload.get("stack", "")),
                    "heading": str(payload.get("heading", "")),
                    "text": str(payload.get("text", "")),
                    "score": float(point.score),
                }
            )
        return hits

    # ------------------------------------------------------------------
    # Write path (scripts/index_skills.py)
    # ------------------------------------------------------------------

    def ensure_collection(self) -> bool:
        """
        Create the collection when it is missing; verify its dimension otherwise.

        A dimension mismatch means the embedding model changed since the last
        index run — upserts would fail, so it is reported rather than papered
        over.  Returns True when the collection is ready for writes.
        """
        if self._client is None:
            return False
        try:
            if not self._client.collection_exists(self._collection):
                return self.recreate_collection()
            info = self._client.get_collection(self._collection)
            size = _vector_size(info)
            dim = get_embedder().dim
            if size is not None and size != dim:
                self._error = (
                    f"collection {self._collection} holds {size}-dim vectors but the "
                    f"embedder produces {dim} – re-run with --recreate"
                )
                return False
            self._collection_known = True
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self._error = f"{type(exc).__name__}: {exc}"
            return False

    def recreate_collection(self) -> bool:
        """Drop (when present) and create the collection plus its payload indices."""
        if self._client is None:
            return False
        try:
            from qdrant_client import models

            if self._client.collection_exists(self._collection):
                self._client.delete_collection(self._collection)
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=get_embedder().dim, distance=models.Distance.COSINE
                ),
            )
            for field in _PAYLOAD_INDEX_FIELDS:
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            self._collection_known = True
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self._error = f"{type(exc).__name__}: {exc}"
            logger.warning("Qdrant collection (re)creation failed: %s", self._error)
            return False

    def indexed_doc_hashes(self) -> dict[str, str]:
        """Return ``{doc_path: doc_hash}`` for every document already indexed."""
        hashes: dict[str, str] = {}
        if self._client is None:
            return hashes
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self._collection,
                limit=_SCROLL_PAGE,
                offset=offset,
                with_payload=["doc_path", "doc_hash"],
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                path = payload.get("doc_path")
                if path:
                    hashes[str(path)] = str(payload.get("doc_hash", ""))
            if offset is None:
                return hashes

    def delete_doc(self, doc_path: str) -> None:
        """Remove every chunk of *doc_path* so a shrunken doc leaves no orphans."""
        if self._client is None:
            return
        from qdrant_client import models

        self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_path", match=models.MatchValue(value=doc_path)
                        )
                    ]
                )
            ),
            wait=True,
        )

    def upsert_chunks(self, chunks: list[dict], vectors: list[list[float]]) -> int:
        """Upsert *chunks* (each carrying an ``id``) with their vectors, in batches."""
        if self._client is None or not chunks:
            return 0
        if len(chunks) != len(vectors):
            raise ValueError(
                f"{len(chunks)} chunk(s) but {len(vectors)} vector(s) – refusing a "
                "misaligned upsert"
            )
        from qdrant_client import models

        points = [
            models.PointStruct(
                id=chunk["id"],
                vector=vectors[index],
                payload={key: value for key, value in chunk.items() if key != "id"},
            )
            for index, chunk in enumerate(chunks)
        ]
        written = 0
        for start in range(0, len(points), _UPSERT_BATCH):
            batch = points[start:start + _UPSERT_BATCH]
            self._client.upsert(collection_name=self._collection, points=batch, wait=True)
            written += len(batch)
        return written

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collection_ok(self) -> bool:
        """Cache a positive probe; re-probe after any failure."""
        if self._collection_known:
            return True
        try:
            self._collection_known = bool(self._client.collection_exists(self._collection))
            if not self._collection_known:
                self._error = (
                    f"collection {self._collection} does not exist – run "
                    "scripts/index_skills.py"
                )
        except Exception as exc:  # pylint: disable=broad-except
            self._error = f"{type(exc).__name__}: {exc}"
            self._collection_known = False
        return self._collection_known


def _interleave(ranked_lists: list[list[dict]], limit: int) -> list[dict]:
    """
    Merge per-stack result lists rank by rank, the list with the best top hit
    first: ``[php1, vue1, php2, vue2, …]``, truncated to *limit*.
    """
    ordered = sorted(
        (hits for hits in ranked_lists if hits),
        key=lambda hits: hits[0]["score"],
        reverse=True,
    )
    merged: list[dict] = []
    for rank in range(max((len(hits) for hits in ordered), default=0)):
        for hits in ordered:
            if rank < len(hits):
                merged.append(hits[rank])
                if len(merged) == limit:
                    return merged
    return merged


def _vector_size(info) -> int | None:
    """Extract the (unnamed) vector size from a get_collection() response."""
    try:
        vectors = info.config.params.vectors
        size = getattr(vectors, "size", None)
        return int(size) if size is not None else None
    except Exception:  # pylint: disable=broad-except
        return None


_DOCUMENT_MEMORY: DocumentMemory | None = None


def get_document_memory() -> DocumentMemory:
    """Return the process-wide DocumentMemory, constructing it on first use."""
    global _DOCUMENT_MEMORY
    if _DOCUMENT_MEMORY is None:
        _DOCUMENT_MEMORY = DocumentMemory()
    return _DOCUMENT_MEMORY
