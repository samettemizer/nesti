"""Standalone CPU reranker experiment; never imported by the production graph.

Only one model/configuration is resident. Calls are sequential and set PyTorch's
process-wide thread count: run each benchmark configuration in its own process.
The complete CrossEncoder is forwarded on token IDs, without a decode/re-encode
round trip or a reconstructed classification head.
"""

from __future__ import annotations

from copy import deepcopy
import gc
from importlib.metadata import version
import json
import logging
import math
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)

_QUERY_LIMIT = 128
_QUERY_HEAD = 96
_QUERY_TAIL = 32
_cached_model: Any = None
_cached_config: tuple[str, int, int, int] | None = None
_details: dict = {}


def scoring_details() -> dict:
    """Return independent measurements of the last successful scoring call.

    Empty input records zero timings and no tokens; a failed call clears the
    measurements. Timings are seconds. ``token_counts`` contains one dictionary
    per input position with original/effective query/passage token counts,
    ``special_tokens`` and unpadded ``pair_tokens``. ``model_loaded`` distinguishes
    a cold load from reuse. These are observations, not quality or SLA claims.
    """
    return deepcopy(_details)


def _positive_integer(name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _artifact_limit(directory: Path) -> int:
    limits = []
    for filename, field in (
        ("config.json", "max_position_embeddings"),
        ("tokenizer_config.json", "model_max_length"),
    ):
        with (directory / filename).open(encoding="utf-8") as handle:
            config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError(f"{filename} must contain an object")
        value = config.get(field)
        if value is not None:
            _positive_integer(f"{filename}:{field}", value)
            # Hugging Face uses a huge sentinel when the tokenizer has no limit.
            if value < 10**12:
                limits.append(value)
    if not limits:
        raise ValueError("artifact must declare a finite supported sequence length")
    return min(limits)


def _load_model(config: tuple[str, int, int, int]) -> tuple[Any, bool]:
    global _cached_model, _cached_config
    if _cached_config == config and _cached_model is not None:
        return _cached_model, False

    # Release the previous configuration before allocating a replacement model.
    _cached_model = None
    _cached_config = None
    gc.collect()
    directory, _batch_size, max_length, threads = config
    if max_length > _artifact_limit(Path(directory)):
        raise ValueError("max_length exceeds the local artifact's supported limit")

    installed = version("sentence-transformers")
    release = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\.post\d+)?(?:\+[\w.]+)?", installed)
    if release is None or tuple(map(int, release.groups())) < (5, 6, 0):
        raise RuntimeError(
            "sentence-transformers >=5.6.0 is required: earlier versions have "
            "CVE-2026-68770; safe-version real-model compatibility is not yet validated"
        )

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from sentence_transformers import CrossEncoder

    torch.set_num_threads(threads)
    model = CrossEncoder(
        directory,
        device="cpu",
        backend="torch",
        local_files_only=True,
        trust_remote_code=False,
        activation_fn=torch.nn.Identity(),
        max_length=max_length,
        model_kwargs={"torch_dtype": torch.float32, "attn_implementation": "sdpa"},
    )
    model.to(device="cpu", dtype=torch.float32)
    model.eval()
    if model.num_labels != 1:
        raise ValueError("reranking requires exactly one raw score per pair")
    tokenizer = model.tokenizer
    if not tokenizer.is_fast:
        raise ValueError("the experiment requires the artifact's fast tokenizer")
    # Encode full texts first; truncation is applied to Encoding objects below.
    tokenizer.backend_tokenizer.no_truncation()
    tokenizer.backend_tokenizer.no_padding()
    _cached_model, _cached_config = model, config
    return model, True


