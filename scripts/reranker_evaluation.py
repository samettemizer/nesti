"""Offline, issue-grouped reranker evaluation; never changes production selection."""
from __future__ import annotations

import hashlib
import importlib.metadata
import itertools
import json
import logging
import math
import multiprocessing
import os
from pathlib import Path
import platform
import random
import resource
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

from prompt_builder import (
    _QDRANT_CODE_BUDGET, _QDRANT_PLAN_BUDGET,
    format_catalog_for_prompt, _format_retrieved_section, chunk_body, drop_injected_chunks,
)
from skill_loader import Skill
import reranker

logger = logging.getLogger(__name__)
POLICIES = ("merged_lane", "dense_order", "reranked", "legacy", "expanded_dense", "expanded_reranked")
METRICS = ("ndcg5", "mrr5", "success5", "ndcg6")
CONFIG_KEYS = ("model_id", "revision", "batch_size", "max_length", "threads")
REPLAY_PASSES = 3
WARMUP_COUNT = 1
BOOTSTRAP_RESAMPLES = 1000


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def candidate_key(candidate: dict) -> str:
    """Return the benchmark content key, not a Qdrant point identifier."""
    return hashlib.sha256(json.dumps(
        [candidate["doc_path"], candidate["heading"], candidate["text"]],
        ensure_ascii=False, separators=(",", ":"),
    ).encode()).hexdigest()


def runtime_provenance() -> dict:
    """Collect local dependency and Linux CPU-allocation provenance without services."""
    dependencies = {}
    for package in ("torch", "sentence-transformers", "transformers", "numpy", "tokenizers"):
        try:
            dependencies[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependencies[package] = None
    quota = None
    for path in (Path("/sys/fs/cgroup/cpu.max"),):
        if path.is_file():
            quota = path.read_text().strip()
    if quota is None:
        root = Path("/sys/fs/cgroup/cpu")
        if (root / "cpu.cfs_quota_us").is_file():
            quota = " ".join((root / name).read_text().strip() for name in ("cpu.cfs_quota_us", "cpu.cfs_period_us"))
    cpu_model = None
    if Path("/proc/cpuinfo").is_file():
        cpu_model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), None)
    return {"dependencies": dependencies, "hardware": {
        "platform": platform.platform(), "python": platform.python_version(),
        "machine": platform.machine(), "cpu_model": cpu_model,
        "cpu_count": os.cpu_count(), "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "cpu_quota": quota,
    }}


def _allocation(hardware: dict) -> float:
    count = len(hardware["affinity"]) if hardware.get("affinity") else hardware.get("cpu_count") or 1
    quota = hardware.get("cpu_quota")
    if quota:
        amount, period = quota.split()
        if amount != "max" and int(amount) > 0:
            count = min(count, int(amount) / int(period))
    return count




