"""Deterministic synthetic benchmark contracts; not model quality evidence."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments import reranker_evaluation as evaluation
from experiments import reranker_poc as cli
from prompt_builder import _format_retrieved_section


def candidate(text: str, stack: str = "php", score: float = .5) -> dict:
    return dict(doc_title="Reference", doc_url="https://example.test/docs", doc_path="test.md",
                source="laravel", stack=stack, heading="Usage", text=text, score=score)


def record() -> dict:
    a, b, c = candidate("wrong answer", score=.9), candidate("direct answer", score=.1), candidate("partial answer", "practice", .8)
    return dict(query_id="synthetic-code", issue_key="synthetic-group", phase="code", subject="Task", description="Description",
                plan="Plan", scope="fullstack", attempt=1, detected_stack="php", split="development", slices=["tests"],
                query_text="Task\nDescription\nPlan", stack_filter="", catalog_skills=[], catalog_text="", rendered_catalog="",
                baseline_candidates=[a, c], expanded_candidates=[a, c, b],
                judgments={evaluation.candidate_key(a): 0, evaluation.candidate_key(b): 2, evaluation.candidate_key(c): 1},
                retrieval_status="verified_nonempty", retrieval_seconds={"baseline": .01, "expanded": .02})


def manifest() -> dict:
    return dict(schema_version=1, captured_at="2026-10-13T00:00:00Z", query_file_sha256="a" * 64,
                fixture_sha256="b" * 64, corpus={"test.md": "c" * 64}, registry_sha256="d" * 64,
                document_memory={"available": True}, dependencies={"fixture": "synthetic"}, hardware={"fixture": "synthetic"})


def fixture(path: Path, rows: list[dict], metadata: dict | None = None) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    Path(str(path) + ".manifest.json").write_text(json.dumps(metadata or manifest()))


def result(model_id: str = "cross-encoder/ettin-reranker-68m-v1") -> dict:
    row = evaluation._quality(record(), [0., 1., 2.])
    row["observations"] = [{"scoring_seconds": .1}] * 3
    return dict(schema_version=1, kind="reranker_evaluation", config=dict(model_id=model_id, revision=evaluation.MODEL_REVISIONS[model_id],
                batch_size=2, max_length=512, threads=1),
                hashes={key: "a" * 64 for key in ("fixture_sha256", "manifest_sha256", "split_sha256", "candidates_sha256")},
                runtime={"fixture": "synthetic"},
                measurements={"warmup_count": 1, "replay_passes": 3}, per_query=[row],
                dataset={"development_issues": 1, "heldout_queries": 0, "evaluated_heldout": False},
                artifact={"fixture": "synthetic"}, resource_ceilings=None)


class EvaluationTests(unittest.TestCase):
    def test_metrics_partial_gain_and_no_relevant_results(self):
        rows = record()
        a, c, b = rows["expanded_candidates"]
        metrics = evaluation._metrics([a, c, b], rows["judgments"], [a, c, b])
        expected = (1 / math.log2(3) + 3 / math.log2(4)) / (3 + 1 / math.log2(3))
        self.assertAlmostEqual(metrics["ndcg5"], expected)
        self.assertEqual(metrics["mrr5"], 1 / 3)
        self.assertEqual(metrics["success5"], 1.)
        zero = evaluation._metrics([a], rows["judgments"], [a])
        self.assertEqual([zero[k] for k in evaluation.METRICS], [0., 0., 0., 0.])
        self.assertTrue(zero["zero_ideal"])
        partial = evaluation._metrics([c], rows["judgments"], [c])
        self.assertEqual(partial["ndcg6"], 1.)
        self.assertEqual(partial["success5"], 0.)

    def test_lane_counts_ties_and_complete_fallback(self):
        p1, p2, p3 = [candidate(text) for text in ("one", "two", "three")]
        practice1, practice2 = candidate("practice one", "practice"), candidate("practice two", "practice")
        baseline = [p1, practice1, p2]
        expanded = [p1, practice1, p2, practice2, p3]
        original = deepcopy(expanded)
        selected, success = evaluation._lane_select(baseline, expanded, [0., 0., 4., 8., 4.])
        self.assertTrue(success)
        self.assertEqual(selected, [p2, practice2, p3])
        self.assertEqual(expanded, original)
        fallback, success = evaluation._lane_select(baseline, [p3, practice2], [10., 10.])
        self.assertFalse(success)
        self.assertEqual(fallback, baseline)

    def test_packing_keeps_neural_order_skips_whole_blocks_and_excludes_only_body(self):
        huge = candidate("x" * 6001, score=1.)
        high = candidate("dense favorite", score=.9)
        low = candidate("reranked favorite", score=.1)
        selected, text = evaluation._pack([huge, low, high], 5000, "", True)
        self.assertEqual(selected, [low, high])
        self.assertLess(text.index(low["text"]), text.index(high["text"]))
        selected, dense_text = evaluation._pack([low, high], 5000, "", False)
        self.assertEqual(selected, [high, low])
        self.assertEqual(dense_text, _format_retrieved_section([low, high], 5000))
        selected, text = evaluation._pack([low, high], 5000, low["text"], True)
        self.assertEqual(selected, [high])
        self.assertNotIn(low["text"], text)

    def test_end_to_end_has_common_ideal_and_no_tautological_recall(self):
        row = record()
        quality = evaluation._quality(row, [0., 1., 2.])
        self.assertIsNone(quality["pooled_recall20"])
        self.assertLess(quality["metrics"]["legacy"]["ndcg6"], 1.)
        self.assertEqual(quality["metrics"]["expanded_reranked"]["ndcg6"], 1.)
        row["judged_universe"] = {**row["judgments"], "f" * 64: 2}
        row["judged_universe_description"] = "Independent synthetic relevant passage outside the candidate pool"
        evaluation._validate_record(row)
        quality = evaluation._quality(row, [0., 1., 2.])
        self.assertEqual(quality["pooled_recall20"], .5)
        self.assertEqual(quality["retrieval_misses"], 1)

    def test_labels_empty_retrieval_and_scope_validation(self):
        row = record()
        evaluation._validate_record(row)
        invalid = [dict(row, judgments={}), dict(row, query_text="rewritten"), dict(row, attempt=True),
                   dict(row, stack_filter="php"), dict(row, baseline_candidates=[], expanded_candidates=[], judgments={}, retrieval_status="retrieval_unverified")]
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "query synthetic-code"):
                evaluation._validate_record(value)
        empty = invalid[-1]
        empty["independent_empty_evidence"] = "Operator independently inspected the synthetic empty collection"
        evaluation._validate_record(empty)
        nan_row = deepcopy(row)
        nan_row["expanded_candidates"][0]["score"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            evaluation._validate_record(nan_row)

    def test_fixture_split_leakage_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "fixture.jsonl"
            row = record()
            fixture(path, [row, dict(row, query_id="another", split="heldout")])
            with self.assertRaisesRegex(ValueError, "leakage"):
                evaluation._load_fixture(str(path))
            fixture(path, [row])
            loaded, metadata, hashes = evaluation._load_fixture(str(path))
            self.assertEqual(loaded, [row])
            changed = deepcopy(row)
            changed["judgments"][evaluation.candidate_key(changed["expanded_candidates"][0])] = 1
            fixture(path, [changed])
            self.assertNotEqual(evaluation._load_fixture(str(path))[2]["fixture_sha256"], hashes["fixture_sha256"])

    def test_holdout_requires_frozen_configuration(self):
        rows = [record(), dict(record(), query_id="heldout", issue_key="heldout-group", split="heldout")]
        config = result()["config"]
        self.assertEqual(evaluation._selected_records(rows, {}, config), rows[:1])
        meta = {"development_selection": {config["model_id"]: {k: v for k, v in config.items() if k != "model_id"}},
                "selection_frozen_at": "2026-10-13T00:00:00Z", "resource_ceilings": {"approval_evidence": "test-only"}}
        with self.assertRaisesRegex(ValueError, "approved resource ceilings"):
            evaluation._selected_records(rows, meta, config)
        meta["resource_ceilings"].update(warm_end_to_end_p95_seconds=10, cold_load_seconds=60,
                                        per_request_deadline_seconds=20, peak_rss_bytes=1000000000, allowed_concurrent_load=1)
        self.assertEqual(evaluation._selected_records(rows, meta, config), rows)
        with self.assertRaisesRegex(ValueError, "configuration differs"):
            evaluation._selected_records(rows, meta, {**config, "batch_size": 8})

    def test_artifact_identity_and_complete_head_are_required(self):
        model_id = "cross-encoder/ettin-reranker-150m-v1"
        revision = evaluation.MODEL_REVISIONS[model_id]
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "reranker-artifact.json"
            path.write_text(json.dumps({"model_id": model_id, "revision": "wrong"}))
            with self.assertRaisesRegex(ValueError, "identity differs"):
                evaluation.validate_artifact(name, model_id, revision)
            path.write_text(json.dumps({"model_id": model_id, "revision": revision}))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                evaluation.validate_artifact(name, model_id, revision)

    def test_bootstrap_resamples_issue_groups_deterministically(self):
        rows = [evaluation._quality(record(), [0., 1., 2.])]
        paired = evaluation._paired(rows, rows, "expanded_reranked", "expanded_dense", "ndcg6")
        self.assertGreater(paired["ci95"][0], 0)
        self.assertEqual(paired["ci95"], [paired["delta"], paired["delta"]])
        self.assertEqual(paired, evaluation._paired(rows, rows, "expanded_reranked", "expanded_dense", "ndcg6"))
        with self.assertRaisesRegex(ValueError, "identical"):
            evaluation._paired(rows, [], "legacy", "legacy", "ndcg6")

    def test_compare_rejects_different_fixtures_and_never_approves_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as name:
            first, second = Path(name) / "first.json", Path(name) / "second.json"
            first.write_text(json.dumps(result()))
            other = result("cross-encoder/ettin-reranker-150m-v1")
            second.write_text(json.dumps(other))
            args = SimpleNamespace(results=[str(first), str(second)])
            comparison = evaluation.compare(args)
            self.assertFalse(comparison["gate"]["approved_for_activation"])
            self.assertEqual(comparison["development_selection"], {})
            self.assertIsNone(comparison["quality_preference"])
            other["hashes"]["fixture_sha256"] = "e" * 64
            second.write_text(json.dumps(other))
            with self.assertRaisesRegex(ValueError, "different fixture"):
                evaluation.compare(args)
            del other["hashes"]["split_sha256"]
            with self.assertRaisesRegex(ValueError, "split_sha256"):
                evaluation._validate_result(other)


class CaptureTests(unittest.TestCase):
    def test_scope_and_attempt_match_real_callers(self):
        row = record()
        self.assertEqual(cli.query_context(row), (row["query_text"], "fullstack", "", (3, 1)))
        self.assertEqual(cli.query_context(dict(row, attempt=2))[2], "php")
        self.assertEqual(cli.query_context(dict(row, scope="frontend", attempt=2))[2:], ("vue", (3, 0)))
        self.assertEqual(cli.query_context(dict(row, scope="backend"))[2:], ("php", (0, 1)))
        self.assertEqual(cli.query_context(dict(row, phase="plan", subject="Scope: frontend", description="PrimeVue DataTable"))[1:], ("frontend", "vue", (3, 0)))
        self.assertEqual(cli.query_context(dict(row, phase="plan", subject="Scope: backend", description="Laravel migrations"))[1:], ("backend", "php", (0, 2)))

    def test_capture_refuses_without_attestation_before_services(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "queries.jsonl"
            path.write_text(json.dumps(record()) + "\n")
            Path(str(path) + ".manifest.json").write_text('{"poller_stopped": false, "sanitized": true}')
            with self.assertRaisesRegex(ValueError, "attestations"):
                cli.capture(SimpleNamespace(queries=str(path)))

    def test_capture_to_judged_fixture_roundtrip_and_empty_capture(self):
        import embedding
        import vector_store
        row = record()
        raw_candidates = row["expanded_candidates"]
        memory = SimpleNamespace(status=lambda: dict(available=True, points=3, collection="synthetic", model="synthetic", dim=384),
                                 search=lambda text, stack, limit: raw_candidates if limit == 20 else raw_candidates[:2])
        embedder = SimpleNamespace(available=True, model_name="synthetic", embed_query=lambda text: [1.])
        corpus = {"corpus_hashes": {"test.md": "c" * 64}, "corpus_sha256": "e" * 64, "registry_sha256": "d" * 64}
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "queries.jsonl"
            path.write_text(json.dumps(row) + "\n")
            Path(str(path) + ".manifest.json").write_text('{"poller_stopped": true, "sanitized": true}')
            with patch.object(embedding, "get_embedder", return_value=embedder), patch.object(vector_store, "get_document_memory", return_value=memory), patch.object(cli, "_corpus_evidence", return_value=corpus), patch("fastembed.TextEmbedding"), patch("dotenv.load_dotenv"):
                frozen, metadata = cli.capture(SimpleNamespace(queries=str(path)))
                self.assertEqual(frozen[0]["judgments"], {})
                with self.assertRaisesRegex(ValueError, "missing candidate relevance"):
                    evaluation._validate_record(frozen[0])
                frozen[0]["judgments"] = row["judgments"]
                evaluation._validate_record(frozen[0])
                metadata["fixture_sha256"] = "b" * 64
                captured = Path(name) / "frozen.jsonl"
                fixture(captured, frozen, metadata)
                self.assertEqual(evaluation._load_fixture(str(captured))[0], frozen)
                memory.search = lambda *args, **kwargs: []
                empty, metadata = cli.capture(SimpleNamespace(queries=str(path)))
                self.assertEqual(metadata["retrieval_unverified_count"], 1)
                with self.assertRaisesRegex(ValueError, "independent verification"):
                    evaluation._validate_record(empty[0])


if __name__ == "__main__":
    unittest.main()
