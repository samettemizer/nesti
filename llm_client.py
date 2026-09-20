"""
llm_client.py – provider cascade for planning and code generation.

Provider roles
──────────────
  Consumer   │   → subscriptions authenticated with `nesti /provider login`
  (first)    │     (Claude Pro/Max, ChatGPT Plus, Antigravity, Copilot).
             │     Flat-rate capacity that is already paid for, so it is
             │     spent before anything that bills per token or per call.
  Local      │   → Ollama (Hermes-3 planner / Qwen3 coder), when enabled.
  Paid API   │   → DeepSeek API, then the Anthropic API (ANTHROPIC_API_KEY)
             │     as the last resort — reached only once every consumer
             │     session in the chain has failed or is logged out.

Cascade rules
─────────────
  • API / timeout failures  → immediate cascade to the next provider within
                              the same attempt; no retry slot consumed.
  • Test failures           → task_engine calls escalate_coder(), which raises
                              the minimum coder tier for the NEXT attempt.
  • Every provider failure and tier escalation emits a Telegram notification.
  • A provider is skipped when it is unavailable — its env vars are absent, or
    (consumer tier) no session is stored for it. Availability is re-checked
    before every attempt, so `nesti /provider login|logout` takes effect
    without restarting the orchestrator.
"""

import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod

import anthropic
import requests

from scripts.oauth import PROVIDERS, TokenStore
from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 8096


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    """Interface every provider must implement."""

    name: str = "unknown"
    # How this provider is paid for. Printed in the orchestrator log next to
    # every test result and in the Merge Request body, so a reviewer can tell
    # at a glance whether a change was produced by a flat-rate subscription
    # or by a per-token API bill.
    billing: str = "platform API"
    model: str = ""

    @property
    def label(self) -> str:
        """`<name> (<billing>, model <model>)` – one line, log/MR ready."""
        model = self.model or "unknown model"
        return f"{self.name} ({self.billing}, model {model})"

    @property
    def available(self) -> bool:
        """Whether this provider can be called at all right now.

        Consulted immediately before every cascade attempt rather than once
        at construction: consumer sessions appear and disappear with
        `nesti /provider login|logout` while the orchestrator keeps running.
        """
        return True

    @abstractmethod
    def generate_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        """Return an implementation plan text.

        If *messages* is provided it is treated as the full conversation history
        (a list of ``{"role": ..., "content": ...}`` dicts); otherwise the call
        is single-turn and built from *user_prompt* (backward-compatible).
        """

    @abstractmethod
    def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        """Return generated code based on an approved plan.

        *messages* has the same meaning as in :meth:`generate_plan`.
        """


# ─────────────────────────────────────────────────────────────────────────────
# Local Ollama clients  (OpenAI-compatible /v1/chat/completions)
# ─────────────────────────────────────────────────────────────────────────────

class _OllamaBase(BaseLLMClient):
    """Shared HTTP logic for any local model served via Ollama."""

    billing = "local model"

    def __init__(
        self,
        url_env: str,
        model_env: str,
        timeout_env: str,
        default_timeout: int,
    ) -> None:
        self.base_url: str = os.environ.get(url_env, "").rstrip("/")
        self.model: str = os.environ.get(model_env, "")
        self.timeout: int = int(os.environ.get(timeout_env, str(default_timeout)))

    @property
    def available(self) -> bool:
        return os.environ.get("LOCAL_LLM_ENABLED", "false").strip().lower() == "true"

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        if not self.available:
            raise RuntimeError(
                f"{self.name} is not configured "
                f"(env vars for URL or model are missing)."
            )
        # Use the supplied conversation history when present, otherwise fall
        # back to a single-turn user message (preserves legacy behaviour).
        payload_messages = messages if messages else [
            {"role": "user", "content": user_prompt}
        ]
        # Inject the system prompt as the first message unless the caller
        # already included one in the history.
        if not any(m.get("role") == "system" for m in payload_messages):
            payload_messages = [
                {"role": "system", "content": system_prompt}
            ] + payload_messages

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            "temperature": 0.7,
            "think": False,
        }
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            text: str = resp.json()["choices"][0]["message"]["content"]
            logger.debug(
                "%s responded (%d chars, %d message(s) sent).",
                self.name,
                len(text),
                len(payload_messages),
            )
            return text
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"{self.name} API error: {exc}") from exc

    def generate_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting plan from %s …", self.name)
        return self._call(system_prompt, user_prompt, messages)

    def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting code from %s …", self.name)
        return self._call(system_prompt, user_prompt, messages)