def _require(condition: bool, query_id: str, message: str) -> None:
    if not condition:
        raise ValueError(f"query {query_id}: {message}")


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _validate_record(record: dict) -> None:
    qid = record.get("query_id", "<missing>") if isinstance(record, dict) else "<missing>"
    _require(isinstance(record, dict), str(qid), "record must be an object")
    for field in ("query_id", "issue_key", "subject", "description", "plan", "query_text", "stack_filter", "catalog_text", "rendered_catalog"):
        _require(isinstance(record.get(field), str), str(qid), f"{field} must be a string")
    _require(bool(record["query_id"].strip() and record["issue_key"].strip() and record["query_text"].strip()), qid, "empty query/group identity or query text")
    _require(record.get("phase") in ("plan", "code"), qid, "invalid phase")
    _require(record.get("scope") in ("backend", "frontend", "fullstack"), qid, "invalid scope")
    _require(record.get("split") in ("development", "heldout"), qid, "explicit development/heldout split required")
    _require(type(record.get("attempt")) is int and record["attempt"] >= (1 if record["phase"] == "code" else 0), qid, "invalid attempt")
    if record["phase"] == "plan":
        from issue_scope import classify_issue
        _require(record["scope"] == classify_issue(record["subject"], record["description"]).scope, qid, "planning scope differs from pre-planner classification")
    _require(record.get("detected_stack") in ("", "php", "vue", "fullstack", "unknown"), qid, "invalid detected_stack")
    slices = record.get("slices", [])
    _require(isinstance(slices, list) and all(isinstance(item, str) and item.strip() for item in slices) and len(slices) == len(set(slices)), qid, "invalid slices")
    expected_query = record["subject"] + "\n" + record["description"]
    if record["phase"] == "code":
        expected_query += "\n" + record["plan"]
    _require(record["query_text"] == expected_query, qid, "query_text differs from actual caller text")
    stack = {"backend": "php", "frontend": "vue"}.get(record["scope"], "")
    if not stack and record["phase"] == "code" and record["attempt"] > 1 and record["detected_stack"] in ("php", "vue"):
        stack = record["detected_stack"]
    _require(record["stack_filter"] == stack, qid, "stack_filter differs from caller policy")
    skills = record.get("catalog_skills")
    _require(isinstance(skills, list), qid, "catalog_skills must be a list")
    for skill in skills:
        _require(isinstance(skill, dict) and all(isinstance(skill.get(key), str) for key in ("url", "title", "content")), qid, "invalid catalog skill")
    _require(record["catalog_text"] == "\n".join(skill["content"] for skill in skills), qid, "catalog_text mismatch")
    rendered = format_catalog_for_prompt(
        [Skill(url=s["url"], title=s["title"], content=s["content"]) for s in skills],
        record["phase"], record["scope"],
    )
    _require(record["rendered_catalog"] == rendered, qid, "rendered catalog mismatch")
    keys = set()
    for field, limit in (("baseline_candidates", 8), ("expanded_candidates", 20)):
        candidates = record.get(field)
        _require(isinstance(candidates, list) and len(candidates) <= limit, qid, f"invalid {field} length")
        for candidate in candidates:
            _require(isinstance(candidate, dict), qid, "candidate must be an object")
            for key in ("doc_title", "doc_url", "doc_path", "source", "stack", "heading", "text"):
                _require(isinstance(candidate.get(key), str), qid, f"candidate {key} must be a string")
            _require(bool(candidate["text"].strip() and chunk_body(candidate)), qid, "blank passage")
            _require(candidate["stack"] in ("php", "vue", "practice"), qid, "invalid candidate stack")
            _require(_finite(candidate.get("score")), qid, "dense score must be finite")
            keys.add(candidate_key(candidate))
    judgments = record.get("judgments")
    _require(isinstance(judgments, dict), qid, "judgments must be an object")
    _require(keys <= judgments.keys(), qid, "missing candidate relevance judgments")
    _require(all(isinstance(key, str) and len(key) == 64 and all(c in "0123456789abcdef" for c in key) and type(label) is int and label in (0, 1, 2) for key, label in judgments.items()), qid, "invalid relevance judgment")
    nonempty = bool(record["baseline_candidates"] and record["expanded_candidates"])
    _require(record.get("retrieval_status") == ("verified_nonempty" if nonempty else "retrieval_unverified"), qid, "invalid retrieval status")
    if not nonempty:
        _require(isinstance(record.get("independent_empty_evidence"), str) and bool(record["independent_empty_evidence"].strip()), qid, "empty retrieval needs independent verification")
    retrieval = record.get("retrieval_seconds")
    _require(isinstance(retrieval, dict) and all(_finite(retrieval.get(key)) and retrieval[key] >= 0 for key in ("baseline", "expanded")), qid, "invalid retrieval_seconds")
    if "judged_universe" in record:
        universe = record["judged_universe"]
        _require(isinstance(universe, dict) and keys <= universe.keys() and all(universe[key] == judgments[key] for key in keys), qid, "judged universe must include consistent candidate labels")
        _require(all(isinstance(key, str) and len(key) == 64 and all(c in "0123456789abcdef" for c in key) and type(label) is int and label in (0, 1, 2) for key, label in universe.items()), qid, "invalid judged universe")
        _require(isinstance(record.get("judged_universe_description"), str) and bool(record["judged_universe_description"].strip()), qid, "pooled recall needs a documented universe")
        _require(bool(set(universe) - keys), qid, "recall universe must extend beyond retrieved candidates")


