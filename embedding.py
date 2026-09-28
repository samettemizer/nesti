"""
embedding.py – shared fastembed text embedder (Phase 8).

Both vector indices — the Qdrant document memory (``vector_store.py``) and the
Redis semantic cache (``semantic_cache.py``) — embed through this one module,
so the two can never drift into different vector spaces.

Model: ``BAAI/bge-small-en-v1.5`` (384 dims, cosine), run in-process on the CPU
via fastembed.  Offline and free once the ONNX weights are cached; the
orchestrator and MCP images bake them in at build time.

bge-v1.5 is trained for asymmetric retrieval: a short *query* is compared
against longer *passages*, and the query side carries an instruction prefix.
``embed_query`` adds it, ``embed_documents`` never does.

Resilience:
    Nothing here raises.  The model is loaded lazily on the first embed call;
    a load failure (package missing, weights not downloadable) is logged once
    and latched, after which ``available`` is False and every embed returns
    ``[]`` — the memory layer then degrades to "no results" and the pipeline
    runs exactly as it did before Phase 8.
"""

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_MODEL: str = "BAAI/bge-small-en-v1.5"
DEFAULT_DIM: int = 384
_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "


def _env_enabled() -> bool:
    """Read NESTI_MEMORY_ENABLED (default true)."""
    raw = os.environ.get("NESTI_MEMORY_ENABLED", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _to_floats(vector) -> list[float]:
    """Plain Python floats: fastembed yields numpy float32 arrays."""
    if hasattr(vector, "tolist"):
        return vector.tolist()
    return [float(value) for value in vector]


class Embedder:
    """
    Lazily-loaded fastembed ``TextEmbedding`` wrapper.

    ``available`` is cheap and side-effect free: it never loads the model, so
    callers may consult it before every request.
    """

    def __init__(self) -> None:
        self._enabled: bool = _env_enabled()
        self._model_name: str = (
            os.environ.get("NESTI_EMBEDDING_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        )
        raw_dim = os.environ.get("NESTI_EMBEDDING_DIM", str(DEFAULT_DIM)).strip()
        try:
            self._dim: int = int(raw_dim)
        except ValueError:
            logger.warning(
                "Invalid NESTI_EMBEDDING_DIM=%r – using default of %d.", raw_dim, DEFAULT_DIM
            )
            self._dim = DEFAULT_DIM
        self._model = None
        self._failed: bool = False
        self._error: str = ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True unless memory is disabled or the model failed to load."""
        return self._enabled and not self._failed

    @property
    def enabled(self) -> bool:
        """False when NESTI_MEMORY_ENABLED switches the memory layer off."""
        return self._enabled

    @property
    def dim(self) -> int:
        """Vector dimension shared by every index built on this embedder."""
        return self._dim

    @property
    def model_name(self) -> str:
        """The fastembed model identifier."""
        return self._model_name

    @property
    def error(self) -> str:
        """The latched model-load error, or ``""``."""
        return self._error

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages (no instruction prefix).  ``[]`` on any failure."""
        if not texts or not self._load():
            return []
        try:
            return [_to_floats(vector) for vector in self._model.embed(texts)]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Document embedding failed: %s", exc)
            return []

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query with the bge instruction prefix.  ``[]`` on failure."""
        if not text or not text.strip() or not self._load():
            return []
        try:
            vectors = list(self._model.embed([_QUERY_PREFIX + text]))
            return _to_floats(vectors[0]) if vectors else []
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Query embedding failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> bool:
        """Construct the model on first use; latch and log a failure once."""
        if self._model is not None:
            return True
        if not self.available:
            return False
        try:
            from fastembed import TextEmbedding  # heavy import, deferred on purpose

            self._model = TextEmbedding(model_name=self._model_name)
            logger.info(
                "Embedding model %s loaded (%d dims).", self._model_name, self._dim
            )
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self._failed = True
            self._error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "Embedding model %s unavailable (%s) – vector memory disabled.",
                self._model_name,
                self._error,
            )
            return False


_EMBEDDER: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the process-wide Embedder, constructing it on first use."""
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = Embedder()
    return _EMBEDDER