class HermesLLMClient(_OllamaBase):
    """Hermes-3 – planner"""
    name = "Hermes-3"

    def __init__(self) -> None:
        super().__init__(
            url_env="HERMES3_LLM_URL",
            model_env="HERMES3_LLM_MODEL",
            timeout_env="HERMES3_LLM_TIMEOUT",
            default_timeout=300,
        )

    @property
    def available(self) -> bool:
        return os.environ.get("HERMES3_LLM_ENABLED", "false").strip().lower() == "true"


class QwenLLMClient(_OllamaBase):
    """Qwen3:30b – code generator."""

    name = "Qwen3:30b"

    def __init__(self) -> None:
        super().__init__(
            url_env="LOCAL_LLM_URL",
            model_env="LOCAL_LLM_MODEL",
            timeout_env="LOCAL_LLM_TIMEOUT",
            default_timeout=1800,
        )


# ─────────────────────────────────────────────────────────────────────────────
# DeepSeek API  (OpenAI-compatible)
# ─────────────────────────────────────────────────────────────────────────────

class DeepSeekLLMClient(BaseLLMClient):
    """DeepSeek API – mid-tier paid fallback for both planning and coding."""

    name = "DeepSeek"
    _API_BASE = "https://api.deepseek.com/v1"

    def __init__(self) -> None:
        self.api_key: str = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        self.model: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout: int = int(os.environ.get("DEEPSEEK_TIMEOUT", "300"))

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        if not self.available:
            raise RuntimeError(
                "DeepSeek is not configured (DEEPSEEK_API_KEY missing)."
            )

        payload_messages = messages if messages else [
            {"role": "user", "content": user_prompt}
        ]
        if not any(m.get("role") == "system" for m in payload_messages):
            payload_messages = [
                {"role": "system", "content": system_prompt}
            ] + payload_messages

        logger.debug(
            "%s request – system_prompt: %d chars, %d message(s) in history.",
            self.name,
            len(system_prompt),
            len(payload_messages),
        )

        url = f"{self._API_BASE}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            "temperature": 0.7,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            text: str = resp.json()["choices"][0]["message"]["content"]
            logger.debug("DeepSeek responded (%d chars).", len(text))
            return text
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"DeepSeek API error: {exc}") from exc

    def generate_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting plan from DeepSeek (%s) …", self.model)
        return self._call(system_prompt, user_prompt, messages)

    def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting code from DeepSeek (%s) …", self.model)
        return self._call(system_prompt, user_prompt, messages)


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic Claude  (paid API key – last resort)
# ─────────────────────────────────────────────────────────────────────────────

class AnthropicLLMClient(BaseLLMClient):
    """
    Claude Sonnet over ANTHROPIC_API_KEY – the last-resort *paid* tier.

    A Claude Pro/Max subscription is deliberately NOT handled here: it is a
    separate, higher-priority tier (ClaudeConsumerClient) because Anthropic
    accepts a consumer OAuth token only in a different request shape, and
    because flat-rate capacity that is already paid for must be spent before
    a per-token bill is opened.
    """

    name = "Claude Sonnet (API key)"

    def __init__(self) -> None:
        self.model: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.api_key: str = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        if not self.available:
            raise RuntimeError("Anthropic API is not configured (ANTHROPIC_API_KEY missing).")

        msg_list = messages if messages else [{"role": "user", "content": user_prompt}]
        # Anthropic keeps the system prompt separate and rejects system-role
        # entries inside the messages array, so strip any that were carried in
        # the shared history.
        msg_list = [m for m in msg_list if m.get("role") != "system"]

        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=_DEFAULT_MAX_TOKENS,
            system=system_prompt,
            messages=msg_list,
        )
        return message.content[0].text

    def generate_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting plan from Anthropic %s …", self.model)
        text = self._call(system_prompt, user_prompt, messages)
        logger.debug("Anthropic plan received (%d chars).", len(text))
        return text

    def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting code from Anthropic %s …", self.model)
        text = self._call(system_prompt, user_prompt, messages)
        logger.debug("Anthropic code received (%d chars).", len(text))
        return text