def _load_fixture(path: str) -> tuple[list[dict], dict, dict]:
    fixture = Path(path)
    data = fixture.read_bytes()
    records = []
    for line_number, line in enumerate(data.splitlines(), 1):
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"fixture line {line_number}: invalid JSON") from exc
        _validate_record(record)
        records.append(record)
    if not records:
        raise ValueError("fixture is empty")
    if len({row["query_id"] for row in records}) != len(records):
        raise ValueError("duplicate query_id")
    groups = defaultdict(set)
    for row in records:
        groups[row["issue_key"]].add(row["split"])
    if any(len(splits) != 1 for splits in groups.values()):
        raise ValueError("issue group leakage between development and heldout")
    manifest_bytes = Path(str(fixture) + ".manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("fixture manifest schema_version must be 1")
    for key in ("captured_at", "query_file_sha256", "fixture_sha256", "corpus", "registry_sha256", "document_memory", "dependencies", "hardware"):
        if not manifest.get(key):
            raise ValueError(f"fixture manifest missing {key}")
    hashes = {"fixture_sha256": hashlib.sha256(data).hexdigest(),
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "split_sha256": _digest(sorted((r["query_id"], r["issue_key"], r["split"]) for r in records)),
              "candidates_sha256": _digest([(r["query_id"], r["query_text"], r["baseline_candidates"], r["expanded_candidates"]) for r in records])}
    return records, manifest, hashes


def _metrics(candidates: list[dict], judgments: dict, universe: list[dict]) -> dict:
    labels = [judgments[candidate_key(candidate)] for candidate in candidates]
    ideal = sorted((judgments[candidate_key(candidate)] for candidate in universe), reverse=True)
    def dcg(values: list[int], k: int) -> float:
        return sum((2 ** label - 1) / math.log2(index + 2) for index, label in enumerate(values[:k]))
    result = {}
    for k in (5, 6):
        denominator = dcg(ideal, k)
        result[f"ndcg{k}"] = dcg(labels, k) / denominator if denominator else 0.0
    direct = next((index + 1 for index, label in enumerate(labels[:5]) if label == 2), None)
    result.update(mrr5=1 / direct if direct else 0.0, success5=float(direct is not None),
                  zero_ideal=not any(ideal), no_directly_relevant=2 not in ideal,
                  directly_relevant_count=labels.count(2),
                  directly_relevant_unique=len({candidate_key(c) for c in candidates if judgments[candidate_key(c)] == 2}))
    return result


def _lane_select(baseline: list[dict], expanded: list[dict], scores: list[float]) -> tuple[list[dict], bool]:
    if not baseline:
        return [], False
    lanes = defaultdict(list)
    for index in sorted(range(len(expanded)), key=lambda i: scores[i], reverse=True):
        lanes[expanded[index]["stack"]].append(expanded[index])
    slots = Counter(candidate["stack"] for candidate in baseline)
    if any(len(lanes[stack]) < count for stack, count in slots.items()):
        return list(baseline), False
    positions = Counter()
    selected = []
    for candidate in baseline:
        stack = candidate["stack"]
        selected.append(lanes[stack][positions[stack]])
        positions[stack] += 1
    return selected, True


def _pack(candidates: list[dict], budget: int, exclude: str, preserve_order: bool) -> tuple[list[dict], str]:
    # Experiment-only simulation of the proposed order branch; production stays dense-only.
    ordered = drop_injected_chunks(candidates, exclude)
    if not preserve_order:
        ordered = sorted(ordered, key=lambda candidate: candidate["score"], reverse=True)
    selected, blocks, used = [], [], 0
    for candidate in ordered:
        body = chunk_body(candidate)
        if not body:
            continue
        block = f"### {candidate['doc_title']} — {candidate['heading']}\nSource: {candidate['doc_url']}\n{body}\n"
        if used + len(block) <= budget:
            selected.append(candidate)
            blocks.append(block)
            used += len(block)
    rendered = "\n## Retrieved Reference Snippets (semantic search over the vendored corpus)\n" + "\n".join(blocks) if blocks else ""
    if not preserve_order:
        actual = _format_retrieved_section(candidates, budget, exclude_text=exclude)
        if rendered != actual:
            raise ValueError("experiment packing no longer matches real legacy formatter")
        rendered = actual
    return selected, rendered


def _quality(record: dict, scores: list[float]) -> dict:
    expanded = drop_injected_chunks(record["expanded_candidates"], record["rendered_catalog"])
    baseline = drop_injected_chunks(record["baseline_candidates"], record["rendered_catalog"])[:6]
    if len(scores) != len(expanded) or not all(_finite(score) for score in scores):
        raise ValueError(f"query {record['query_id']}: invalid scoring result")
    rank = lambda values: [expanded[index] for index in sorted(range(len(expanded)), key=lambda i: values[i], reverse=True)]
    dense_scores = [candidate["score"] for candidate in expanded]
    orders = {"merged_lane": expanded, "dense_order": rank(dense_scores), "reranked": rank(scores)}
    result = {name: _metrics(order, record["judgments"], expanded) for name, order in orders.items()}
    dense, dense_success = _lane_select(baseline, expanded, dense_scores)
    neural, neural_success = _lane_select(baseline, expanded, scores)
    budget = _QDRANT_PLAN_BUDGET if record["phase"] == "plan" else _QDRANT_CODE_BUDGET
    # End-to-end policies share an ideal pool, including baseline-only positions.
    universe = list(expanded)
    remaining = Counter(candidate_key(c) for c in expanded)
    for candidate in drop_injected_chunks(record["baseline_candidates"], record["rendered_catalog"]):
        key = candidate_key(candidate)
        if remaining[key]:
            remaining[key] -= 1
        else:
            universe.append(candidate)
    for name, selected, preserve in (("legacy", baseline, False), ("expanded_dense", dense, dense_success), ("expanded_reranked", neural, neural_success)):
        packed, text = _pack(selected, budget, record["rendered_catalog"], preserve)
        result[name] = _metrics(packed, record["judgments"], universe)
        result[name].update(selected_keys=[candidate_key(c) for c in selected], rendered_keys=[candidate_key(c) for c in packed],
                            rendered_characters=len(text), rendered_sha256=hashlib.sha256(text.encode()).hexdigest(),
                            lane_replacement=preserve)
    pool = {candidate_key(c) for c in record["expanded_candidates"]}
    direct = {key for key, label in record["judgments"].items() if label == 2}
    recall = None
    missing = None
    if "judged_universe" in record:
        relevant = {key for key, label in record["judged_universe"].items() if label == 2}
        recall = len(pool & relevant) / len(relevant) if relevant else 0.0
        missing = len(relevant - pool)
    return {"query_id": record["query_id"], "issue_key": record["issue_key"], "scope": record["scope"],
            "phase": record["phase"], "split": record["split"], "slices": record.get("slices", []),
            "metrics": result, "candidate_hit": bool(pool & direct), "pooled_recall20": recall,
            "retrieval_misses": missing, "retrieval_unverified": record["retrieval_status"] == "retrieval_unverified"}


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def _distribution(values: list[float]) -> dict:
    return {"count": len(values), "p50": _percentile(values, .5), "p95": _percentile(values, .95), "max": max(values) if values else None}


def _replay(records: list[dict], config: dict, model_dir: str) -> dict:
    from reranker import score_candidates, scoring_details
    options = {key: config[key] for key in ("batch_size", "max_length", "threads")}
    options["model_dir"] = model_dir
    eligible = [drop_injected_chunks(r["expanded_candidates"], r["rendered_catalog"]) for r in records]
    first = next((index for index, candidates in enumerate(eligible) if candidates), None)
    cold = None
    if first is not None:
        score_candidates(records[first]["query_text"], eligible[first], **options)
        cold = scoring_details()
    per_query, inference_times, e2e_times, token_counts = [], [], [], []
    per_query = [None] * len(records)
    for replay in range(REPLAY_PASSES):
        for index, record in enumerate(records):
            start = time.perf_counter()
            scores = score_candidates(record["query_text"], eligible[index], **options)
            details = scoring_details()
            scoring_seconds = time.perf_counter() - start
            row = _quality(record, scores)
            selection_seconds = time.perf_counter() - start - scoring_seconds
            retrieval = record["retrieval_seconds"]
            # Retrieval is frozen capture timing, not a new live end-to-end measurement.
            e2e = scoring_seconds + selection_seconds + retrieval["baseline"] + (retrieval["expanded"] if drop_injected_chunks(record["baseline_candidates"], record["rendered_catalog"])[:6] else 0)
            observation = {"scoring_seconds": scoring_seconds, "selection_formatting_seconds": selection_seconds,
                           "estimated_end_to_end_seconds": e2e, "inference_seconds": details.get("inference_seconds")}
            if replay == 0:
                row["observations"] = []
                row["token_counts"] = details.get("token_counts", [])
                per_query[index] = row
                token_counts.extend(row["token_counts"])
            elif row["metrics"] != per_query[index]["metrics"]:
                raise ValueError(f"query {record['query_id']}: ranking changed across replay passes")
            per_query[index]["observations"].append(observation)
            inference_times.append(scoring_seconds)
            e2e_times.append(e2e)
    token_summary = {key: _distribution([item[key] for item in token_counts]) for key in (
        "original_query_tokens", "effective_query_tokens", "original_passage_tokens", "effective_passage_tokens", "special_tokens", "pair_tokens")}
    unique_queries = [row["token_counts"][0] for row in per_query if row["token_counts"]]
    token_summary["query_truncation_rate"] = sum(t["effective_query_tokens"] < t["original_query_tokens"] for t in unique_queries) / len(unique_queries) if unique_queries else None
    token_summary["passage_truncation_rate"] = sum(t["effective_passage_tokens"] < t["original_passage_tokens"] for t in token_counts) / len(token_counts) if token_counts else None
    return {"per_query": per_query, "measurements": {
        "warmup_count": WARMUP_COUNT if first is not None else 0, "replay_passes": REPLAY_PASSES,
        "cold": cold, "warm_scoring_seconds": _distribution(inference_times),
        "estimated_end_to_end_seconds": _distribution(e2e_times),
        "end_to_end_method": "captured retrieval durations plus replay scoring/selection/formatting; not live deployment latency",
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "os_threads": next((int(line.split()[1]) for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("Threads:")), None),
        "tokens": token_summary,
    }}


def _worker(connection: object, records: list[dict], config: dict, model_dir: str, started: float) -> None:
    try:
        startup = time.perf_counter() - started
        result = _replay(records, config, model_dir)
        result["measurements"]["process_startup_seconds"] = startup
        result["runtime"] = runtime_provenance()
        connection.send((True, result))
    except Exception as exc:
        connection.send((False, f"{type(exc).__name__}: {exc}"))
    finally:
        connection.close()


def _config(args: object) -> dict:
    config = {key: getattr(args, key) for key in CONFIG_KEYS}
    if config["batch_size"] not in (2, 4, 8) or type(config["batch_size"]) is not int:
        raise ValueError("batch_size must be 2, 4 or 8")
    if config["threads"] not in (1, 2, 4) or type(config["threads"]) is not int or config["threads"] > _allocation(runtime_provenance()["hardware"]):
        raise ValueError("threads must be 1, 2 or 4 and within CPU allocation")
    lengths = (512,) if "MiniLM" in config["model_id"] else (512, 1024, 2048)
    if type(config["max_length"]) is not int or config["max_length"] not in lengths:
        raise ValueError("unsupported model sweep max_length")
    return config


def _approved_ceilings(ceilings: object) -> bool:
    required = ("warm_end_to_end_p95_seconds", "cold_load_seconds", "per_request_deadline_seconds", "peak_rss_bytes", "allowed_concurrent_load")
    return (
        isinstance(ceilings, dict)
        and isinstance(ceilings.get("approval_evidence"), str)
        and bool(ceilings["approval_evidence"].strip())
        and all(_finite(ceilings.get(key)) and ceilings[key] > 0 for key in required)
    )


def _selected_records(records: list[dict], manifest: dict, config: dict) -> list[dict]:
    selection = manifest.get("development_selection")
    if selection is None:
        return [row for row in records if row["split"] == "development"]
    if not isinstance(selection, dict) or not manifest.get("selection_frozen_at") or not _approved_ceilings(manifest.get("resource_ceilings")):
        raise ValueError("heldout requires frozen development selection and approved resource ceilings")
    expected = selection.get(config["model_id"])
    actual = {key: config[key] for key in CONFIG_KEYS if key != "model_id"}
    if expected != actual:
        raise ValueError("configuration differs from frozen development selection; heldout sweep forbidden")
    return records


def evaluate(args: object) -> dict:
    """Evaluate one pinned configuration in a fresh process, without retrieval."""
    config = _config(args)
    artifact = reranker.validate_artifact(args.model_dir, args.model_id, args.revision, args.max_length)
    records, manifest, hashes = _load_fixture(args.fixture)
    selected = _selected_records(records, manifest, config)
    if not selected:
        raise ValueError("no development records to evaluate")
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, selected, config, args.model_dir, time.perf_counter()))
    process.start()
    child.close()
    try:
        success, result = parent.recv()
    except EOFError as exc:
        raise RuntimeError("evaluation process exited without a result") from exc
    finally:
        parent.close()
        if process.is_alive():
            process.join(timeout=2)
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
        if process.is_alive():
            process.kill()
        process.join()
    if not success:
        raise RuntimeError(result)
    if process.exitcode:
        raise RuntimeError(f"evaluation process exited {process.exitcode}")
    root = Path(args.model_dir)
    artifact_files = {}
    paths = sorted(path for path in root.rglob("*") if path.is_file())
    for path in paths:
        with path.open("rb") as handle:
            artifact_files[str(path.relative_to(root))] = hashlib.file_digest(handle, "sha256").hexdigest()
    result.update(schema_version=1, kind="reranker_evaluation", created_at=datetime.now(timezone.utc).isoformat(),
                  config=config, hashes=hashes, artifact={"manifest": artifact, "files_sha256": artifact_files,
                  "storage_bytes": sum(path.stat().st_size for path in paths), "image_storage_bytes": None},
                  capture={key: manifest[key] for key in ("captured_at", "corpus", "registry_sha256", "document_memory", "dependencies", "hardware")},
                  resource_ceilings=manifest.get("resource_ceilings"), development_selection=manifest.get("development_selection"),
                  selection_frozen_at=manifest.get("selection_frozen_at"),
                  dataset={"queries": len(records), "development_issues": len({r["issue_key"] for r in records if r["split"] == "development"}),
                           "heldout_queries": sum(r["split"] == "heldout" for r in records), "evaluated_heldout": any(r["split"] == "heldout" for r in selected)},
                  gate={"approved_for_activation": False, "reasons": ["Offline experiment only; compare models and complete deployment/offline/fallback evidence before promotion."]})
    return result


