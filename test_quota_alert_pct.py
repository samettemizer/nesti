import sys
import logging
from unittest.mock import patch

import os
os.environ["REDIS_URL"] = "redis://nesti-redis:6379/0"

from graph.nodes import node_on_layer_failure
from scripts.oauth import PROVIDERS, TokenStore

logging.basicConfig(level=logging.INFO)

store = TokenStore()
store.save_token("claude", {"access_token": "test-token"})
original_get_usage = PROVIDERS["claude"].get_usage
PROVIDERS["claude"].get_usage = lambda token_data: {"remaining": 4, "limit": 50, "reset_time": 0}

state = {
    "issue_id": 999,
    "attempt": 1,
    "max_attempts": 3,
    "test_passed": False,
    "test_output": "Failing test output mock",
    "openapi_passed": True,
    "vitest_passed": True,
    "playwright_passed": True,
}

try:
    with patch("graph.nodes.telegram_notify") as mock_notify:
        with patch("graph.nodes._store.append_test_failure"):
            with patch("graph.nodes._llm.escalate_coder"):
                node_on_layer_failure(state)
                mock_notify.assert_called_with("⚠️ Low Quota Warning: Provider 'claude' has only 4 requests left.")
                print("SUCCESS: Telegram alert fired for < 10% quota.")
finally:
    PROVIDERS["claude"].get_usage = original_get_usage
    store.delete_token("claude")