def _prepare_pairs(tokenizer: Any, query: str, candidates: list[dict], max_length: int) -> tuple[list[dict], list[dict]]:
    backend = tokenizer.backend_tokenizer
    query_encoding = backend.encode(query, add_special_tokens=False)
    original_query_tokens = len(query_encoding.ids)
    if original_query_tokens == 0:
        raise ValueError("query produced no tokenizer tokens")
    if original_query_tokens > _QUERY_LIMIT:
        head = deepcopy(query_encoding)
        head.truncate(_QUERY_HEAD, direction="right")
        query_encoding.truncate(_QUERY_TAIL, direction="left")
        query_encoding = type(query_encoding).merge([head, query_encoding], growing_offsets=False)
    effective_query_tokens = len(query_encoding.ids)
    special_tokens = tokenizer.num_special_tokens_to_add(pair=True)
    capacity = max_length - effective_query_tokens - special_tokens
    if capacity < 1:
        raise ValueError("max_length leaves no passage tokens after the bounded query and special tokens")

    pairs, counts = [], []
    for candidate in candidates:
        passage = backend.encode(candidate["text"], add_special_tokens=False)
        original_passage_tokens = len(passage.ids)
        if original_passage_tokens == 0:
            raise ValueError("passage produced no tokenizer tokens")
        if original_passage_tokens > capacity:
            passage.truncate(capacity, direction="right")
        encoded = backend.post_process(query_encoding, passage, add_special_tokens=True)
        effective_passage_tokens = len(passage.ids)
        pair_tokens = len(encoded.ids)
        if pair_tokens != effective_query_tokens + effective_passage_tokens + special_tokens or pair_tokens > max_length:
            raise ValueError("tokenizer pair construction violated the token budget")
        row = {"input_ids": encoded.ids, "attention_mask": encoded.attention_mask}
        if "token_type_ids" in tokenizer.model_input_names:
            row["token_type_ids"] = encoded.type_ids
        pairs.append(row)
        counts.append({
            "original_query_tokens": original_query_tokens,
            "effective_query_tokens": effective_query_tokens,
            "original_passage_tokens": original_passage_tokens,
            "effective_passage_tokens": effective_passage_tokens,
            "special_tokens": special_tokens,
            "pair_tokens": pair_tokens,
        })
    return pairs, counts


def score_candidates(
    query: str,
    candidates: list[dict],
    *,
    model_dir: str,
    batch_size: int,
    max_length: int,
    threads: int,
) -> list[float]:
    """Return finite raw scores in input order, without changing candidate data.

    Empty candidates require no configuration, framework import or model load.
    Malformed text/configuration, unavailable artifacts/dependencies and any
    model/tokenizer/output failure raise; no partial or synthetic scores escape.
    Stable ranking belongs to the caller: sort input positions descending by
    score, retaining original positions on ties.
    """
    global _details
    _details = {}
    started = perf_counter()
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list of dictionaries")
    if not candidates:
        _details = {
            "load_seconds": 0.0, "inference_seconds": 0.0,
            "tokenization_seconds": 0.0, "total_seconds": 0.0,
            "token_counts": [], "model_loaded": False,
        }
        return []
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a nonblank string")
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict) or not isinstance(candidate.get("text"), str) or not candidate["text"].strip():
            raise ValueError(f"candidate {index}: text must be a nonblank string")
    for name, value in (("batch_size", batch_size), ("max_length", max_length), ("threads", threads)):
        _positive_integer(name, value)
    if not isinstance(model_dir, str) or not model_dir.strip():
        raise ValueError("model_dir must name a local artifact directory")
    directory = Path(model_dir).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("model_dir is not a local artifact directory")

    load_started = perf_counter()
    model, loaded = _load_model((str(directory), batch_size, max_length, threads))
    load_seconds = perf_counter() - load_started if loaded else 0.0
    token_started = perf_counter()
    pairs, counts = _prepare_pairs(model.tokenizer, query, candidates, max_length)
    tokenization_seconds = perf_counter() - token_started
    import torch

    scores = []
    inference_started = perf_counter()
    with torch.inference_mode():
        for start in range(0, len(pairs), batch_size):
            batch = pairs[start:start + batch_size]
            features = model.tokenizer.pad(batch, padding=True, return_tensors="pt")
            # Forward the entire modular CrossEncoder, including its saved head.
            output = model(features)["scores"]
            if tuple(output.shape) not in ((len(batch),), (len(batch), 1)):
                raise ValueError("model returned the wrong score count or shape")
            if not output.is_floating_point():
                raise ValueError("model scores must be floating point")
            values = output.detach().cpu().float().reshape(-1).tolist()
            if any(not math.isfinite(value) for value in values):
                raise ValueError("model returned a non-finite score")
            scores.extend(float(value) for value in values)
    inference_seconds = perf_counter() - inference_started
    if len(scores) != len(candidates):
        raise ValueError("model returned the wrong score count")
    _details = {
        "load_seconds": load_seconds,
        "inference_seconds": inference_seconds,
        "tokenization_seconds": tokenization_seconds,
        "total_seconds": perf_counter() - started,
        "token_counts": counts,
        "model_loaded": loaded,
    }
    return scores
