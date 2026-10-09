"""Offline startup and skill-index regressions. Run: python test_startup.py."""

import hashlib
import io
import logging
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

# Importing the CLI must not load operator credentials or construct the engine.
with (
    patch("dotenv.load_dotenv"),
    patch.dict(sys.modules, {"task_engine": SimpleNamespace(TaskEngine=Mock())}),
):
    import main as startup

import embedding
from scripts import index_skills

logger = logging.getLogger(__name__)
passed_checks = 0


def check(condition: bool, label: str) -> None:
    """Fail immediately, matching the offline graph smoke suite."""
    global passed_checks
    assert condition, f"FAILED: {label}"
    passed_checks += 1
    print(f"  ✓ {label}")


def _run_startup(
    *, enabled: str | None = None, index_status: int = 0,
    index_error: Exception | None = None, ready_error: Exception | None = None,
    loop: bool = False,
) -> tuple[list[str], int | None]:
    events: list[str] = []

    def ready() -> None:
        events.append("ready")
        if ready_error:
            raise ready_error

    def index(argv: list[str]) -> int:
        assert argv == [], "startup must use the ordinary hash-based index command"
        events.append("index")
        if index_error:
            raise index_error
        return index_status

    def poll() -> bool:
        events.append("poll")
        if loop:
            raise KeyboardInterrupt
        return True

    def engine() -> SimpleNamespace:
        events.append("engine")
        return SimpleNamespace(run_once=poll)

    environment = {} if enabled is None else {"NESTI_MEMORY_ENABLED": enabled}
    with (
        patch.dict(os.environ, environment, clear=True),
        patch.object(embedding, "_EMBEDDER", None),
        patch.dict(sys.modules, {"task_engine": SimpleNamespace(TaskEngine=engine)}),
        patch.object(sys, "argv", ["main.py", *(["--loop"] if loop else [])]),
        patch.object(startup, "_setup_logging"),
        patch.object(startup, "_wait_for_qdrant", side_effect=ready),
        patch.object(startup.logger, "exception"),
        patch.object(index_skills, "main", side_effect=index),
    ):
        try:
            startup.main()
        except SystemExit as exc:
            return events, exc.code
    return events, None


check(_run_startup() == (["ready", "index", "engine", "poll"], 0),
      "default-enabled startup indexes before engine construction and polling")
check(_run_startup(loop=True) == (["ready", "index", "engine", "poll"], None),
      "loop startup indexes once before its first poll")
for loop in (False, True):
    for options in ({"index_status": 1}, {"index_error": RuntimeError("index failed")}):
        check(_run_startup(loop=loop, **options) == (["ready", "index"], 1),
              f"index failure exits nonzero without constructing or polling engine (loop={loop})")
check(_run_startup(ready_error=RuntimeError("Qdrant not ready"), loop=True)
      == (["ready"], 1), "readiness failure stops before indexing and polling")
for disabled in ("0", "false", "no", "off", " FALSE "):
    check(_run_startup(enabled=disabled) == (["engine", "poll"], 0),
          f"memory disabled ({disabled!r}) skips readiness and indexing")


# Only Qdrant's first-start readiness is retried, not indexing itself.
with (
    patch("vector_store.get_document_memory", return_value=SimpleNamespace(url="http://qdrant:6333/")),
    patch.dict(os.environ, {"QDRANT_API_KEY": "test-only-key"}, clear=True),
    patch.object(startup.time, "monotonic", return_value=0),
    patch.object(startup.time, "sleep") as sleep,
    patch.object(startup.requests, "get", side_effect=[
        startup.requests.ConnectionError("starting"),
        SimpleNamespace(status_code=503), SimpleNamespace(status_code=200),
    ]) as get,
):
    startup._wait_for_qdrant()
    check(get.call_count == 3 and sleep.call_count == 2,
          "fresh Qdrant may refuse a connection or report unready before becoming ready")

with (
    patch("vector_store.get_document_memory", return_value=SimpleNamespace(url="http://qdrant:6333")),
    patch.dict(os.environ, {}, clear=True),
    patch.object(startup.time, "monotonic", side_effect=[0, 0, 60, 60]),
    patch.object(startup.time, "sleep"),
    patch.object(startup.requests, "get", side_effect=startup.requests.ConnectionError("down")) as get,
):
    try:
        startup._wait_for_qdrant()
    except RuntimeError as exc:
        check("60 seconds" in str(exc) and get.call_count == 1,
              "unavailable Qdrant fails after the bounded startup window")
    else:
        raise AssertionError("Qdrant readiness timeout must fail startup")


# Exercise the existing indexer, not a second startup ingestion implementation.
with tempfile.TemporaryDirectory() as directory:
    guide = Path(directory) / "guide.md"
    original = "# Guide\n\n## Rules\n\n" + "Keep the rules in the shared code. " * 8
    guide.write_text(original, encoding="utf-8")
    memory = Mock(collection="test_docs", url="http://qdrant:6333")
    memory.ensure_collection.return_value = True
    memory.indexed_doc_hashes.return_value = {
        "guide.md": hashlib.sha256(original.encode("utf-8")).hexdigest(),
    }
    memory.upsert_chunks.side_effect = lambda chunks, vectors: len(chunks)
    embedder = Mock(enabled=True)
    embedder.embed_documents.side_effect = lambda texts: [[0.0] for _ in texts]
    with (
        patch.object(index_skills, "load_dotenv"),
        patch.object(index_skills, "get_document_memory", return_value=memory),
        patch.object(index_skills, "get_embedder", return_value=embedder),
        patch.object(index_skills.skill_catalog, "CATALOG_DIR", Path(directory)),
        patch.object(index_skills, "iter_sources", return_value=[{
            "doc_path": "guide.md", "doc_title": "Guide",
        }]),
        redirect_stdout(io.StringIO()),
    ):
        unchanged_status = index_skills.main([])
        unchanged_calls = embedder.embed_documents.call_args_list[:]
        skipped = not memory.upsert_chunks.called and not memory.delete_doc.called
        guide.write_text(original + "\nChanged guidance.\n", encoding="utf-8")
        changed_status = index_skills.main([])
    check(unchanged_status == 0 and skipped and unchanged_calls == [call(["nesti"])],
          "ordinary indexing skips unchanged hashes without re-embedding documents")
    check(changed_status == 0 and memory.upsert_chunks.call_count == 1
          and memory.delete_doc.call_args == call("guide.md")
          and memory.upsert_chunks.call_args.args[0][0]["doc_hash"]
          == hashlib.sha256(guide.read_bytes()).hexdigest(),
          "changed documents are replaced with their current hash before polling")

print(f"\n{passed_checks} startup/index checks passed.")