def _aggregate(rows: list[dict]) -> dict:
    result = {policy: {metric: statistics.mean(row["metrics"][policy][metric] for row in rows) for metric in METRICS} for policy in POLICIES} if rows else {}
    if rows:
        result["counts"] = {"queries": len(rows), "issues": len({row["issue_key"] for row in rows}),
                            "zero_ideal": sum(row["metrics"]["merged_lane"]["zero_ideal"] for row in rows),
                            "no_directly_relevant": sum(row["metrics"]["merged_lane"]["no_directly_relevant"] for row in rows),
                            "retrieval_unverified": sum(row["retrieval_unverified"] for row in rows)}
        result["candidate_hit_rate"] = statistics.mean(row["candidate_hit"] for row in rows)
        recalls = [row["pooled_recall20"] for row in rows if row["pooled_recall20"] is not None]
        result["pooled_recall20"] = statistics.mean(recalls) if recalls else None
        result["pooled_recall_queries"] = len(recalls)
        result["corpus_recall"] = "not measured"
        result["directly_relevant_rendered"] = {policy: statistics.mean(row["metrics"][policy]["directly_relevant_unique"] for row in rows) for policy in ("legacy", "expanded_dense", "expanded_reranked")}
    return result


def _paired(left: list[dict], right: list[dict], left_policy: str, right_policy: str, metric: str) -> dict:
    other = {row["query_id"]: row for row in right}
    if not left or set(other) != {row["query_id"] for row in left}:
        raise ValueError("paired comparison requires identical nonempty queries")
    groups = defaultdict(list)
    for row in left:
        peer = other[row["query_id"]]
        if row["issue_key"] != peer["issue_key"]:
            raise ValueError("paired comparison issue identity mismatch")
        groups[row["issue_key"]].append(row["metrics"][left_policy][metric] - peer["metrics"][right_policy][metric])
    keys = sorted(groups)
    rng = random.Random(0)
    draws = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        values = [value for key in rng.choices(keys, k=len(keys)) for value in groups[key]]
        draws.append(statistics.mean(values))
    return {"delta": statistics.mean(value for values in groups.values() for value in values),
            "ci95": [_percentile(draws, .025), _percentile(draws, .975)],
            "seed": 0, "resamples": BOOTSTRAP_RESAMPLES, "unit": "issue_key", "issues": len(keys), "queries": len(left)}


