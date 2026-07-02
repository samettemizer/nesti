"""
telegram_notifier.py – critical alert dispatcher via Telegram Bot API.

Sends notifications when providers fail, coder tiers escalate, or
unexpected exceptions surface in the orchestrator.

Configuration (via .env):
    TELEGRAM_BOT_TOKEN  – token from @BotFather
    TELEGRAM_CHAT_ID    – target chat / group / channel ID

Design contract:
    • Never raises – Telegram failures must never crash the orchestrator.
    • Module-level singleton; safe to import from multiple modules.
    • Supports basic HTML tags: <b>, <i>, <code>, <pre>.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org"
_REQUEST_TIMEOUT = 10  # seconds


class TelegramNotifier:
    """Sends messages to a Telegram chat.  All methods are fire-and-forget."""

    def __init__(self) -> None:
        self.token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.enabled: bool = bool(self.token and self.chat_id)

        if not self.enabled:
            logger.info(
                "Telegram notifier disabled "
                "(TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set)."
            )

    def send(self, message: str) -> None:
        """
        Send *message* to the configured chat.

        Never raises – any error is logged as a warning and silently swallowed
        so that a Telegram outage cannot disrupt the orchestration loop.
        """
        if not self.enabled:
            return

        try:
            url = f"{_TELEGRAM_API_BASE}/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": f"🤖 <b>AI Developer</b>\n\n{message}",
                "parse_mode": "HTML",
            }
            resp = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
            if not resp.ok:
                logger.warning(
                    "Telegram API returned HTTP %s: %s",
                    resp.status_code,
                    resp.text[:300],
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Telegram notification failed (non-critical): %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton + public convenience function
# ---------------------------------------------------------------------------

_notifier: TelegramNotifier | None = None


def _get_notifier() -> TelegramNotifier:
    global _notifier  # pylint: disable=global-statement
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


def notify(message: str) -> None:
    """
    Send a Telegram notification.

    Safe to call even when Telegram is not configured – the call is a no-op
    in that case.  Import and use this function from any module.
    """
    _get_notifier().send(message)