# ─────────────────────────────────────────────────────────────────────────────
# Consumer subscriptions  (nesti /provider login → TokenStore)
# ─────────────────────────────────────────────────────────────────────────────

_TOKEN_STORE: TokenStore | None = None
_TOKEN_STORE_RETRY_AT: float = 0.0
_TOKEN_STORE_RETRY_INTERVAL = 30.0  # seconds between reconnect attempts


def _token_store() -> TokenStore:
    """Process-wide TokenStore, rebuilt after a Redis outage.

    Constructing one opens and pings a Redis connection and availability is
    consulted before every cascade attempt, so it must not be rebuilt per
    call. It must not be cached forever either: TokenStore degrades to an
    empty in-memory dict when Redis is unreachable, which reads exactly like
    "no subscription is logged in" and would silently divert the whole
    pipeline onto the billed APIs for the rest of the process. So a degraded
    store is retried, at most every _TOKEN_STORE_RETRY_INTERVAL seconds.
    """
    global _TOKEN_STORE, _TOKEN_STORE_RETRY_AT  # pylint: disable=global-statement
    now = time.monotonic()
    if _TOKEN_STORE is None or (not _TOKEN_STORE.available and now >= _TOKEN_STORE_RETRY_AT):
        _TOKEN_STORE = TokenStore()
        _TOKEN_STORE_RETRY_AT = now + _TOKEN_STORE_RETRY_INTERVAL
    return _TOKEN_STORE


class _ConsumerLLMBase(BaseLLMClient):
    """
    Shared plumbing for a provider paid for by a consumer subscription.

    "Available" means a session for this provider is in the TokenStore, so a
    provider that was never logged in — or was logged out with
    `nesti /provider logout <name>` — drops out of the cascade with no
    configuration change and no restart.
    """

    billing = "consumer subscription"
    provider_key: str = ""

    def __init__(self) -> None:
        self.timeout: int = int(os.environ.get("NESTI_CONSUMER_TIMEOUT", "600"))

    @property
    def available(self) -> bool:
        try:
            return _token_store().get_token(self.provider_key) is not None
        except Exception:  # pylint: disable=broad-except
            return False

    def _credentials(self) -> dict:
        """Stored credentials, renewed when they are at or near expiry.

        Renewal lives in the provider classes (scripts/oauth.py), which own
        every OAuth endpoint; a renewed credential is written straight back
        so the next issue — and the next process — starts from it.
        """
        store = _token_store()
        token_data = store.get_token(self.provider_key)
        if not token_data:
            raise RuntimeError(
                f"{self.name}: no consumer session stored "
                f"(run 'nesti /provider login {self.provider_key}')."
            )
        fresh = PROVIDERS[self.provider_key].fresh_credentials(token_data)
        if fresh != token_data:
            store.save_token(self.provider_key, fresh)
        return fresh

    @staticmethod
    def _history(user_prompt: str, messages: list[dict] | None) -> list[dict]:
        return list(messages) if messages else [{"role": "user", "content": user_prompt}]

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        raise NotImplementedError

    def generate_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting plan from %s …", self.name)
        return self._call(system_prompt, user_prompt, messages)

    def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        logger.info("Requesting code from %s …", self.name)
        return self._call(system_prompt, user_prompt, messages)