def _resource_failures(result: dict) -> list[str]:
    ceilings = result.get("resource_ceilings")
    if not _approved_ceilings(ceilings):
        return ["operator-approved resource ceilings are missing or incomplete"]
    measurements = result["measurements"]
    cold = measurements.get("cold") or {}
    checks = ((measurements["estimated_end_to_end_seconds"]["p95"], "warm_end_to_end_p95_seconds"),
              (cold.get("load_seconds"), "cold_load_seconds"),
              (measurements["warm_scoring_seconds"]["max"], "per_request_deadline_seconds"),
              (measurements["peak_rss_bytes"], "peak_rss_bytes"))
    return [f"resource ceiling missing/exceeded: {key}" for value, key in checks if not _finite(value) or value > ceilings[key]]


def _validate_result(result: dict) -> None:
    if not isinstance(result, dict) or result.get("schema_version") != 1 or result.get("kind") != "reranker_evaluation":
        raise ValueError("invalid evaluation result schema")
    for key in ("config", "hashes", "runtime", "measurements", "per_query", "dataset", "artifact"):
        if not result.get(key):
            raise ValueError(f"evaluation result missing {key}")
    for key in ("fixture_sha256", "manifest_sha256", "split_sha256", "candidates_sha256"):
        digest = result["hashes"].get(key)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"evaluation result missing valid {key}")
    config = result["config"]
    if reranker.MODEL_REVISIONS.get(config.get("model_id")) != config.get("revision"):
        raise ValueError("result uses an unpinned model")
    measurements = result["measurements"]
    if measurements.get("warmup_count") != 1 or measurements.get("replay_passes") != 3:
        raise ValueError("result needs one warmup and three measured replay passes")
    identities, groups = set(), defaultdict(set)
    for row in result["per_query"]:
        if row.get("query_id") in identities or not row.get("query_id") or not row.get("issue_key"):
            raise ValueError("result has duplicate or missing query identity")
        identities.add(row["query_id"])
        groups[row["issue_key"]].add(row.get("split"))
        if row.get("split") not in ("development", "heldout") or row.get("scope") not in ("backend", "frontend", "fullstack"):
            raise ValueError("result has invalid split/scope")
        if len(row.get("observations", [])) != 3:
            raise ValueError("result query is missing replay observations")
        for policy in POLICIES:
            values = row.get("metrics", {}).get(policy, {})
            if any(not _finite(values.get(metric)) or not 0 <= values[metric] <= 1 for metric in METRICS):
                raise ValueError("result has missing or nonfinite/out-of-range quality metrics")
    if any(len(splits) > 1 for splits in groups.values()):
        raise ValueError("result leaks issue groups between splits")
    if any(row["split"] == "heldout" for row in result["per_query"]):
        _selected_records(result["per_query"], result, config)


