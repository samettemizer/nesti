"""Synthetic scoring/worker regressions; no real model, services or downloads."""
from copy import deepcopy
from contextlib import nullcontext
import json
import multiprocessing
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tokenizers import Tokenizer, models, pre_tokenizers, processors

import reranker


def synthetic_artifact(root: Path, **overrides) -> dict:
    """Create metadata/non-model placeholders only for spawn-safe fake workers."""
    root.mkdir(parents=True, exist_ok=True)
    model_id = "cross-encoder/ettin-reranker-150m-v1"
    profile = {
        "model_id": model_id, "revision": reranker.MODEL_REVISIONS[model_id],
        "batch_size": 2, "max_length": 512, "threads": 1,
        "load_timeout_seconds": 5.0, "inference_timeout_seconds": 1.0,
        **overrides,
    }
    files = {
        "config.json": {"max_position_embeddings": 8192},
        "tokenizer_config.json": {"model_max_length": 7999},
        "tokenizer.json": {"synthetic": True},
        "config_sentence_transformers.json": {"synthetic": True},
        "reranker-artifact.json": {"model_id": profile["model_id"], "revision": profile["revision"]},
        "reranker-profile.json": profile,
        "modules.json": [
            {"idx": i, "name": str(i), "path": path, "type": kind}
            for i, (path, kind) in enumerate(reranker._ETTIN_MODULES)
        ],
    }
    for module in ("1_Pooling", "2_Dense", "3_LayerNorm", "4_Dense"):
        (root / module).mkdir()
        files[f"{module}/config.json"] = {"synthetic": True}
    for name, value in files.items():
        (root / name).write_text(json.dumps(value), encoding="utf-8")
    for name in ("model.safetensors", "2_Dense/model.safetensors", "3_LayerNorm/model.safetensors", "4_Dense/model.safetensors"):
        (root / name).write_bytes(b"synthetic test placeholder; not model weights")
    if "ettin" not in profile["model_id"]:
        (root / "modules.json").unlink()
    return profile


def fake_worker(connection, model_dir, profile):
    """Exercise the actual spawn/pipe boundary without importing an ML framework."""
    mode = Path(model_dir).name
    try:
        if mode == "load_timeout":
            time.sleep(60)
        if mode == "load_exit":
            os._exit(17)
        if mode == "load_error":
            connection.send_bytes(b'{"error":"load_error"}')
            return
        if mode == "bad_ready":
            connection.send_bytes(b'{"ready":1}')
            return
        connection.send_bytes(b'{"ready":true}')
        if mode == "send_timeout":
            time.sleep(60)
        if mode == "ignore_terminate":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            request = json.loads(connection.recv_bytes())
            if set(request) != {"query", "texts"} or not all(isinstance(text, str) for text in request["texts"]):
                raise AssertionError("worker received metadata instead of only query/texts")
            count = len(request["texts"])
            if mode in ("inference_timeout", "ignore_terminate"):
                time.sleep(60)
            if mode == "inference_exit":
                os._exit(18)
            if mode == "inference_raise":
                raise RuntimeError("synthetic worker exception")
            if mode == "inference_error":
                connection.send_bytes(b'{"error":"inference_error"}')
                return
            if mode == "partial_reply":
                os.write(connection.fileno(), struct.pack("!i", 100) + b"{")
                time.sleep(60)
            if mode == "oversized_reply":
                os.write(connection.fileno(), struct.pack("!i", reranker._MAX_REPLY_BYTES + 1))
                time.sleep(60)
            scores = [float(i) for i in range(count)]
            if mode == "ties":
                scores = [1.0] * count
            elif mode == "wrong_count":
                scores.pop()
            elif mode in ("nan", "inf", "bool"):
                scores[0] = {"nan": float("nan"), "inf": float("inf"), "bool": True}[mode]
            elif mode == "wrong_shape":
                scores = [[value] for value in scores]
            connection.send_bytes(json.dumps({"scores": scores}).encode())
    except (EOFError, OSError):
        pass
    finally:
        connection.close()


