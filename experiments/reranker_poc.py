#!/usr/bin/env python3
"""Read-only capture and offline documentation reranker experiments.

Capture requires QUERY_PATH.manifest.json with operator attestations
``{"poller_stopped": true, "sanitized": true}``. Attempts are one-based.
No command downloads models, labels data, or enables production reranking.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)
_PLAN_LIMITS = {"backend": (0, 2), "frontend": (3, 0), "fullstack": (3, 2)}
_CODE_LIMITS = {"backend": (0, 1), "frontend": (3, 0), "fullstack": (3, 1)}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def query_context(record: dict) -> tuple[str, str, str, tuple[int, int]]:
    """Validate caller inputs and reproduce dense query/scope/filter decisions."""
    from issue_scope import classify_issue

    if not isinstance(record, dict):
        raise ValueError("query record must be an object")
    key = record.get("query_id", "<missing query_id>")
    for field in ("query_id", "issue_key", "subject", "description", "plan", "scope", "phase", "detected_stack"):
        if not isinstance(record.get(field), str):
            raise ValueError(f"query {key}: {field} must be a string")
    if not record["query_id"].strip() or not record["issue_key"].strip():
        raise ValueError(f"query {key}: query_id and issue_key must be nonblank")
    if record["phase"] not in ("plan", "code"):
        raise ValueError(f"query {key}: phase must be plan or code")
    if record["scope"] not in _PLAN_LIMITS:
        raise ValueError(f"query {key}: invalid scope")
    if record["detected_stack"] not in ("", "php", "vue", "fullstack", "unknown"):
        raise ValueError(f"query {key}: invalid detected_stack")
    if type(record.get("attempt")) is not int or record["attempt"] < 1:
        raise ValueError(f"query {key}: attempt must be a positive one-based integer")
    if record.get("split") not in ("development", "heldout"):
        raise ValueError(f"query {key}: split must be development or heldout")
    if "slices" in record and (
        not isinstance(record["slices"], list)
        or any(not isinstance(s, str) or not s.strip() for s in record["slices"])
    ):
        raise ValueError(f"query {key}: slices must be nonblank strings")
    text = f"{record['subject']}\n{record['description']}"
    if not text.strip():
        raise ValueError(f"query {key}: issue text must not be blank")
    scope = record["scope"]
    if record["phase"] == "plan":
        scope = classify_issue(record["subject"], record["description"]).scope
        limits = _PLAN_LIMITS[scope]
        detected = ""
    else:
        text += f"\n{record['plan']}"
        limits = _CODE_LIMITS[scope]
        detected = record["detected_stack"] if record["attempt"] > 1 else ""
    stack = {"backend": "php", "frontend": "vue"}.get(scope) or (
        detected if detected in ("php", "vue") else ""
    )
    return text, scope, stack, limits


def _read_queries(path: Path) -> list[dict]:
    records = []
    ids: set[str] = set()
    groups: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"query line {line_number}: invalid JSON") from exc
        query_context(row)
        key = row["query_id"]
        if key in ids:
            raise ValueError(f"query {key}: duplicate query_id")
        ids.add(key)
        if groups.setdefault(row["issue_key"], row["split"]) != row["split"]:
            raise ValueError(f"query {key}: issue group crosses splits")
        records.append(row)
    if not records:
        raise ValueError("query file is empty")
    return records


def _corpus_evidence(memory: object) -> dict:
    from scripts.index_skills import iter_sources
    from skill_catalog import CATALOG_DIR

    sources = iter_sources()
    if not sources:
        raise ValueError("vendored corpus registry is unavailable or empty")
    hashes = {
        source["doc_path"]: _sha256(
            (CATALOG_DIR / source["doc_path"]).read_text(encoding="utf-8").encode("utf-8")
        )
        for source in sources
    }
    indexed = memory.indexed_doc_hashes()
    if hashes != indexed:
        raise ValueError("indexed document hashes do not match the complete vendored corpus; stop capture")
    return {
        "corpus_hashes": hashes,
        "corpus_sha256": _sha256(json.dumps(hashes, sort_keys=True).encode()),
        "registry_sha256": _sha256((CATALOG_DIR / "registry.json").read_bytes()),
    }


def capture(args: argparse.Namespace) -> tuple[list[dict], dict]:
    """Freeze exact eight/twenty searches; never write to document memory."""
    queries_path = Path(args.queries)
    authorization = json.loads(Path(str(queries_path) + ".manifest.json").read_text(encoding="utf-8"))
    if not isinstance(authorization, dict) or any(
        authorization.get(key) is not True for key in ("poller_stopped", "sanitized")
    ):
        raise ValueError("capture requires poller_stopped=true and sanitized=true operator attestations")
    records = _read_queries(queries_path)
    # Only capture loads the service environment; evaluate/smoke stay credential-free.
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from embedding import get_embedder
    from vector_store import get_document_memory
    from skill_catalog import select_skills
    from prompt_builder import format_catalog_for_prompt
    from experiments.reranker_evaluation import runtime_provenance
    from reranker import MODEL_REVISIONS

    memory = get_document_memory()
    status = memory.status()
    if not status["available"] or not status.get("points"):
        raise ValueError("document memory unavailable or collection empty; capture not verified")
    embedder = get_embedder()
    if not embedder.available:
        raise ValueError("cached embedder is unavailable")
    # The normal lazy loader may download; capture must use the cached artifact.
    from fastembed import TextEmbedding
    embedder._model = TextEmbedding(model_name=embedder.model_name, local_files_only=True)
    if not embedder.embed_query("documentation capture readiness"):
        raise ValueError("cached embedder cannot produce a query vector")
    corpus = _corpus_evidence(memory)
    frozen = []
    for row in records:
        text, scope, stack, limits = query_context(row)
        skills = select_skills(
            text, max_component_docs=limits[0], max_topic_docs=limits[1],
            max_practice_docs=1 if row["phase"] == "plan" else 0,
        )
        started = time.monotonic()
        baseline = memory.search(text, stack=stack, limit=8)
        baseline_seconds = time.monotonic() - started
        expanded_started = time.monotonic()
        expanded = memory.search(text, stack=stack, limit=20)
        expanded_seconds = time.monotonic() - expanded_started
        frozen.append({
            **row, "scope": scope, "query_text": text, "stack_filter": stack,
            "catalog_skills": [asdict(skill) for skill in skills],
            "catalog_text": "\n".join(skill.content for skill in skills),
            "rendered_catalog": format_catalog_for_prompt(skills, row["phase"], scope),
            "baseline_candidates": baseline, "expanded_candidates": expanded,
            "judgments": {},
            "retrieval_status": "verified_nonempty" if baseline and expanded else "retrieval_unverified",
            "retrieval_seconds": {"baseline": baseline_seconds, "expanded": expanded_seconds},
        })
    after = _corpus_evidence(memory)
    if after != corpus:
        raise ValueError("corpus changed during capture; discard this capture")
    manifest = {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "query_file_sha256": _sha256(queries_path.read_bytes()),
        "corpus": corpus["corpus_hashes"],
        "corpus_sha256": corpus["corpus_sha256"],
        "registry_sha256": corpus["registry_sha256"],
        "model_revisions": MODEL_REVISIONS,
        "document_memory": {key: status[key] for key in ("available", "collection", "points", "model", "dim")},
        "retrieval_unverified_count": sum(row["retrieval_status"] == "retrieval_unverified" for row in frozen),
        "capture_attestations": {"poller_stopped": True, "sanitized": True},
        **runtime_provenance(),
    }
    return frozen, manifest


def smoke(args: argparse.Namespace) -> dict:
    """Exercise a complete local artifact with real inference, not mock scores."""
    from copy import deepcopy
    from experiments.reranker_evaluation import runtime_provenance
    from reranker import score_candidates, scoring_details, validate_artifact

    artifact = validate_artifact(args.model_dir, args.model_id, args.revision)
    candidates = [
        {"text": "Mars is known as the Red Planet because of iron oxide on its surface.", "score": 0.1},
        {"text": "Venus has a thick atmosphere and is the second planet from the Sun.", "score": 0.9},
        {"text": "Apples are fruit grown on trees and used in pies.", "score": 0.8},
    ]
    original = deepcopy(candidates)
    config = {"model_dir": args.model_dir, "batch_size": 2, "max_length": 512, "threads": 1}
    scores = score_candidates("Which planet is known as the Red Planet?", candidates, **config)
    cold_details = scoring_details()
    if sorted(range(len(scores)), key=scores.__getitem__, reverse=True)[0] != 0:
        raise ValueError("real-model smoke failed: Mars did not rank first")
    warm_scores = score_candidates("Which planet is known as the Red Planet?", candidates, **config)
    warm_details = scoring_details()
    if max(range(len(warm_scores)), key=warm_scores.__getitem__) != 0:
        raise ValueError("real-model smoke failed: warm ranking changed")
    if warm_details["model_loaded"]:
        raise ValueError("real-model smoke failed: warm call reloaded the model")
    if candidates != original or len(warm_scores) != 3:
        raise ValueError("real-model smoke failed: metadata changed or score count mismatch")
    long_candidates = [{"text": "A passage about Mars and planetary geology. " * 1500, "score": 0.5}]
    long_query = "planetary science " * 300 + "Which planet is the Red Planet?"
    score_candidates(long_query, long_candidates, **config)
    long_details = scoring_details()
    counts = long_details["token_counts"][0]
    if not (
        counts["original_query_tokens"] > 128
        and counts["effective_query_tokens"] == 128
        and counts["effective_passage_tokens"] < counts["original_passage_tokens"]
        and counts["pair_tokens"] <= 512
    ):
        raise ValueError("real-model smoke failed: long-input token policy not observed")
    return {
        "status": "compatibility_smoke_only", "model_id": args.model_id, "revision": args.revision,
        "scores": scores, "warm_scores": warm_scores, "metadata_unchanged": True,
        "cold": cold_details, "warm": warm_details, "long_input": long_details,
        "artifact": artifact, "provenance": runtime_provenance(),
        "activation": "not approved for activation",
    }


def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run one explicit experiment operation; failures exit nonzero without fallback data."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cap = commands.add_parser("capture", help="freeze read-only Qdrant searches; stopped poller required")
    cap.add_argument("--queries", required=True)
    cap.add_argument("--output", required=True)
    for name in ("evaluate", "smoke"):
        command = commands.add_parser(name, help="local CPU inference, no downloads")
        for field in ("model-dir", "model-id", "revision"):
            command.add_argument("--" + field, required=True)
        if name == "evaluate":
            command.add_argument("--fixture", required=True)
            command.add_argument("--output", required=True)
            for field in ("batch-size", "max-length", "threads"):
                command.add_argument("--" + field, type=int, required=True)
    comparison = commands.add_parser("compare", help="paired issue-group comparison and Markdown report")
    comparison.add_argument("--results", nargs="+", required=True)
    comparison.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "smoke":
            print(_json(smoke(args)), end="")
            return 0
        output = Path(args.output)
        companions = []
        if args.command == "capture":
            companions = [Path(str(output) + ".manifest.json")]
        elif args.command == "compare":
            companions = [output.with_suffix(".md")]
            if companions[0] == output:
                raise ValueError("comparison output must not have .md suffix")
        if any(path.exists() for path in [output, *companions]):
            raise ValueError("output already exists; choose new explicit artifact paths")
        if args.command == "capture":
            rows, manifest = capture(args)
            content = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)
            manifest["fixture_sha256"] = _sha256(content.encode("utf-8"))
            extra = _json(manifest)
            summary = {"captured_records": len(rows), "retrieval_unverified": manifest["retrieval_unverified_count"]}
        else:
            from experiments.reranker_evaluation import evaluate, compare, render_report
            result = evaluate(args) if args.command == "evaluate" else compare(args)
            content = _json(result)
            extra = render_report(result) if args.command == "compare" else ""
            summary = {"output": str(output), "activation": "not approved for activation"}
        _write_new(output, content)
        if companions:
            _write_new(companions[0], extra)
        print(_json(summary), end="")
        return 0
    except Exception as exc:
        # Model/service exceptions may contain private inputs; only validation errors are displayed.
        detail = str(exc) if isinstance(exc, (ValueError, FileNotFoundError)) else type(exc).__name__
        print(f"reranker experiment failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