def compare(args: object) -> dict:
    """Compare identical frozen data, selecting configurations on development only."""
    results = [json.loads(Path(path).read_text()) for path in args.results]
    if not results:
        raise ValueError("no evaluation results supplied")
    for result in results:
        _validate_result(result)
    reference = results[0]
    seen = set()
    for result in results:
        if result["hashes"] != reference["hashes"]:
            raise ValueError("results have different fixture, manifest, split or candidate hashes")
        if result["runtime"] != reference["runtime"] or result.get("resource_ceilings") != reference.get("resource_ceilings"):
            raise ValueError("results have incomparable runtime provenance/resource ceilings")
        identity = tuple(result["config"][key] for key in CONFIG_KEYS)
        if identity in seen:
            raise ValueError("duplicate model/configuration result; repeated heldout inspection is forbidden")
        seen.add(identity)
        if [(r["query_id"], r["issue_key"], r["split"], r["scope"], r["slices"]) for r in result["per_query"]] != [(r["query_id"], r["issue_key"], r["split"], r["scope"], r["slices"]) for r in reference["per_query"]]:
            raise ValueError("results have different evaluated query identities/order")
        for row, peer in zip(result["per_query"], reference["per_query"]):
            if any(row["metrics"][policy] != peer["metrics"][policy] for policy in ("merged_lane", "dense_order", "legacy", "expanded_dense")):
                raise ValueError("fixed candidate reference policy differs across results")
    configurations, by_model = {}, defaultdict(list)
    for result in results:
        config_id = _digest(result["config"])
        summaries, comparisons = {}, {}
        for split in ("development", "heldout"):
            rows = [row for row in result["per_query"] if row["split"] == split]
            if not rows:
                continue
            summaries[split] = {"all": _aggregate(rows)}
            tags = sorted({tag for row in rows for tag in ["scope:" + row["scope"], *row["slices"]]})
            for tag in tags:
                summaries[split][tag] = _aggregate([row for row in rows if tag == "scope:" + row["scope"] or tag in row["slices"]])
            comparisons[split] = {}
            for left, right in (("reranked", "dense_order"), ("reranked", "merged_lane"), ("expanded_dense", "legacy"), ("expanded_reranked", "expanded_dense"), ("expanded_reranked", "legacy")):
                comparisons[split][f"{left}-{right}"] = {metric: _paired(rows, rows, left, right, metric) for metric in METRICS}
        configurations[config_id] = {"config": result["config"], "summaries": summaries, "paired": comparisons,
                                     "resource_failures": _resource_failures(result), "measurements": result["measurements"]}
        if "development" in summaries and not _resource_failures(result):
            by_model[result["config"]["model_id"]].append(result)
    selections = {}
    selected_results = {}
    for model_id, candidates in by_model.items():
        def selection_key(result: dict) -> tuple:
            rows = [row for row in result["per_query"] if row["split"] == "development"]
            quality = _aggregate(rows)["expanded_reranked"]["ndcg6"]
            config = result["config"]
            timings = [observation["scoring_seconds"] for row in rows for observation in row["observations"]]
            return (-quality, _percentile(timings, .95), config["max_length"], config["batch_size"], config["threads"])
        winner = min(candidates, key=selection_key)
        selections[model_id] = {key: winner["config"][key] for key in CONFIG_KEYS if key != "model_id"}
        selected_results[model_id] = winner
    cross_model = {}
    for left_id, right_id in itertools.combinations(sorted(selected_results), 2):
        left_result, right_result = selected_results[left_id], selected_results[right_id]
        for split in ("development", "heldout"):
            left = [row for row in left_result["per_query"] if row["split"] == split]
            right = [row for row in right_result["per_query"] if row["split"] == split]
            if left and right:
                cross_model[f"{left_id} - {right_id} ({split})"] = {policy: {metric: _paired(left, right, policy, policy, metric) for metric in METRICS} for policy in ("reranked", "expanded_reranked")}
    reasons = ["Production integration, killable-worker fallback tests, network-isolated inference and co-located deployment headroom/concurrent-load proof remain unverified.",
               "End-to-end latency uses captured retrieval plus replay timing, not actual deployment measurements."]
    if reference["dataset"]["development_issues"] < 30:
        reasons.append("Fewer than 30 development issue groups.")
    if reference["dataset"]["heldout_queries"] < 100:
        reasons.append("Fewer than 100 heldout labeled query records.")
    if not reference["dataset"].get("evaluated_heldout"):
        reasons.append("Heldout has not been evaluated after frozen development selection.")
    if set(selected_results) != set(reranker.MODEL_REVISIONS):
        reasons.append("Missing resource-eligible measured configurations for all three comparison models.")
    if any(_resource_failures(result) for result in results):
        reasons.append("Some configurations lack approved ceilings or exceed them; excluded from development selection.")
    scopes = {row["scope"] for row in reference["per_query"]}
    tags = {tag for row in reference["per_query"] for tag in row["slices"]}
    missing_slices = sorted({"api", "migrations", "primevue", "tests", "documentation", "long-input", "terminology-collision"} - tags)
    if scopes != {"backend", "frontend", "fullstack"} or missing_slices:
        reasons.append("Required scope/slice coverage is incomplete: " + ", ".join(missing_slices))
    qualifying = []
    for model_id, result in selected_results.items():
        if "ettin" not in model_id:
            continue
        rows = [row for row in result["per_query"] if row["split"] == "heldout"]
        if rows and _paired(rows, rows, "expanded_reranked", "expanded_dense", "ndcg6")["ci95"][0] > 0 and _paired(rows, rows, "expanded_reranked", "legacy", "success5")["delta"] >= 0:
            qualifying.append(model_id)
    preferred = None
    small, large = "cross-encoder/ettin-reranker-68m-v1", "cross-encoder/ettin-reranker-150m-v1"
    if small in qualifying:
        preferred = small
        if large in qualifying:
            left = [row for row in selected_results[large]["per_query"] if row["split"] == "heldout"]
            right = [row for row in selected_results[small]["per_query"] if row["split"] == "heldout"]
            if _paired(left, right, "expanded_reranked", "expanded_reranked", "ndcg6")["ci95"][0] > 0:
                preferred = large
    elif large in qualifying:
        preferred = large
    if not preferred:
        reasons.append("No Ettin configuration demonstrates the required heldout quality advantage.")
    return {"schema_version": 1, "kind": "reranker_comparison", "hashes": reference["hashes"], "dataset": reference["dataset"],
            "runtime": reference["runtime"], "resource_ceilings": reference.get("resource_ceilings"),
            "configurations": configurations, "development_selection": selections, "cross_model": cross_model,
            "quality_qualifying_models": qualifying, "quality_preference": preferred,
            "gate": {"approved_for_activation": False, "decision": "not approved for activation", "reasons": reasons},
            "limitations": ["Conditional ranking is not corpus recall; pooled recall requires an explicitly larger judged universe.",
                            "Prospective lane-order packing is an experiment-only simulation checked against the real legacy formatter.",
                            "Offline relevance does not establish issue success, retries, token cost or energy savings.",
                            "Holdout must be run once after selection; separate CLI invocations cannot prove an operator has never inspected it.",
                            "API/migration/security-sensitive failures and every per-scope regression require human review."]}


def render_report(result: dict) -> str:
    """Render aggregate, non-content-bearing evidence and the explicit no-activation gate."""
    lines = ["# Documentation reranker evaluation", "", "**Not approved for activation.**", ""]
    lines.extend("- " + reason for reason in result["gate"]["reasons"])
    lines.extend(["", "## Dataset and provenance", "", "```json", json.dumps({key: result.get(key) for key in ("hashes", "dataset", "runtime", "resource_ceilings")}, indent=2, sort_keys=True), "```", "", "## Measured configurations", ""])
    for entry in result.get("configurations", {}).values():
        lines.extend(["### " + entry["config"]["model_id"], "", "```json", json.dumps(entry, indent=2, sort_keys=True), "```", ""])
    lines.extend(["## Development selection and paired model comparisons", "", "```json", json.dumps({key: result.get(key) for key in ("development_selection", "cross_model", "quality_qualifying_models", "quality_preference")}, indent=2, sort_keys=True), "```", "", "## Limits", ""])
    lines.extend("- " + limitation for limitation in result.get("limitations", []))
    return "\n".join(lines) + "\n"
