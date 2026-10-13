"""Offline scoring boundary regressions; no model, services or downloads."""
from copy import deepcopy
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tokenizers import Tokenizer, models, pre_tokenizers, processors

import reranker


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
        pairs, counts = reranker._prepare_pairs(tok, query, rows, 150)
        self.assertEqual(pairs[0]["input_ids"], [1] + list(range(3, 99)) + list(range(171, 203)) + [2] + [203] * 19 + [2])
        self.assertEqual(counts, [{"original_query_tokens": 200, "effective_query_tokens": 128,
                                  "original_passage_tokens": 1000, "effective_passage_tokens": 19,
                                  "special_tokens": 3, "pair_tokens": 150}])
        self.assertEqual(rows, original)
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
            (root / "config.json").write_text(json.dumps({"max_position_embeddings": 8192}))
            (root / "tokenizer_config.json").write_text(json.dumps({"model_max_length": 7999}))
            self.assertEqual(reranker._artifact_limit(root), 7999)
            with self.assertRaisesRegex(ValueError, "supported limit"):
                reranker._load_model((name, 2, 8192, 1))
            with patch.object(reranker, "version", return_value="5.4.1"), self.assertRaisesRegex(RuntimeError, "CVE-2026-68770"):
                reranker._load_model((name, 2, 512, 1))

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


if __name__ == "__main__":
    unittest.main()
