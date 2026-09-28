"""Chunk, embed and index the vendored ``skills/`` corpus into Qdrant (Phase 8).

Every document listed in ``skills/registry.json`` is read at FULL length —
``skill_catalog``'s 7 000-char per-document cap is deliberately not applied,
because reaching past that cap is the point of the vector index — split on its
``## `` sections, embedded with ``embedding.get_embedder()`` and upserted into
the ``QDRANT_DOCS_COLLECTION`` collection (default ``nesti_docs``).

Idempotent by content hash: an unchanged document is skipped, a changed one is
deleted and re-indexed (a document that shrank leaves no orphan chunks), and a
document that left the registry is removed.  Chunk ids are deterministic, so a
re-run never duplicates points.

Run manually after ``scripts/fetch_skills.py``; the orchestrator never blocks
on ingestion::

    python scripts/index_skills.py [--force] [--recreate] [--only primevue|laravel]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import uuid
from pathlib import Path

# scripts/ is sys.path[0] when run as a file; the project modules live one up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

# Project modules read their environment lazily (at construction, inside
# main()), so load_dotenv() lives in main(): importing chunk_document for a
# unit test must not pull the operator's .env into the caller's process.
import skill_catalog  # noqa: E402
from embedding import get_embedder  # noqa: E402
from vector_store import get_document_memory  # noqa: E402

logger = logging.getLogger(__name__)

_MAX_CHUNK_CHARS = 2_000
_MIN_CHUNK_CHARS = 120
_PREAMBLE_HEADING = "Overview"


def _chunk_id(doc_path: str, index: int) -> str:
    """Deterministic point id: re-indexing overwrites instead of duplicating."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nesti:{doc_path}:{index}"))


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split on ``\\n## `` boundaries; return ``(heading, body)`` pairs in order."""
    parts = text.split("\n## ")
    sections: list[tuple[str, str]] = []
    preamble = parts[0]
    # The preamble's own "# Title" line is already carried by the chunk prefix.
    lines = preamble.lstrip("\n").split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    sections.append((_PREAMBLE_HEADING, "\n".join(lines).strip()))
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        sections.append((heading.strip() or _PREAMBLE_HEADING, body.strip()))
    return sections


def _split_body(body: str) -> list[str]:
    """Pack paragraphs into pieces of at most ``_MAX_CHUNK_CHARS``; hard-cut giants."""
    if len(body) <= _MAX_CHUNK_CHARS:
        return [body]
    pieces: list[str] = []
    current = ""
    for paragraph in body.split("\n\n"):
        if len(paragraph) > _MAX_CHUNK_CHARS:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(
                paragraph[start:start + _MAX_CHUNK_CHARS]
                for start in range(0, len(paragraph), _MAX_CHUNK_CHARS)
            )
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > _MAX_CHUNK_CHARS:
            pieces.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def chunk_document(text: str, doc_title: str, doc_path: str = "") -> list[dict]:
    """
    Split one markdown document into retrieval chunks.

    Each chunk is ``{"id", "heading", "chunk_index", "text"}``.  ``text`` starts
    with the context line ``# {doc_title}\\n## {heading}\\n\\n`` so a chunk
    retrieved alone still names its component/topic, and its body never
    exceeds ``_MAX_CHUNK_CHARS``.  Bodies shorter than ``_MIN_CHUNK_CHARS`` are
    navigation stubs and dropped — unless that would leave the document with
    no chunk at all, in which case its longest body is kept so every document
    stays represented (and hash-tracked) in the index.
    """
    candidates: list[tuple[str, str]] = []
    for heading, body in _split_sections(text):
        if not body:
            continue
        for piece in _split_body(body):
            piece = piece.strip()
            if piece:
                candidates.append((heading, piece))

    kept = [(h, b) for h, b in candidates if len(b) >= _MIN_CHUNK_CHARS]
    if not kept and candidates:
        kept = [max(candidates, key=lambda pair: len(pair[1]))]

    chunks: list[dict] = []
    for index, (heading, body) in enumerate(kept):
        chunks.append(
            {
                "id": _chunk_id(doc_path, index),
                "heading": heading,
                "chunk_index": index,
                "text": f"# {doc_title}\n## {heading}\n\n{body}",
            }
        )
    return chunks


