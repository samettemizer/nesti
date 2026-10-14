"""Local CPU scoring and opt-in, bounded reranking in a spawned worker.

Importing this module loads no ML framework. Standalone scoring changes PyTorch's
thread count only in its caller process; production scoring runs in the worker.
The complete CrossEncoder is forwarded without reconstructing its saved head.
"""

from __future__ import annotations

import atexit
from collections import Counter
from copy import deepcopy
import gc
from importlib.metadata import version
import json
import logging
import math
import multiprocessing
import os
from pathlib import Path
import re
import select
import struct
import threading
from time import monotonic, perf_counter
from typing import Any

logger = logging.getLogger(__name__)

MODEL_REVISIONS = {
    "cross-encoder/ettin-reranker-150m-v1": "025501c4e0f9bbeb4c5b198318e0089ff061cc14",
    "cross-encoder/ettin-reranker-68m-v1": "d166fa88ddde3c42bc3ee92f7df476d941c8204a",
    "cross-encoder/ms-marco-MiniLM-L6-v2": "233902d25c440f23af6f7d6e94d2946bac0bee0a",
}
_PROFILE_KEYS = {
    "model_id", "revision", "batch_size", "max_length", "threads",
    "load_timeout_seconds", "inference_timeout_seconds",
}
_DEFAULT_MODEL_PATH = "/opt/nesti-reranker"
_MAX_CANDIDATES = 20
_MAX_SLOTS = 6
# Bound IPC/tokenization, with headroom for issue+plan queries and 2K-char indexed bodies.
_MAX_QUERY_BYTES = 64 * 1024
_MAX_PASSAGE_BYTES = 16 * 1024
_MAX_REPLY_BYTES = 4096
_JOIN_SECONDS = 0.2
_ETTIN_MODULES = (
    ("", "sentence_transformers.base.modules.transformer.Transformer"),
    ("1_Pooling", "sentence_transformers.sentence_transformer.modules.pooling.Pooling"),
    ("2_Dense", "sentence_transformers.base.modules.dense.Dense"),
    ("3_LayerNorm", "sentence_transformers.sentence_transformer.modules.layer_norm.LayerNorm"),
    ("4_Dense", "sentence_transformers.base.modules.dense.Dense"),
)
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


