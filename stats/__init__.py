"""
stats – usage events behind ``nesti /stats``.

Every LLMClient cascade attempt and every graph.tools call made during an issue
run is appended as one JSON event to the Redis list ``nesti:stats:events``.
Recording never raises and never changes the caller's result or exception;
without Redis it is disabled for the process (ConversationStore's degrade).
"""

import functools
import json
import logging
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import redis

logger = logging.getLogger(__name__)

KEY = "nesti:stats:events"
# shortcut: keeps the newest 100k events (~40 MB in Redis and in stats.html); move to a time-series store if longer history is needed
MAX_EVENTS = 100_000
_DEFAULT_REDIS_URL = "redis://nesti-redis:6379/0"

_redis = None          # None = not tried yet, False = unavailable for this process
_run: dict = {}        # run/issue/title of the issue being processed
_last: dict = {}       # model/provider of the run's last successful LLM request
_request: dict | None = None  # cascade attempt in flight, filled by usage()


def _client():
    global _redis
    if _redis is None:
        try:
            _redis = redis.from_url(os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL),
                                    decode_responses=True, socket_connect_timeout=3)
            _redis.ping()
        except Exception as exc:
            logger.warning("Usage stats disabled – Redis unavailable: %s", exc)
            _redis = False
    return _redis or None


def _base(kind: str) -> dict:
    return {"t": time.time(), "kind": kind,
            "project": os.environ.get("GITLAB_PROJECT_PATH", ""), **_run}


def _emit(event: dict) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.pipeline().rpush(KEY, json.dumps(event, default=str)).ltrim(KEY, -MAX_EVENTS, -1).execute()
    except Exception as exc:
        logger.warning("Usage stats event dropped: %s", exc)


def begin(issue_id: int, title: str) -> None:
    """Attribute the following events to one issue run (task_engine, before graph.invoke)."""
    end()
    _run.update(run=f"{issue_id}@{int(time.time())}", issue=issue_id, title=title)


def end() -> None:
    """Close the current issue run; tool calls outside a run are not recorded."""
    _run.clear()
    _last.clear()


def _tokens(usage: dict) -> list[int]:
    """[uncached input, cache read, cache write, output] from any provider's usage block."""
    def n(key: str, source: object = usage) -> int:
        value = source.get(key) if isinstance(source, dict) else None
        return value if type(value) is int and value >= 0 else 0

    if "promptTokenCount" in usage:  # Gemini: prompt includes the cached part, thoughts bill as output
        cached = n("cachedContentTokenCount")
        return [max(n("promptTokenCount") - cached, 0), cached, 0,
                n("candidatesTokenCount") + n("thoughtsTokenCount")]
    if "prompt_tokens" in usage:  # OpenAI chat (OpenRouter, DeepSeek, Ollama, Copilot): prompt includes cached
        cached = n("cached_tokens", usage.get("prompt_tokens_details")) or n("prompt_cache_hit_tokens")
        return [max(n("prompt_tokens") - cached, 0), cached, 0, n("completion_tokens")]
    if "input_tokens_details" in usage:  # Responses API (ChatGPT): input includes cached
        cached = n("cached_tokens", usage.get("input_tokens_details"))
        return [max(n("input_tokens") - cached, 0), cached, 0, n("output_tokens")]
    # Anthropic: input_tokens already excludes cache reads and writes
    return [n("input_tokens"), n("cache_read_input_tokens"),
            n("cache_creation_input_tokens"), n("output_tokens")]


def usage(raw: dict | None) -> None:
    """Add one response's token counters to the attempt in flight (llm_client._log_usage)."""
    if _request is not None and isinstance(raw, dict):
        _request["tok"] = [a + b for a, b in zip(_request["tok"], _tokens(raw))]


@contextmanager
def llm_request(role: str, provider: object) -> Iterator[None]:
    """Time and record one cascade attempt; its exception propagates unchanged."""
    global _request
    event = _request = {**_base("llm"), "role": role, "tok": [0, 0, 0, 0]}
    error = None
    try:
        yield
    except BaseException as exc:
        error = str(exc)[:500] or type(exc).__name__
        raise
    finally:
        _request = None
        name = str(getattr(provider, "name", "unknown"))
        event.update(provider=name, billing=str(getattr(provider, "billing", "")),
                     model=str(getattr(provider, "model", "") or name), ok=error is None,
                     error=error, dur=round(time.time() - event["t"], 3))
        if error is None and _run:
            _last.update(model=event["model"], provider=name)
        _emit(event)


def instrument(namespace: dict) -> None:
    """Wrap every ``tool_*`` function in *namespace* (graph/tools.py globals) so calls in a run are recorded."""
    for name, fn in list(namespace.items()):
        if name.startswith("tool_") and callable(fn):
            namespace[name] = _recorded(fn)


def _recorded(fn: Callable[..., dict]) -> Callable[..., dict]:
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _run:
            return fn(*args, **kwargs)
        event = {**_base("tool"), "tool": fn.__name__.removeprefix("tool_"), **_last}
        result = fn(*args, **kwargs)
        inner = result.get("result") if isinstance(result, dict) else None
        layer_failed = isinstance(inner, dict) and inner.get("passed") is False
        error = (result.get("error") if isinstance(result, dict) else None) or ("test layer failed" if layer_failed else None)
        event.update(ok=isinstance(result, dict) and bool(result.get("success")) and not layer_failed,
                     error=str(error)[:500] if error else None, dur=round(time.time() - event["t"], 3))
        _emit(event)
        return result
    return wrapper


def load() -> list[dict]:
    """Every recorded event, oldest first; [] when Redis is unavailable."""
    client = _client()
    if client is None:
        return []
    try:
        return [json.loads(item) for item in client.lrange(KEY, 0, -1)]
    except Exception as exc:
        logger.warning("Usage stats unreadable: %s", exc)
        return []