def iter_sources(only: str | None = None) -> list[dict]:
    """Every indexable document in the registry, with its payload metadata."""
    registry = skill_catalog.load_registry()
    sources: list[dict] = []

    primevue = registry.get("primevue") or {}
    if only in (None, "primevue") and isinstance(primevue, dict):
        pattern = str(primevue.get("source_pattern", ""))
        version = str(primevue.get("version", ""))
        for entry in primevue.get("components") or []:
            sources.append({
                "doc_path": entry["path"],
                "doc_title": entry["name"],
                "doc_url": skill_catalog._build_url(pattern, slug=entry["slug"]),
                "source": "primevue",
                "stack": "vue",
                "version": version,
            })
        for entry in primevue.get("pages") or []:
            sources.append({
                "doc_path": entry["path"],
                "doc_title": entry["slug"].title(),
                "doc_url": skill_catalog._build_url(pattern, slug=entry["slug"]),
                "source": "primevue",
                "stack": "vue",
                "version": version,
            })

    laravel = registry.get("laravel") or {}
    if only in (None, "laravel") and isinstance(laravel, dict):
        pattern = str(laravel.get("source_pattern", ""))
        for entry in laravel.get("topics") or []:
            sources.append({
                "doc_path": entry["path"],
                "doc_title": entry["title"],
                "doc_url": skill_catalog._build_url(
                    pattern, branch=entry["branch"], topic=entry["topic"]
                ),
                "source": "laravel",
                "stack": "php",
                "version": str(entry.get("branch") or laravel.get("branch", "")),
            })
    return sources


def _fmt(count: int) -> str:
    """Thousands with a thin space: ``2041`` → ``2 041``."""
    return f"{count:,}".replace(",", " ")


def main(argv: list[str] | None = None) -> int:
    """Index the corpus, print the summary line, return the exit code."""
    parser = argparse.ArgumentParser(description="Index the skills/ corpus into Qdrant.")
    parser.add_argument("--force", action="store_true",
                        help="re-embed every document, ignoring content hashes")
    parser.add_argument("--recreate", action="store_true",
                        help="drop and recreate the collection first")
    parser.add_argument("--only", choices=["primevue", "laravel"],
                        help="index only one corpus")
    args = parser.parse_args(argv)
    load_dotenv()  # before the singletons below read QDRANT_URL & co.

    memory = get_document_memory()
    embedder = get_embedder()

    if not embedder.enabled:
        print("NESTI_MEMORY_ENABLED=false – nothing to index.")
        return 1
    if not embedder.embed_documents(["nesti"]):
        print(f"embedding model {embedder.model_name} unavailable: {embedder.error}")
        return 1
    ready = memory.recreate_collection() if args.recreate else memory.ensure_collection()
    if not ready:
        print(f"Qdrant unavailable at {memory.url} (collection {memory.collection}): "
              f"{memory.error or 'client could not be constructed'}")
        return 1

    sources = iter_sources(args.only)
    if not sources:
        print("skills/registry.json lists no documents – run scripts/fetch_skills.py first.")
        return 1

    indexed_hashes = memory.indexed_doc_hashes()
    wanted_paths = {source["doc_path"] for source in sources}
    indexed_docs = skipped = chunk_total = 0
    failures: list[str] = []

    for source in sources:
        doc_path = source["doc_path"]
        try:
            raw = (skill_catalog.CATALOG_DIR / doc_path).read_text(encoding="utf-8")
        except Exception as exc:  # pylint: disable=broad-except
            failures.append(f"{doc_path}: unreadable ({exc})")
            continue
        doc_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if not args.force and indexed_hashes.get(doc_path) == doc_hash:
            skipped += 1
            continue

        chunks = chunk_document(raw, source["doc_title"], doc_path)
        if not chunks:
            failures.append(f"{doc_path}: empty document")
            continue
        vectors = embedder.embed_documents([chunk["text"] for chunk in chunks])
        if len(vectors) != len(chunks):
            failures.append(f"{doc_path}: embedding failed")
            continue
        for chunk in chunks:
            chunk.update(source, doc_hash=doc_hash)
        try:
            if doc_path in indexed_hashes:
                memory.delete_doc(doc_path)
            chunk_total += memory.upsert_chunks(chunks, vectors)
        except Exception as exc:  # pylint: disable=broad-except
            failures.append(f"{doc_path}: upsert failed ({exc})")
            continue
        indexed_docs += 1
        logger.info("indexed %s → %d chunk(s)", doc_path, len(chunks))

    # A document that left the registry must not keep answering searches.
    own_prefix = f"{args.only}/" if args.only else ""
    removed = 0
    for stale in sorted(set(indexed_hashes) - wanted_paths):
        if own_prefix and not stale.startswith(own_prefix):
            continue
        try:
            memory.delete_doc(stale)
            removed += 1
        except Exception as exc:  # pylint: disable=broad-except
            failures.append(f"{stale}: stale-document removal failed ({exc})")

    summary = (
        f"indexed {indexed_docs} doc(s) → {_fmt(chunk_total)} chunk(s) · "
        f"skipped {skipped} unchanged"
    )
    if removed:
        summary += f" · removed {removed} stale"
    print(f"{summary} · collection {memory.collection} @ {memory.url}")

    if failures:
        logger.error("%d indexing failure(s):", len(failures))
        for item in failures:
            logger.error("  - %s", item)
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