def validate_artifact(
    model_dir: str | Path, model_id: str, revision: str, max_length: int = 512,
) -> dict:
    """Validate pinned local files and sequence limits without importing ML code."""
    if not isinstance(model_id, str) or MODEL_REVISIONS.get(model_id) != revision:
        raise ValueError("model_id/revision is not one of the pinned artifacts")
    _positive_integer("max_length", max_length)
    if max_length not in (512, 1024, 2048):
        raise ValueError("unsupported max_length")
    root = Path(model_dir)
    if not root.is_dir():
        raise ValueError("local model directory is missing")
    manifest = json.loads((root / "reranker-artifact.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("model_id") != model_id or manifest.get("revision") != revision:
        raise ValueError("local artifact identity differs from requested model/revision")
    required = ["config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors"]
    if "ettin" in model_id:
        required += ["modules.json", "config_sentence_transformers.json", "1_Pooling/config.json"]
        for module in ("2_Dense", "3_LayerNorm", "4_Dense"):
            required += [f"{module}/config.json", f"{module}/model.safetensors"]
    if any(not (root / name).is_file() or (root / name).stat().st_size == 0 for name in required):
        raise ValueError("local artifact is incomplete: tokenizer, weights or modular head files are missing")
    if "ettin" in model_id:
        modules = json.loads((root / "modules.json").read_text(encoding="utf-8"))
        expected = [
            {"idx": i, "name": str(i), "path": path, "type": kind}
            for i, (path, kind) in enumerate(_ETTIN_MODULES)
        ]
        if modules != expected:
            raise ValueError("local artifact has an unexpected modular architecture")
    elif (root / "modules.json").exists():
        raise ValueError("MiniLM must use its non-modular CrossEncoder architecture")
    if max_length > _artifact_limit(root):
        raise ValueError("max_length exceeds the local artifact's supported limit")
    return manifest


def validate_profile(profile_path: str | Path) -> dict:
    """Require an explicit deployment profile beside its complete local artifact."""
    path = Path(profile_path).expanduser().resolve()
    with path.open(encoding="utf-8") as handle:
        content = handle.read(16 * 1024 + 1)
    if len(content) > 16 * 1024:
        raise ValueError("profile is too large")
    profile = json.loads(content)
    if not isinstance(profile, dict) or set(profile) != _PROFILE_KEYS:
        raise ValueError("profile must contain exactly the seven deployment settings")
    if profile["model_id"] not in (
        "cross-encoder/ettin-reranker-150m-v1", "cross-encoder/ettin-reranker-68m-v1",
    ):
        raise ValueError("runtime requires a pinned Ettin artifact")
    for name in ("batch_size", "max_length", "threads"):
        _positive_integer(name, profile[name])
    for name in ("load_timeout_seconds", "inference_timeout_seconds"):
        if not _finite(profile[name]) or profile[name] <= 0:
            raise ValueError("profile deadlines must be positive finite numbers")
    validate_artifact(path.parent, profile["model_id"], profile["revision"], profile["max_length"])
    return profile


def _finite(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _load_model(config: tuple[str, int, int, int]) -> tuple[Any, bool]:
    global _cached_model, _cached_config
    if _cached_config == config and _cached_model is not None:
        return _cached_model, False

    # Release the previous configuration before allocating a replacement model.
    _cached_model = None
    _cached_config = None
    gc.collect()
    directory, _batch_size, max_length, threads = config
    root = Path(directory)
    manifest = json.loads((root / "reranker-artifact.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("artifact manifest must contain an object")
    validate_artifact(root, manifest.get("model_id"), manifest.get("revision"), max_length)

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


def _truncate_encoding(encoding: Any, length: int, direction: str) -> None:
    encoding.truncate(length, direction=direction)
    # Tokenizers otherwise multiplies discarded windows when merging/post-processing pairs.
    state = json.loads(encoding.__getstate__())
    state["overflowing"] = []
    encoding.__setstate__(json.dumps(state).encode("utf-8"))


def _prepare_pairs(tokenizer: Any, query: str, candidates: list[dict], max_length: int) -> tuple[list[dict], list[dict]]:
    backend = tokenizer.backend_tokenizer
    query_encoding = backend.encode(query, add_special_tokens=False)
    original_query_tokens = len(query_encoding.ids)
    if original_query_tokens == 0:
        raise ValueError("query produced no tokenizer tokens")
    if original_query_tokens > _QUERY_LIMIT:
        head = deepcopy(query_encoding)
        _truncate_encoding(head, _QUERY_HEAD, "right")
        _truncate_encoding(query_encoding, _QUERY_TAIL, "left")
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
            _truncate_encoding(passage, capacity, "right")
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


class _WorkerFailure(Exception):
    """A bounded, input-free failure reason suitable for operator logs."""


def _send_message(connection: Any, message: dict, deadline: float) -> None:
    payload = json.dumps(message, ensure_ascii=False, allow_nan=False).encode("utf-8")
    pending = memoryview(struct.pack("!i", len(payload)) + payload)
    fd = connection.fileno()
    while pending:
        remaining = deadline - monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise _WorkerFailure("inference_timeout")
        try:
            written = os.write(fd, pending)
        except BlockingIOError:
            continue
        if written == 0:
            raise _WorkerFailure("worker_eof")
        pending = pending[written:]


def _receive_message(connection: Any, deadline: float, timeout_reason: str) -> dict:
    fd = connection.fileno()

    def read_exact(size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            remaining = deadline - monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise _WorkerFailure(timeout_reason)
            try:
                part = os.read(fd, size - len(data))
            except BlockingIOError:
                continue
            if not part:
                raise _WorkerFailure("worker_eof")
            data.extend(part)
        return bytes(data)

    size = struct.unpack("!i", read_exact(4))[0]
    if not 0 < size <= _MAX_REPLY_BYTES:
        raise _WorkerFailure("malformed_reply")
    try:
        reply = json.loads(read_exact(size))
    except (ValueError, UnicodeError) as exc:
        raise _WorkerFailure("malformed_reply") from exc
    if not isinstance(reply, dict):
        raise _WorkerFailure("malformed_reply")
    return reply


def _validated_scores(values: object, count: int) -> list[float]:
    if not isinstance(values, list) or len(values) != count or any(not _finite(value) for value in values):
        raise _WorkerFailure("malformed_scores")
    return [float(value) for value in values]


def _worker_main(connection: Any, model_dir: str, profile: dict) -> None:
    """Load once in the child; exchange only text requests and raw-score replies."""
    options = {key: profile[key] for key in ("batch_size", "max_length", "threads")}
    options["model_dir"] = model_dir
    try:
        try:
            _load_model((model_dir, profile["batch_size"], profile["max_length"], profile["threads"]))
        except Exception:
            connection.send_bytes(b'{"error":"load_error"}')
            return
        connection.send_bytes(b'{"ready":true}')
        while True:
            request = json.loads(connection.recv_bytes())
            try:
                scores = score_candidates(request["query"], [{"text": text} for text in request["texts"]], **options)
                connection.send_bytes(json.dumps({"scores": scores}, allow_nan=False).encode("utf-8"))
            except Exception:
                connection.send_bytes(b'{"error":"inference_error"}')
                return
    except (EOFError, OSError):
        pass
    finally:
        connection.close()


class _Runtime:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: Any = None
        self.connection: Any = None
        self.profile: dict = {}
        self.unavailable_reason = ""

    def close(self) -> None:
        """Stop and reap the worker with bounded waits, including at process exit."""
        process, connection = self.process, self.connection
        self.process = self.connection = None
        if connection is not None:
            try:
                connection.close()
            except OSError:
                pass
        if process is None:
            return
        try:
            if process.is_alive():
                process.terminate()
            process.join(_JOIN_SECONDS)
            if process.is_alive():
                process.kill()
                process.join(_JOIN_SECONDS)
            if not process.is_alive():
                process.close()
        except (OSError, ValueError, AssertionError):
            pass

    def _disable(self, reason: str) -> tuple[None, str]:
        self.close()
        if not self.unavailable_reason:
            self.unavailable_reason = reason
            logger.warning("Reranker unavailable until process restart reason=%s", reason)
        return None, reason

    def score(self, query: str, texts: list[str]) -> tuple[list[float] | None, str]:
        """Return bounded scores, or a fixed failure code; never queue or respawn."""
        if not self.lock.acquire(blocking=False):
            return None, "busy"
        try:
            if self.unavailable_reason:
                return None, "unavailable"
            if self.process is None:
                try:
                    directory = Path(os.environ.get("NESTI_RERANKER_MODEL_PATH", _DEFAULT_MODEL_PATH)).expanduser().resolve()
                    self.profile = validate_profile(directory / "reranker-profile.json")
                except Exception:
                    return self._disable("invalid_profile_or_artifact")
                deadline = monotonic() + self.profile["load_timeout_seconds"]
                context = multiprocessing.get_context("spawn")
                self.connection, child_connection = context.Pipe(duplex=True)
                try:
                    self.process = context.Process(
                        target=_worker_main, args=(child_connection, str(directory), self.profile),
                        name="nesti-reranker", daemon=True,
                    )
                    self.process.start()
                finally:
                    child_connection.close()
                # Connection.send/recv may block after poll; nonblocking framed I/O covers all bytes.
                os.set_blocking(self.connection.fileno(), False)
                ready = _receive_message(self.connection, deadline, "load_timeout")
                if ready == {"error": "load_error"}:
                    raise _WorkerFailure("load_error")
                if set(ready) != {"ready"} or ready["ready"] is not True:
                    raise _WorkerFailure("malformed_ready")
            if not self.process.is_alive():
                raise _WorkerFailure("worker_exited")
            deadline = monotonic() + self.profile["inference_timeout_seconds"]
            _send_message(self.connection, {"query": query, "texts": texts}, deadline)
            reply = _receive_message(self.connection, deadline, "inference_timeout")
            if reply == {"error": "inference_error"}:
                raise _WorkerFailure("inference_error")
            if set(reply) != {"scores"}:
                raise _WorkerFailure("malformed_reply")
            return _validated_scores(reply["scores"], len(texts)), ""
        except _WorkerFailure as exc:
            return self._disable(str(exc))
        except Exception:
            return self._disable("worker_error")
        finally:
            self.lock.release()


_runtime = _Runtime()
atexit.register(_runtime.close)


def rerank_candidates(query: str, candidates: list[dict], slot_stacks: list[str]) -> list[dict] | None:
    """Stable-rank each lane and replay baseline slots, or fail the entire request.

    Inputs remain untouched; the graph owns exact dense fallback. A permanent
    worker failure logs its reason once, followed by per-attempt unavailable summaries.
    """
    started = monotonic()
    count = len(candidates) if isinstance(candidates, list) else 0
    selected: list[dict] = []
    scored = 0
    reason = "invalid_input"
    try:
        if not isinstance(candidates, list) or not isinstance(slot_stacks, list):
            return None
        if not candidates and not slot_stacks:
            reason = "empty"
            return []
        if not 0 < count <= _MAX_CANDIDATES or not 0 < len(slot_stacks) <= _MAX_SLOTS:
            return None
        if not isinstance(query, str) or not query.strip() or len(query.encode("utf-8")) > _MAX_QUERY_BYTES:
            return None
        if any(stack not in ("php", "vue", "practice") for stack in slot_stacks):
            return None
        for row in candidates:
            if (
                not isinstance(row, dict)
                or row.get("stack") not in ("php", "vue", "practice")
                or not isinstance(row.get("text"), str) or not row["text"].strip()
                or len(row["text"].encode("utf-8")) > _MAX_PASSAGE_BYTES
                or not _finite(row.get("score"))
            ):
                return None
        available = Counter(row["stack"] for row in candidates)
        if any(available[stack] < needed for stack, needed in Counter(slot_stacks).items()):
            reason = "missing_lane"
            return None
        scores, reason = _runtime.score(query, [row["text"] for row in candidates])
        if scores is None:
            return None
        scored = len(scores)
        lanes = {
            stack: iter(sorted(
                (i for i, row in enumerate(candidates) if row["stack"] == stack),
                key=scores.__getitem__, reverse=True,
            ))
            for stack in available
        }
        model = f"{_runtime.profile['model_id']}@{_runtime.profile['revision']}"
        for stack in slot_stacks:
            index = next(lanes[stack])
            selected.append({**candidates[index], "rerank_score": scores[index], "rerank_model": model})
        return selected
    except Exception:
        reason = "invalid_input"
        selected = []
        return None
    finally:
        logger.info(
            "Rerank candidates=%d scored=%d selected=%d model=%s revision=%s elapsed_ms=%.1f fallback=%s",
            count, scored, len(selected), _runtime.profile.get("model_id", "unknown"),
            _runtime.profile.get("revision", "unknown"), (monotonic() - started) * 1000, reason or "none",
        )
