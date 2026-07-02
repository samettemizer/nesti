"""
llm_client.py – provider cascade for planning and code generation.

Provider roles
──────────────
  Planning  │ Hermes-3    (local via Ollama)
            │   → DeepSeek  (mid-tier paid API)
            │   → Claude Sonnet  (last-resort paid API)

  Coding    │ Qwen3:30b   (local – via Ollama)
            │   → DeepSeek  (mid-tier paid API)
            │   → Claude Sonnet  (last-resort paid API)

Cascade rules
─────────────
  • API / timeout failures  → immediate cascade to the next provider within
                              the same attempt; no retry slot consumed.
  • Test failures           → task_engine calls escalate_coder(), which raises
                              the minimum coder tier for the NEXT attempt.
  • Every provider failure and tier escalation emits a Telegram notification.
  • A provider is silently skipped at init-time when its env vars are absent,
    so the system degrades gracefully (e.g. Hermes-3 not yet installed).
"""

import logging
import os
from abc import ABC, abstractmethod

import anthropic
import requests

from telegram_notifier import notify as telegram_notify

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 8096


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    """Interface every provider must implement."""

    name: str = "unknown"

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
        return os.environ.get("LOCAL_LLM_ENABLED").strip().lower() == "true"
        # return bool(self.base_url and self.model)

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
    """Hermes-3 – primary planner."""
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
        return os.environ.get("HERMES3_LLM_ENABLED").strip().lower() == "true"
        # return bool(self.base_url and self.model)


class QwenLLMClient(_OllamaBase):
    """Qwen3:30b – primary code generator."""

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
# Anthropic Claude  (last resort)
# ─────────────────────────────────────────────────────────────────────────────

class AnthropicLLMClient(BaseLLMClient):
    """Claude Sonnet – premium last-resort fallback."""

    name = "Claude Sonnet"

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        messages: list[dict] | None = None,
    ) -> str:
        msg_list = messages if messages else [{"role": "user", "content": user_prompt}]
        # Anthropic keeps the system prompt separate and rejects system-role
        # entries inside the messages array, so strip any that were carried in
        # the shared history.
        msg_list = [m for m in msg_list if m.get("role") != "system"]
        message = self.client.messages.create(
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
# Unified client with cascading fallback
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Unified LLM client with 3-tier cascading fallback.

    Planning cascade (fully automatic within every call):
        Hermes-3  →  DeepSeek  →  Claude Sonnet

    Coding cascade (hybrid):
        • API / timeout errors  → immediate cascade within the same attempt.
        • Test failures         → task_engine calls escalate_coder() to raise
                                  _min_coder_tier before the next attempt.

    The two cascade mechanisms are independent:
        – _min_coder_tier is the floor; generate_code() starts there each call.
        – If the floor provider has an API error, it cascades upward within
          that same call and also advances _min_coder_tier so the next call
          won't retry a known-broken provider.

    Telegram notifications are sent on every failure and tier escalation.
    """

    def __init__(self) -> None:
        # Instantiate providers once; DeepSeek and Claude are shared across
        # both chains to avoid creating duplicate API client objects.
        hermes = HermesLLMClient()
        qwen = QwenLLMClient()
        deepseek = DeepSeekLLMClient()
        claude = AnthropicLLMClient()

        # ── Planner chain: Hermes-3 → DeepSeek → Claude ──────────────
        self._planners: list[BaseLLMClient] = []
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

        # ── Coder chain: Qwen → DeepSeek → Claude ────────────────────
        self._coders: list[BaseLLMClient] = []
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

        logger.info(
            "LLM chains ready – Planners: [%s] | Coders: [%s]",
            ", ".join(p.name for p in self._planners),
            ", ".join(c.name for c in self._coders),
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
            try:
                result = provider.generate_plan(system_prompt, user_prompt, messages)
                if idx > 0:
                    logger.info(
                        "Plan obtained via tier-%d planner: %s", idx, provider.name
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
            try:
                result = provider.generate_code(system_prompt, user_prompt, messages)
                if idx > self._min_coder_tier:
                    logger.info(
                        "Code obtained via tier-%d coder: %s (API cascade).",
                        idx,
                        provider.name,
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
        Advance the minimum coder tier by one step.

        Called by task_engine when PHPUnit tests fail – signals that the
        current provider's output quality is insufficient and the next tier
        should be used on the following attempt.

        This is distinct from API-failure escalation (which happens inside
        generate_code automatically); this handles quality-based escalation.
        """
        if self._min_coder_tier >= len(self._coders) - 1:
            logger.warning(
                "escalate_coder() called but already at the last tier (%s). "
                "No further escalation possible.",
                self._coders[-1].name,
            )
            return

        old_name = self._coders[self._min_coder_tier].name
        self._min_coder_tier += 1
        new_name = self._coders[self._min_coder_tier].name

        logger.info(
            "Coder tier escalated (test failure): %s → %s", old_name, new_name
        )
        telegram_notify(
            f"📈 Coder escalated due to test failure:\n"
            f"<b>{old_name}</b> → <b>{new_name}</b>"
        )

    @property
    def current_coder_name(self) -> str:
        """Human-readable name of the coder tier that will be tried next."""
        if self._min_coder_tier < len(self._coders):
            return self._coders[self._min_coder_tier].name
        return "none (all exhausted)"