class ClaudeConsumerClient(_ConsumerLLMBase):
    """
    Claude Pro/Max subscription (`nesti /provider login claude`).

    Anthropic accepts a consumer OAuth token only when the request looks like
    Claude Code's own traffic: `Authorization: Bearer` (not the `x-api-key`
    the anthropic SDK sends), the `oauth-2025-04-20` beta header, and a system
    prompt that identifies as Claude Code. That is why this is a raw requests
    call instead of reusing AnthropicLLMClient's SDK path. See CLAUDE.md
    "OAuth Consumer-Provider CLI" for the accepted-risk decision it implements.
    """

    name = "Claude Pro/Max (consumer)"
    provider_key = "claude"
    _API_URL = "https://api.anthropic.com/v1/messages"
    _SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."

    def __init__(self) -> None:
        super().__init__()
        self.model: str = os.environ.get(
            "NESTI_CLAUDE_CONSUMER_MODEL",
            os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        token = self._credentials()["access_token"]
        # Anthropic rejects system-role entries inside `messages`.
        msg_list = [
            m for m in self._history(user_prompt, messages) if m.get("role") != "system"
        ]
        resp = requests.post(
            self._API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "oauth-2025-04-20",
            },
            json={
                "model": self.model,
                "max_tokens": _DEFAULT_MAX_TOKENS,
                "system": f"{self._SYSTEM_PREFIX}\n\n{system_prompt}",
                "messages": msg_list,
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(
                f"{self.name} request failed ({resp.status_code}): {resp.text[:300]}"
            )
        return resp.json()["content"][0]["text"]


class ChatGPTConsumerClient(_ConsumerLLMBase):
    """
    ChatGPT Plus/Pro subscription (`nesti /provider login chatgpt-plus`).

    Talks to the Codex backend the official Codex CLI uses
    (`{chatgpt}/backend-api/codex/responses`, Responses API shape). Three
    things about that endpoint are not optional: the `chatgpt-account-id`
    header (claim `chatgpt_account_id` of the login id_token — captured at
    login, which is why a session stored before this tier existed must log in
    again), `store: false`, and `stream: true` — it only answers as an SSE
    stream, so the text is reassembled from `response.output_text.delta`
    events here.
    """

    name = "ChatGPT Plus (consumer)"
    provider_key = "chatgpt-plus"
    _API_URL = "https://chatgpt.com/backend-api/codex/responses"
    _ORIGINATOR = "codex_cli_rs"

    def __init__(self) -> None:
        super().__init__()
        self.model: str = os.environ.get("NESTI_CHATGPT_MODEL", "gpt-5.1-codex")

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        creds = self._credentials()
        account_id = creds.get("account_id")
        if not account_id:
            raise RuntimeError(
                f"{self.name}: stored session carries no account_id — run "
                "'nesti /provider login chatgpt-plus' again (it is read from "
                "the id_token at login)."
            )

        instructions = [system_prompt]
        input_items: list[dict] = []
        for msg in self._history(user_prompt, messages):
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                instructions.append(content)
                continue
            input_items.append(
                {
                    "type": "message",
                    "role": role,
                    "content": [
                        {
                            "type": "output_text" if role == "assistant" else "input_text",
                            "text": content,
                        }
                    ],
                }
            )

        payload = {
            "model": self.model,
            "instructions": "\n\n".join(part for part in instructions if part),
            "input": input_items,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "store": False,
            "stream": True,
            "include": [],
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {creds['access_token']}",
            "chatgpt-account-id": account_id,
            "OpenAI-Beta": "responses=experimental",
            "originator": self._ORIGINATOR,
            "session-id": str(uuid.uuid4()),
        }
        with requests.post(
            self._API_URL, headers=headers, json=payload, timeout=self.timeout, stream=True
        ) as resp:
            if not resp.ok:
                raise RuntimeError(
                    f"{self.name} request failed ({resp.status_code}): {resp.text[:300]}"
                )
            return self._read_stream(resp)

    @classmethod
    def _read_stream(cls, resp: requests.Response) -> str:
        deltas: list[str] = []
        completed = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            raw = line[len("data:") :].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type")
            if event_type == "response.output_text.delta":
                deltas.append(event.get("delta") or "")
            elif event_type == "response.completed":
                completed = cls._text_from_response(event.get("response") or {})
            elif event_type in ("response.failed", "error"):
                detail = event.get("error") or (event.get("response") or {}).get("error")
                raise RuntimeError(f"ChatGPT Codex stream failed: {detail}")
        # Deltas are the normal path; the terminal event is the fallback for a
        # response delivered in one piece.
        text = "".join(deltas) or completed
        if not text.strip():
            raise RuntimeError("ChatGPT Codex stream carried no output text.")
        return text

    @staticmethod
    def _text_from_response(response: dict) -> str:
        chunks: list[str] = []
        for item in response.get("output") or []:
            for part in item.get("content") or []:
                if part.get("type") in ("output_text", "text") and part.get("text"):
                    chunks.append(part["text"])
        return "".join(chunks)


class AntigravityConsumerClient(_ConsumerLLMBase):
    """
    Google Antigravity subscription (`nesti /provider login antigravity`).

    Uses the Cloud Code Assist API the Antigravity/Gemini CLI tooling uses:
    the Vertex GenerateContent body is nested under `request`, with `model`
    and `project` as siblings, and the answer arrives under `response`.
    Google access tokens live one hour, so every call goes through
    fresh_credentials() first.
    """

    name = "Antigravity (consumer)"
    provider_key = "antigravity"
    _API_URL = "https://cloudcode-pa.googleapis.com/v1internal:generateContent"

    def __init__(self) -> None:
        super().__init__()
        self.model: str = os.environ.get("NESTI_ANTIGRAVITY_MODEL", "gemini-3-pro-preview")

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        creds = self._credentials()
        instructions = [system_prompt]
        contents: list[dict] = []
        for msg in self._history(user_prompt, messages):
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                instructions.append(content)
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": content}],
                }
            )

        payload = {
            "model": self.model,
            "project": creds.get("project_id"),
            "user_prompt_id": str(uuid.uuid4()),
            "request": {
                "contents": contents,
                "systemInstruction": {
                    "role": "user",
                    "parts": [{"text": "\n\n".join(part for part in instructions if part)}],
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": _DEFAULT_MAX_TOKENS,
                },
            },
        }
        resp = requests.post(
            self._API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {creds['access_token']}",
            },
            json=payload,
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(
                f"{self.name} request failed ({resp.status_code}): {resp.text[:300]}"
            )
        candidates = ((resp.json() or {}).get("response") or {}).get("candidates") or []
        if not candidates:
            raise RuntimeError(f"{self.name} returned no candidates.")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        # Thought parts are reasoning traces, not answer text.
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():
            raise RuntimeError(f"{self.name} returned an empty completion.")
        return text