def candidate(text="passage", stack="php", score=0.5) -> dict:
    """Return a normal dense candidate plus metadata that must survive selection."""
    return dict(doc_title="Title", doc_url="https://docs.invalid/page", doc_path="page",
                source="test", stack=stack, heading="Heading", text=text, score=score,
                extra={"preserve": True})


def tokenizer() -> SimpleNamespace:
    """Use a real tokenizer backend to verify token IDs and pair truncation."""
    words = ["[UNK]", "[CLS]", "[SEP]", *[f"q{i}" for i in range(200)], "passage"]
    backend = Tokenizer(models.WordLevel({word: i for i, word in enumerate(words)}, unk_token="[UNK]"))
    backend.pre_tokenizer = pre_tokenizers.Whitespace()
    backend.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 1), ("[SEP]", 2)],
    )
    return SimpleNamespace(backend_tokenizer=backend, model_input_names=["input_ids", "attention_mask", "token_type_ids"],
                           num_special_tokens_to_add=lambda pair: 3)


class ScoringTests(unittest.TestCase):
    def test_empty_does_not_load_and_invalid_text_fails_before_loading(self):
        with patch.object(reranker, "_load_model", side_effect=AssertionError("must not load")):
            self.assertEqual(reranker.score_candidates("", [], model_dir="", batch_size=0, max_length=0, threads=0), [])
            for query, rows in [(" ", [{"text": "valid"}]), ("query", [{}]), ("query", [{"text": None}]),
                                ("query", [{"text": " \n"}]), ("query", ["passage"])]:
                with self.subTest(query=query, rows=rows), self.assertRaises(ValueError):
                    reranker.score_candidates(query, rows, model_dir="missing", batch_size=2, max_length=512, threads=1)

    def test_query_head_tail_and_passage_budget_use_exact_ids(self):
        tok = tokenizer()
        query = " ".join(f"q{i}" for i in range(200))
        rows = [{"text": "passage " * 1000, "score": .8, "arbitrary": {"keep": True}}]
        original = deepcopy(rows)
        backend = tok.backend_tokenizer
        processed = []

        def post_process(*args, **kwargs):
            result = backend.post_process(*args, **kwargs)
            processed.append(result)
            return result

        tok.backend_tokenizer = SimpleNamespace(encode=backend.encode, post_process=post_process)
        pairs, counts = reranker._prepare_pairs(tok, query, rows, 150)
        self.assertEqual(pairs[0]["input_ids"], [1] + list(range(3, 99)) + list(range(171, 203)) + [2] + [203] * 19 + [2])
        self.assertEqual(counts, [{"original_query_tokens": 200, "effective_query_tokens": 128,
                                  "original_passage_tokens": 1000, "effective_passage_tokens": 19,
                                  "special_tokens": 3, "pair_tokens": 150}])
        self.assertEqual(rows, original)
        self.assertFalse(processed[0].overflowing, "discarded windows must not multiply during pair processing")
        with self.assertRaisesRegex(ValueError, "no passage tokens"):
            reranker._prepare_pairs(tok, query, rows, 131)

    def test_short_query_and_equal_boundary_are_unchanged(self):
        tok = tokenizer()
        for length in (1, 128):
            query = " ".join(f"q{i}" for i in range(length))
            pairs, counts = reranker._prepare_pairs(tok, query, [{"text": "passage"}], 512)
            self.assertEqual(pairs[0]["input_ids"], [1] + list(range(3, length + 3)) + [2, 203, 2])
            self.assertEqual(counts[0]["effective_query_tokens"], length)

    def test_model_limits_and_vulnerable_framework_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            synthetic_artifact(root)
            self.assertEqual(reranker._artifact_limit(root), 7999)
            with self.assertRaisesRegex(ValueError, "max_length"):
                reranker._load_model((name, 2, 8192, 1))
            with patch.object(reranker, "version", return_value="5.4.1"), self.assertRaisesRegex(RuntimeError, "CVE-2026-68770"):
                reranker._load_model((name, 2, 512, 1))

    def test_direct_load_validates_artifact_before_framework_import(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            synthetic_artifact(root)
            modules = root / "modules.json"
            architecture = json.loads(modules.read_text())
            architecture[-1]["type"] = "untrusted.remote.Module"
            modules.write_text(json.dumps(architecture))
            with patch.object(reranker, "version") as framework, self.assertRaisesRegex(ValueError, "architecture"):
                reranker._load_model((name, 2, 512, 1))
            framework.assert_not_called()

    def test_safe_offline_complete_model_load_and_configuration_reuse(self):
        fake_torch = SimpleNamespace(
            set_num_threads=MagicMock(), float32=object(),
            nn=SimpleNamespace(Identity=MagicMock(return_value="identity")),
        )
        model = MagicMock()
        model.num_labels = 1
        model.tokenizer.is_fast = True
        constructor = MagicMock(return_value=model)
        with tempfile.TemporaryDirectory() as name, \
                patch.dict(os.environ), \
                patch.dict(sys.modules, {"torch": fake_torch,
                                        "sentence_transformers": SimpleNamespace(CrossEncoder=constructor)}), \
                patch.object(reranker, "version", return_value="5.6.0"), \
                patch.object(reranker, "_cached_model", None), \
                patch.object(reranker, "_cached_config", None):
            synthetic_artifact(Path(name))
            config = (name, 2, 512, 1)
            self.assertEqual(reranker._load_model(config), (model, True))
            self.assertEqual(reranker._load_model(config), (model, False))
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")
            constructor.assert_called_once_with(
                name, device="cpu", backend="torch", local_files_only=True,
                trust_remote_code=False, activation_fn="identity", max_length=512,
                model_kwargs={"torch_dtype": fake_torch.float32, "attn_implementation": "sdpa"},
            )
            fake_torch.set_num_threads.assert_called_once_with(1)
            model.to.assert_called_once_with(device="cpu", dtype=fake_torch.float32)
            model.eval.assert_called_once_with()
            model.tokenizer.backend_tokenizer.no_truncation.assert_called_once_with()
            model.tokenizer.backend_tokenizer.no_padding.assert_called_once_with()

    def test_invalid_configuration_and_missing_artifact(self):
        options = dict(model_dir=".", batch_size=2, max_length=512, threads=1)
        for key, value in [("batch_size", True), ("threads", 0), ("max_length", -1), ("model_dir", "does-not-exist")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                reranker.score_candidates("query", [{"text": "passage"}], **{**options, key: value})

    def test_output_shape_and_finiteness_fail_whole_call(self):
        fake_torch = SimpleNamespace(inference_mode=nullcontext)
        model = MagicMock()
        model.tokenizer = MagicMock()
        rows = [{"text": "one", "score": .9}, {"text": "two", "score": .1}]
        original = deepcopy(rows)
        cases = [((2, 2), [1., 2.], True), ((1,), [1.], True), ((2,), [float("nan"), 2.], True),
                 ((2,), [1., float("inf")], True), ((2,), [1., 2.], False)]
        for shape, values, floating in cases:
            output = MagicMock()
            output.shape = shape
            output.is_floating_point.return_value = floating
            output.detach.return_value.cpu.return_value.float.return_value.reshape.return_value.tolist.return_value = values
            model.return_value = {"scores": output}
            with patch.dict("sys.modules", {"torch": fake_torch}), patch.object(reranker, "_load_model", return_value=(model, False)), patch.object(reranker, "_prepare_pairs", return_value=([{}, {}], [])):
                with self.subTest(shape=shape, values=values), self.assertRaises(ValueError):
                    reranker.score_candidates("query", rows, model_dir=".", batch_size=2, max_length=512, threads=1)
            self.assertEqual(reranker.scoring_details(), {})
        self.assertEqual(rows, original)

    def test_successful_scoring_batches_and_reports_independent_measurements(self):
        fake_torch = SimpleNamespace(inference_mode=MagicMock(side_effect=nullcontext))
        model = MagicMock()
        rows = [candidate("one"), candidate("two"), candidate("three")]
        original = deepcopy(rows)
        outputs = []
        for values in ([2.0, -1.0], [0.5]):
            output = MagicMock()
            output.shape = (len(values), 1)
            output.is_floating_point.return_value = True
            output.detach.return_value.cpu.return_value.float.return_value.reshape.return_value.tolist.return_value = values
            outputs.append({"scores": output})
        model.side_effect = outputs
        counts = [{"pair_tokens": 10}] * 3
        with patch.dict(sys.modules, {"torch": fake_torch}), \
                patch.object(reranker, "_load_model", return_value=(model, True)), \
                patch.object(reranker, "_prepare_pairs", return_value=([{}, {}, {}], counts)):
            scores = reranker.score_candidates("query", rows, model_dir=".", batch_size=2, max_length=512, threads=1)
        self.assertEqual(scores, [2.0, -1.0, 0.5])
        self.assertEqual(rows, original)
        self.assertEqual(model.call_count, 2)
        fake_torch.inference_mode.assert_called_once_with()
        self.assertEqual([len(call.args[0]) for call in model.tokenizer.pad.call_args_list], [2, 1])
        details = reranker.scoring_details()
        self.assertTrue(details["model_loaded"])
        self.assertEqual(details["token_counts"], counts)
        details["token_counts"][0]["pair_tokens"] = 99
        self.assertEqual(reranker.scoring_details()["token_counts"][0]["pair_tokens"], 10)


class FramingTests(unittest.TestCase):
    def test_malformed_and_partial_frames_fail_without_unbounded_reads(self):
        for payload in (b"", b"[]", b"{", b"\xff", b'{"scores":[]}'):
            frame = struct.pack("!i", len(payload)) + payload
            chunks = [frame[:2], frame[2:4], payload]
            with self.subTest(payload=payload), \
                    patch.object(reranker.select, "select", return_value=([7], [], [])), \
                    patch.object(reranker.os, "read", side_effect=chunks):
                if payload == b'{"scores":[]}':
                    self.assertEqual(reranker._receive_message(MagicMock(), time.monotonic() + 1, "timeout"), {"scores": []})
                else:
                    with self.assertRaisesRegex(reranker._WorkerFailure, "malformed_reply"):
                        reranker._receive_message(MagicMock(), time.monotonic() + 1, "timeout")
        with patch.object(reranker.select, "select", return_value=([7], [], [])), \
                patch.object(reranker.os, "read", return_value=b""):
            with self.assertRaisesRegex(reranker._WorkerFailure, "worker_eof"):
                reranker._receive_message(MagicMock(), time.monotonic() + 1, "timeout")

    def test_expired_deadline_never_reads_or_writes(self):
        with patch.object(reranker.os, "write") as write, patch.object(reranker.os, "read") as read:
            with self.assertRaisesRegex(reranker._WorkerFailure, "inference_timeout"):
                reranker._send_message(MagicMock(), {"query": "text"}, time.monotonic() - 1)
            with self.assertRaisesRegex(reranker._WorkerFailure, "load_timeout"):
                reranker._receive_message(MagicMock(), time.monotonic() - 1, "load_timeout")
            read.assert_not_called()
            write.assert_not_called()

class ProfileTests(unittest.TestCase):
    def test_shared_artifact_validation_and_profile(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            profile = synthetic_artifact(root)
            self.assertEqual(reranker.validate_profile(root / "reranker-profile.json"), profile)
            self.assertEqual(reranker.validate_artifact(root, profile["model_id"], profile["revision"]),
                             {"model_id": profile["model_id"], "revision": profile["revision"]})
            (root / "tokenizer_config.json").write_text('{"model_max_length":512}')
            with self.assertRaisesRegex(ValueError, "supported limit"):
                reranker.validate_artifact(root, profile["model_id"], profile["revision"], 1024)
            (root / "4_Dense/model.safetensors").unlink()
            with self.assertRaisesRegex(ValueError, "incomplete"):
                reranker.validate_profile(root / "reranker-profile.json")

    def test_profile_requires_exact_pinned_explicit_settings(self):
        invalid = [
            ("model_id", ""), ("model_id", "cross-encoder/ms-marco-MiniLM-L6-v2"),
            ("revision", "main"), ("revision", ""), ("batch_size", True),
            ("batch_size", 0), ("threads", -1), ("threads", 1.0), ("max_length", 4096),
            ("max_length", True), ("load_timeout_seconds", float("nan")),
            ("load_timeout_seconds", float("inf")), ("load_timeout_seconds", 10**1000),
            ("inference_timeout_seconds", True), ("inference_timeout_seconds", 0),
            ("inference_timeout_seconds", "1"), ("extra", "unexpected"),
        ]
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            profile = synthetic_artifact(root)
            path = root / "reranker-profile.json"
            for key, value in invalid:
                path.write_text(json.dumps({**profile, key: value}))
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    reranker.validate_profile(path)
            for key in profile:
                path.write_text(json.dumps({name: value for name, value in profile.items() if name != key}))
                with self.subTest(missing=key), self.assertRaises(ValueError):
                    reranker.validate_profile(path)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                reranker.validate_profile(path)

    def test_artifact_identity_modules_and_nonempty_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            profile = synthetic_artifact(root)
            manifest = root / "reranker-artifact.json"
            manifest.write_text(json.dumps({"model_id": profile["model_id"], "revision": "wrong"}))
            with self.assertRaisesRegex(ValueError, "identity differs"):
                reranker.validate_profile(root / "reranker-profile.json")
            manifest.write_text(json.dumps({key: profile[key] for key in ("model_id", "revision")}))
            modules = root / "modules.json"
            original = modules.read_text()
            altered = json.loads(original)
            altered[-1]["path"] = "../outside-model"
            modules.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, "architecture"):
                reranker.validate_profile(root / "reranker-profile.json")
            modules.write_text(original)
            (root / "3_LayerNorm/model.safetensors").write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                reranker.validate_profile(root / "reranker-profile.json")

    def test_minilm_remains_available_to_experiments_only(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            model_id = "cross-encoder/ms-marco-MiniLM-L6-v2"
            profile = synthetic_artifact(root, model_id=model_id, revision=reranker.MODEL_REVISIONS[model_id])
            self.assertEqual(reranker.validate_artifact(root, model_id, profile["revision"])["model_id"], model_id)
            with self.assertRaisesRegex(ValueError, "Ettin"):
                reranker.validate_profile(root / "reranker-profile.json")
            (root / "modules.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "non-modular"):
                reranker.validate_artifact(root, model_id, profile["revision"])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.runtime = reranker._Runtime()
        self.addCleanup(self.runtime.close)
        replacement = patch.object(reranker, "_runtime", self.runtime)
        replacement.start()
        self.addCleanup(replacement.stop)
        worker = patch.object(reranker, "_worker_main", fake_worker)
        worker.start()
        self.addCleanup(worker.stop)
        self.rows = [candidate("one", score=.9), candidate("practice one", "practice", .8),
                     candidate("two", score=.7), candidate("three", score=.1),
                     candidate("practice two", "practice", .2)]

    def configure(self, mode="success", **overrides):
        root = Path(self.directory.name) / mode
        profile = synthetic_artifact(root, **overrides)
        environment = patch.dict(os.environ, {"NESTI_RERANKER_MODEL_PATH": str(root)})
        environment.start()
        self.addCleanup(environment.stop)
        return root, profile

    def test_real_spawn_warm_reuse_stable_lanes_and_untouched_metadata(self):
        self.configure()
        original = deepcopy(self.rows)
        slots = ["php", "practice", "php"]
        first = reranker.rerank_candidates("private query", self.rows, slots)
        pid = self.runtime.process.pid
        second = reranker.rerank_candidates("second query", self.rows, slots)
        self.assertEqual(self.runtime.process.pid, pid)
        self.assertEqual(first, second)
        self.assertEqual([row["text"] for row in first], ["three", "practice two", "two"])
        self.assertEqual([row["stack"] for row in first], slots)
        self.assertEqual([row["score"] for row in first], [.1, .2, .7])
        self.assertEqual([row["rerank_score"] for row in first], [3., 4., 2.])
        self.assertEqual(len({row["rerank_model"] for row in first}), 1)
        for row, source in zip(first, [self.rows[3], self.rows[4], self.rows[2]]):
            self.assertEqual({key: value for key, value in row.items() if not key.startswith("rerank_")}, source)
            self.assertIsNot(row, source)
        self.assertEqual(self.rows, original)
        self.runtime.close()
        with self.assertRaises(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)
        self.assertIsNone(self.runtime.connection)

    def test_equal_scores_preserve_positions_within_lanes(self):
        self.configure("ties")
        selected = reranker.rerank_candidates("query", self.rows, ["php", "practice", "php"])
        self.assertEqual([row["text"] for row in selected], ["one", "practice one", "two"])

    def test_busy_returns_immediately_without_queue_or_disable(self):
        with self.runtime.lock, patch.object(reranker.multiprocessing, "get_context") as spawn:
            started = time.monotonic()
            self.assertIsNone(reranker.rerank_candidates("query", self.rows, ["php"]))
            self.assertLess(time.monotonic() - started, .2)
            spawn.assert_not_called()
        self.assertEqual(self.runtime.unavailable_reason, "")
        self.configure()
        self.assertIsNotNone(reranker.rerank_candidates("query", self.rows, ["php"]))

    def test_invalid_and_empty_inputs_do_no_work_and_do_not_latch(self):
        invalid = [
            ("", self.rows, ["php"]), ("query", [{}], ["php"]),
            ("query", [{**self.rows[0], "text": " "}], ["php"]),
            ("query", [{**self.rows[0], "text": 1}], ["php"]),
            ("query", [{**self.rows[0], "score": float("nan")}], ["php"]),
            ("query", [{**self.rows[0], "score": True}], ["php"]),
            ("query", [{**self.rows[0], "stack": "other"}], ["php"]),
            ("query", self.rows, ["vue"]), ("query", self.rows, ["php"] * 4),
            ("query", self.rows, ["other"]), ("query", self.rows, []),
            ("query", self.rows * 5, ["php"]), ("query", self.rows, ["php"] * 7),
            ("query", [], ["php"]), ("query", None, ["php"]),
            ("query", self.rows, None),
            ("x" * (reranker._MAX_QUERY_BYTES + 1), self.rows, ["php"]),
            ("é" * (reranker._MAX_QUERY_BYTES // 2 + 1), self.rows, ["php"]),
            ("query", [candidate("x" * (reranker._MAX_PASSAGE_BYTES + 1))], ["php"]),
            ("query", [candidate("é" * (reranker._MAX_PASSAGE_BYTES // 2 + 1))], ["php"]),
            ("\ud800", self.rows, ["php"]),
        ]
        with patch.object(self.runtime, "score", side_effect=AssertionError("must not send")) as score:
            self.assertEqual(reranker.rerank_candidates("", [], []), [])
            for query, rows, slots in invalid:
                with self.subTest(query=query[:20] if isinstance(query, str) else query, slots=slots):
                    self.assertIsNone(reranker.rerank_candidates(query, rows, slots))
            score.assert_not_called()
        self.assertEqual(self.runtime.unavailable_reason, "")

    def test_invalid_profile_latches_without_spawning(self):
        root, profile = self.configure()
        profile["threads"] = True
        (root / "reranker-profile.json").write_text(json.dumps(profile))
        with patch.object(reranker.multiprocessing, "get_context") as spawn:
            self.assertIsNone(reranker.rerank_candidates("query", self.rows, ["php"]))
            profile["threads"] = 1
            (root / "reranker-profile.json").write_text(json.dumps(profile))
            self.assertIsNone(reranker.rerank_candidates("query", self.rows, ["php"]))
            spawn.assert_not_called()
        self.assertEqual(self.runtime.unavailable_reason, "invalid_profile_or_artifact")

    def test_worker_failures_are_reaped_bounded_and_latched(self):
        modes = {
            "load_timeout": "load_timeout", "load_error": "load_error",
            "bad_ready": "malformed_ready", "load_exit": "worker_eof",
            "inference_timeout": "inference_timeout", "inference_error": "inference_error",
            "inference_exit": "worker_eof", "inference_raise": "worker_eof",
            "partial_reply": "inference_timeout", "oversized_reply": "malformed_reply",
            "wrong_count": "malformed_scores", "wrong_shape": "malformed_scores",
            "nan": "malformed_scores", "inf": "malformed_scores", "bool": "malformed_scores",
            "ignore_terminate": "inference_timeout", "send_timeout": "inference_timeout",
        }
        for mode, expected in modes.items():
            with self.subTest(mode=mode):
                self.runtime = reranker._Runtime()
                self.addCleanup(self.runtime.close)
                self.configure(mode, load_timeout_seconds=.15 if mode == "load_timeout" else 5.,
                               inference_timeout_seconds=.15)
                pids = []
                close = self.runtime.close

                def record_close():
                    if self.runtime.process is not None and self.runtime.process.pid is not None:
                        pids.append(self.runtime.process.pid)
                    close()

                rows = [candidate("x" * reranker._MAX_PASSAGE_BYTES) for _ in range(20)] if mode == "send_timeout" else self.rows
                query = "x" * reranker._MAX_QUERY_BYTES if mode == "send_timeout" else "private failure query"
                with patch.object(reranker, "_runtime", self.runtime), patch.object(self.runtime, "close", side_effect=record_close), \
                        patch.object(reranker.multiprocessing, "get_context", wraps=multiprocessing.get_context) as spawn, \
                        self.assertLogs("reranker", level="INFO") as logs:
                    started = time.monotonic()
                    self.assertIsNone(reranker.rerank_candidates(query, rows, ["php"]))
                    self.assertLess(time.monotonic() - started, 6.)
                    self.assertEqual(self.runtime.unavailable_reason, expected)
                    self.assertIsNone(reranker.rerank_candidates("query again", rows, ["php"]))
                    spawn.assert_called_once_with("spawn")
                self.assertEqual(len(pids), 1)
                with self.assertRaises(ChildProcessError):
                    os.waitpid(pids[0], os.WNOHANG)
                self.assertIsNone(self.runtime.connection)
                self.assertIsNone(self.runtime.process)
                summaries = [line for line in logs.output if "Rerank candidates=" in line]
                self.assertEqual(len(summaries), 2)
                self.assertEqual(sum("until process restart" in line for line in logs.output), 1)
                self.assertTrue(all("private failure query" not in line and "practice one" not in line for line in logs.output))

    def test_worker_dying_after_success_is_not_restarted(self):
        self.configure()
        self.assertIsNotNone(reranker.rerank_candidates("query", self.rows, ["php"]))
        self.runtime.process.kill()
        self.runtime.process.join(2)
        with patch.object(reranker.multiprocessing, "get_context") as spawn:
            self.assertIsNone(reranker.rerank_candidates("query", self.rows, ["php"]))
            self.assertIsNone(reranker.rerank_candidates("query", self.rows, ["php"]))
            spawn.assert_not_called()
        self.assertEqual(self.runtime.unavailable_reason, "worker_exited")

    def test_spawn_failures_close_both_pipe_ends_and_latch(self):
        self.configure()
        for stage in ("construct", "start"):
            runtime = reranker._Runtime()
            context = MagicMock()
            parent, child = MagicMock(), MagicMock()
            context.Pipe.return_value = (parent, child)
            if stage == "construct":
                context.Process.side_effect = OSError("cannot construct")
            else:
                process = context.Process.return_value
                process.start.side_effect = OSError("cannot start")
                process.is_alive.return_value = False
            with self.subTest(stage=stage), patch.object(reranker.multiprocessing, "get_context", return_value=context):
                self.assertEqual(runtime.score("query", ["passage"]), (None, "worker_error"))
                self.assertEqual(runtime.score("query", ["passage"]), (None, "unavailable"))
            parent.close.assert_called_once_with()
            child.close.assert_called_once_with()
            self.assertIsNone(runtime.process)
            self.assertIsNone(runtime.connection)

    def test_pipe_close_error_does_not_skip_child_reaping(self):
        runtime = reranker._Runtime()
        runtime.connection = MagicMock()
        runtime.connection.close.side_effect = OSError("already closed")
        process = runtime.process = MagicMock()
        process.is_alive.side_effect = [True, True, False]
        runtime.close()
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual(process.join.call_count, 2)
        process.close.assert_called_once_with()

    def test_import_does_not_load_frameworks_or_graph(self):
        subprocess.run(
            [sys.executable, "-c", "import sys; import reranker; "
             "assert not any(name in sys.modules for name in "
             "('torch', 'sentence_transformers', 'transformers', 'graph.nodes', 'prompt_builder')); "
             "assert reranker._runtime.process is None"],
            check=True, timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