class CopilotConsumerClient(_ConsumerLLMBase):
    """
    GitHub Copilot subscription (`nesti /provider login copilot`).

    The stored credential is not the chat credential: CopilotProvider.
    fresh_credentials exchanges it for a short-lived session token and reports
    the chat host to use. The chat surface itself is OpenAI-shaped but rejects
    clients that do not identify as an editor integration, hence the
    Copilot-* / Editor-* headers.

    A Personal Access Token cannot drive this tier. Verified against the live
    hosts on 2026-09-20 with a valid "Copilot Requests" PAT: both
    api.githubcopilot.com/chat/completions and /responses answer 400
    "Personal Access Tokens are not supported for this endpoint",
    api.github.com/copilot_internal/v2/token answers 404, and GitHub Models
    (models.github.ai) answers 410 — it is being retired. Only an OAuth token
    issued to an editor integration works, so a PAT-only session (what
    `nesti /provider login copilot` stores today, and what the quota check
    needs) makes this tier unavailable instead of failing every single
    attempt with the same 400.
    """

    name = "GitHub Copilot (consumer)"
    provider_key = "copilot"
    _INTEGRATION_ID = "vscode-chat"
    _OAUTH_TOKEN_PREFIXES = ("gho_", "ghu_")
    _pat_warning_logged = False

    def __init__(self) -> None:
        super().__init__()
        self.model: str = os.environ.get("NESTI_COPILOT_MODEL", "gpt-4.1")

    @property
    def available(self) -> bool:
        try:
            token_data = _token_store().get_token(self.provider_key)
        except Exception:  # pylint: disable=broad-except
            return False
        if not token_data:
            return False
        if str(token_data.get("access_token", "")).startswith(self._OAUTH_TOKEN_PREFIXES):
            return True
        if not CopilotConsumerClient._pat_warning_logged:
            CopilotConsumerClient._pat_warning_logged = True
            logger.warning(
                "Copilot session is a Personal Access Token – GitHub rejects PATs on "
                "every Copilot inference host, so this tier stays out of the cascade "
                "(quota reporting via 'nesti /usage' is unaffected)."
            )
        return False

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        creds = self._credentials()
        provider = PROVIDERS[self.provider_key]
        msg_list = self._history(user_prompt, messages)
        if not any(m.get("role") == "system" for m in msg_list):
            msg_list = [{"role": "system", "content": system_prompt}] + msg_list

        base = (creds.get("chat_api_base") or provider.DEFAULT_CHAT_API).rstrip("/")
        resp = requests.post(
            f"{base}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {creds['session_token']}",
                "Copilot-Integration-Id": self._INTEGRATION_ID,
                "Editor-Version": provider.EDITOR_VERSION,
                "Editor-Plugin-Version": provider.EDITOR_PLUGIN_VERSION,
                "User-Agent": provider.USER_AGENT,
                "Openai-Intent": "conversation-panel",
            },
            json={
                "model": self.model,
                "messages": msg_list,
                "max_tokens": _DEFAULT_MAX_TOKENS,
                "temperature": 0.7,
                "stream": False,
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(
                f"{self.name} request failed ({resp.status_code}): {resp.text[:300]}"
            )
        choices = (resp.json() or {}).get("choices") or []
        if not choices:
            raise RuntimeError(f"{self.name} returned no choices.")
        return choices[0]["message"]["content"]


# Consumption order of the consumer tier. Overridable because which
# subscription should burn first is an operator decision (quota safety, see
# node_on_layer_failure), not a property of the code.
_CONSUMER_CLIENTS: dict[str, type[_ConsumerLLMBase]] = {
    "claude": ClaudeConsumerClient,
    "chatgpt-plus": ChatGPTConsumerClient,
    "antigravity": AntigravityConsumerClient,
    "copilot": CopilotConsumerClient,
}
_DEFAULT_CONSUMER_PRIORITY = "claude,chatgpt-plus,antigravity,copilot"


def build_consumer_clients() -> list[_ConsumerLLMBase]:
    """Consumer tier in consumption order (`NESTI_CONSUMER_PRIORITY`).

    Every known provider is instantiated whether or not it is logged in;
    `available` decides per attempt, so a login that happens while the
    orchestrator loop is running is picked up on the next call.
    """
    raw = os.environ.get("NESTI_CONSUMER_PRIORITY", _DEFAULT_CONSUMER_PRIORITY)
    clients: list[_ConsumerLLMBase] = []
    seen: set[str] = set()
    for key in (part.strip().lower() for part in raw.split(",")):
        if not key or key in seen:
            continue
        client_cls = _CONSUMER_CLIENTS.get(key)
        if client_cls is None:
            logger.warning(
                "Unknown consumer provider '%s' in NESTI_CONSUMER_PRIORITY – ignored.", key
            )
            continue
        seen.add(key)
        clients.append(client_cls())
    return clients


# ─────────────────────────────────────────────────────────────────────────────
# Unified client with cascading fallback
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Unified LLM client with a consumer-first cascading fallback.

    Chain order (planners and coders alike):
        0..n  consumer subscriptions, in NESTI_CONSUMER_PRIORITY order —
              already paid for, so they are spent first and one failing
              subscription simply hands over to the next one;
        then  the local Ollama tier, when enabled;
        then  DeepSeek, then the Anthropic API key — the per-token billed
              channels, reached only when every consumer session ahead of
              them is logged out or failing.

    Coding cascade (hybrid):
        • API / timeout errors  → immediate cascade within the same attempt.
        • Test failures         → task_engine calls escalate_coder() to raise
                                  _min_coder_tier before the next attempt.

    The two cascade mechanisms are independent:
        – _min_coder_tier is the floor; generate_code() starts there each call.
        – If the floor provider has an API error, it cascades upward within
          that same call and also advances _min_coder_tier so the next call
          won't retry a known-broken provider.

    Unavailable tiers are skipped at attempt time, never removed: a consumer
    session logged in (or out) while the loop runs changes the next call.

    Telegram notifications are sent on every failure and tier escalation.
    """

    def __init__(self) -> None:
        # Instantiate providers once; the consumer clients, DeepSeek and
        # Claude are shared across both chains to avoid duplicate client
        # objects (and, for the consumer tier, duplicate token lookups).
        consumers = build_consumer_clients()
        hermes = HermesLLMClient()
        qwen = QwenLLMClient()
        deepseek = DeepSeekLLMClient()
        claude = AnthropicLLMClient()

        # ── Planner chain: consumers → Hermes-3 → DeepSeek → Claude API ──
        self._planners: list[BaseLLMClient] = [*consumers]
        if hermes.available:
            self._planners.append(hermes)
        else:
            logger.warning(
                "Hermes-3 not enabled (HERMES3_LLM_URL / HERMES3_LLM_MODEL missing) "
                "– excluded from planner chain."
            )
        if deepseek.available:
            self._planners.append(deepseek)
        else:
            logger.warning(
                "DeepSeek not configured (DEEPSEEK_API_KEY missing) "
                "– excluded from planner chain."
            )
        self._planners.append(claude)  # Claude is always the final safety net

        # ── Coder chain: consumers → Qwen → DeepSeek → Claude API ────────
        self._coders: list[BaseLLMClient] = [*consumers]
        if qwen.available:
            self._coders.append(qwen)
        else:
            logger.warning(
                "Qwen3 not enabled (LOCAL_LLM_URL / LOCAL_LLM_MODEL missing) "
                "– excluded from coder chain."
            )
        if deepseek.available:
            self._coders.append(deepseek)
        else:
            logger.warning(
                "DeepSeek not configured – excluded from coder chain."
            )
        self._coders.append(claude)

        # Minimum coder tier; raised by escalate_coder() after test failures
        self._min_coder_tier: int = 0

        # Provider that last answered successfully. The pipeline logs and the
        # Merge Request body attribute the work to it, so it must be the
        # provider that actually served the call, not the chain head.
        self._last_planner: BaseLLMClient | None = None
        self._last_coder: BaseLLMClient | None = None

        logger.info(
            "LLM chains ready – Planners: [%s] | Coders: [%s]",
            ", ".join(p.name for p in self._planners),
            ", ".join(c.name for c in self._coders),
        )
        logger.info(
            "Consumer tier: %s",
            ", ".join(
                f"{c.name}{'' if c.available else ' (no session)'}" for c in consumers
            )
            or "none configured",
        )

    # ── Planning ──────────────────────────────────────────────────────────────

    def generate_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        """
        Try planners in cascade order.  Returns the first successful plan.
        Raises RuntimeError only when every planner in the chain has failed.

        *messages*, when provided, is forwarded verbatim to each provider as the
        conversation history; when None the providers behave single-turn.
        """
        last_exc: Exception | None = None

        for idx, provider in enumerate(self._planners):
            if not provider.available:
                logger.debug("Planner %s skipped – unavailable.", provider.name)
                continue
            try:
                result = provider.generate_plan(system_prompt, user_prompt, messages)
                self._last_planner = provider
                if idx > 0:
                    logger.info(
                        "Plan obtained via tier-%d planner: %s", idx, provider.label
                    )
                return result
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Planner %s failed: %s", provider.name, exc)
                telegram_notify(
                    f"⚠️ Planner <b>{provider.name}</b> failed (tier {idx}):\n"
                    f"<code>{exc}</code>"
                )
                last_exc = exc

        err = "All planning providers exhausted."
        logger.error(err)
        telegram_notify(f"❌ {err} Issue will be reopened.")
        raise RuntimeError(err) from last_exc

    # ── Coding ────────────────────────────────────────────────────────────────

    def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        """
        Try coders starting from _min_coder_tier.

        API failures advance _min_coder_tier immediately so the next call
        in the same attempt, or any subsequent attempt, won't retry a
        provider that is currently unreachable.

        *messages*, when provided, is forwarded verbatim to each provider as the
        conversation history; when None the providers behave single-turn.

        Raises RuntimeError only when every reachable coder has failed.
        """
        last_exc: Exception | None = None

        for idx in range(self._min_coder_tier, len(self._coders)):
            provider = self._coders[idx]
            if not provider.available:
                logger.debug("Coder %s skipped – unavailable.", provider.name)
                continue
            try:
                result = provider.generate_code(system_prompt, user_prompt, messages)
                self._last_coder = provider
                if idx > self._min_coder_tier:
                    logger.info(
                        "Code obtained via tier-%d coder: %s (API cascade).",
                        idx,
                        provider.label,
                    )
                return result
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Coder %s failed: %s", provider.name, exc)
                telegram_notify(
                    f"⚠️ Coder <b>{provider.name}</b> failed (tier {idx}):\n"
                    f"<code>{exc}</code>"
                )
                # Advance floor so next call skips this broken provider
                self._min_coder_tier = idx + 1
                last_exc = exc

        err = "All coding providers exhausted."
        logger.error(err)
        telegram_notify(f"❌ {err} Issue will be reopened.")
        raise RuntimeError(err) from last_exc

    def escalate_coder(self) -> None:
        """
        Advance the minimum coder tier to the next *available* provider.

        Called by node_on_layer_failure when a test layer fails – signals
        that the current provider's output quality is insufficient and the
        next tier should be used on the following attempt. Unavailable tiers
        (a consumer provider with no session, an unconfigured API key) are
        stepped over, so escalation always lands on something callable.

        This is distinct from API-failure escalation (which happens inside
        generate_code automatically); this handles quality-based escalation.
        """
        old_name = self.current_coder_name

        for idx in range(self._min_coder_tier + 1, len(self._coders)):
            if not self._coders[idx].available:
                continue
            self._min_coder_tier = idx
            new_name = self._coders[idx].name
            logger.info(
                "Coder tier escalated (test failure): %s → %s", old_name, new_name
            )
            telegram_notify(
                f"📈 Coder escalated due to test failure:\n"
                f"<b>{old_name}</b> → <b>{new_name}</b>"
            )
            return

        logger.warning(
            "escalate_coder() called but no higher tier is available (current: %s). "
            "No further escalation possible.",
            old_name,
        )

    @property
    def current_coder_name(self) -> str:
        """Human-readable name of the coder tier that will be tried next."""
        for idx in range(self._min_coder_tier, len(self._coders)):
            if self._coders[idx].available:
                return self._coders[idx].name
        return "none (all exhausted)"

    @property
    def last_coder_label(self) -> str:
        """`<name> (<billing>, model <model>)` of the coder that last answered."""
        return self._last_coder.label if self._last_coder else "unknown provider"

    @property
    def last_planner_label(self) -> str:
        """Same, for the planner that last answered."""
        return self._last_planner.label if self._last_planner else "unknown provider"

    def last_coder_attribution(self) -> dict[str, str]:
        """Structured attribution of the coder that produced the current code.

        Carried through IssueState rather than read again at commit time:
        `_min_coder_tier` moves during a run, so the chain head at commit is
        not necessarily the provider whose output is being merged.
        """
        provider = self._last_coder
        if provider is None:
            return {"provider": "unknown", "model": "unknown", "billing": "unknown"}
        return {
            "provider": provider.name,
            "model": provider.model or "unknown",
            "billing": provider.billing,
        }
