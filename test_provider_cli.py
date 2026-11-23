"""Offline provider metadata/menu transport and API-key quota regressions.

Run: .venv/bin/python -m unittest -v test_provider_cli
No graph imports, real credentials, network requests or inference calls.
"""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

from scripts import oauth


class ProviderCLITest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret", "OPENROUTER_API_ENABLED": "false"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.store = Mock(available=True)
        self.store.get_all_tokens.return_value = {}
        self.store.get_token.return_value = None
        self.store_patch = patch.object(oauth, "TokenStore", return_value=self.store)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.http_patch = patch.object(oauth.requests, "get")
        self.http = self.http_patch.start()
        self.addCleanup(self.http_patch.stop)
        self.http.return_value.json.return_value = {"data": {}}
        self.model = {
            "id": "nvidia/free", "name": "Nemotron", "context_length": 1000000,
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "pricing": {"prompt": "0", "completion": "0"},
        }

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(oauth.sys, "argv", ["nesti", *args]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                oauth.main()
                code = 0
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_provider_labels_and_json(self):
        code, out, _ = self.cli("/provider")
        self.assertEqual(code, 0)
        self.assertIn("  - openrouter (Authenticated)\n", out)
        self.assertIn("copilot (coming soon)", out)
        self.assertNotIn("platform API", out)
        self.assertNotIn("model:", out)
        self.assertNotIn("disabled", out)
        rows = json.loads(self.cli("/provider", "--json")[1])
        self.assertEqual(rows[-1], {"name": "openrouter", "kind": "platform", "authenticated": True, "coming_soon": False})
        self.assertTrue(all(row["kind"] == "consumer" for row in rows[:-1]))
        self.assertNotIn("test-secret", json.dumps(rows))
        self.store.get_model.assert_not_called()
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": " "}):
            self.assertIn("  - openrouter\n", self.cli("/provider")[1])
        self.http.assert_not_called()

    def test_catalog_alias_filter_and_raw_contract(self):
        self.http.return_value.json.return_value = {"data": [self.model, None, {}, {**self.model, "architecture": None}]}
        with patch.object(oauth, "TokenStore", side_effect=AssertionError("catalog uses no Redis")):
            for args in (("models", "openrouter", "NVIDIA"), ("openrouter", "models", "nemotron")):
                code, out, _ = self.cli("/provider", *args, "--json")
                self.assertEqual(code, 0)
                rows = json.loads(out)
                self.assertEqual(rows[0]["id"], "nvidia/free")
                self.assertTrue(rows[0]["free"])
                self.assertEqual(rows[0]["context"], 1000000)
            self.assertEqual(oauth.list_provider_models("openrouter"), [self.model])
            self.assertEqual(json.loads(self.cli("/provider", "models", "openrouter", "absent", "--json")[1]), [])
        self.store.save_model.assert_not_called()
        self.store.save_token.assert_not_called()
        self.assertEqual(os.environ["OPENROUTER_API_ENABLED"], "false")

    def test_free_requires_all_known_costs_zero(self):
        for pricing, free in (({}, False), (None, False), ([], False),
                              ({"prompt": "0", "completion": "0"}, True),
                              ({"prompt": "0", "completion": "0", "request": "0"}, True),
                              ({"prompt": "0", "completion": "0", "request": "0.01"}, False),
                              ({"prompt": "0", "completion": "0", "request": None}, False)):
            with self.subTest(pricing=pricing):
                self.assertEqual(oauth._model_metadata({**self.model, "pricing": pricing})["free"], free)
        for bad in (None, "", True, "NaN", "Infinity", "-1", "0.0000000000001", "1"):
            for key in ("prompt", "completion", "request"):
                pricing = {"prompt": "0", "completion": "0", key: bad}
                self.assertFalse(oauth._model_metadata({**self.model, "pricing": pricing})["free"], pricing)
        for value, expected in ((None, "unknown"), ("-1", "variable"), ("NaN", "variable"),
                                ("0.00001", "10"), ("0.0000001575", "0.1575"),
                                ("0.0000000000001", "0.0000001"), ("0", "0")):
            self.assertEqual(oauth._model_price(value), expected)
        self.assertIsNone(oauth._model_metadata({**self.model, "context_length": True})["context"])

    def test_table_color_and_unknown(self):
        self.http.return_value.json.return_value = {"data": [self.model]}
        for color in (False, True):
            with patch.object(oauth.sys, "stdout") as output, patch.dict(os.environ, {}, clear=True):
                output.isatty.return_value = color
                oauth._cmd_provider_models("openrouter")
                text = " ".join(str(call.args) for call in output.write.call_args_list)
                self.assertIn("[FREE]", text)
                self.assertIn("1,000,000", text)
                self.assertEqual("\\x1b" in text, color)
                output.reset_mock()
                os.environ["NO_COLOR"] = ""
                oauth._cmd_provider_models("openrouter")
                self.assertNotIn("\\x1b", " ".join(str(call.args) for call in output.write.call_args_list))

    def test_quota_zero_null_optional_and_allowlist(self):
        self.http.return_value.json.return_value = {"data": {
            "usage": 0, "usage_daily": 0, "usage_weekly": 1.25, "usage_monthly": 2,
            "limit": None, "limit_remaining": None, "limit_reset": "monthly",
            "label": "private-label", "token": "private-token", "is_free_tier": True,
            "rate_limit": {"requests": 999},
            "free_model_daily_requests": {"used": 0, "limit": 50, "remaining": 50},
            "effective_budget": {"scope": "key", "limit_usd": 5, "remaining_usd": 0,
                                 "spend_usd": 5, "reset_interval": "daily", "resets_at": "2026-11-24T00:00:00Z"},
        }}
        code, out, _ = self.cli("/usage")
        self.assertEqual(code, 0)
        for text in ("All-time: 0", "Remaining: unknown", "Key cap: no key cap", "Reset: monthly",
                     "0 used / 50 limit; 50 remaining", "Effective budget: key", "Remaining: 0", "Cap: 5"):
            self.assertIn(text, out)
        for secret in ("private-label", "private-token", "999", "unlimited", "No authenticated"):
            self.assertNotIn(secret, out)
        self.http.assert_called_once_with(oauth.OPENROUTER_API_BASE + "/key",
                                          headers={"Authorization": "Bearer test-secret"}, timeout=20)
        self.store.save_token.assert_not_called()
        self.store.save_model.assert_not_called()

    def test_missing_invalid_and_zero_quota(self):
        self.assertIn("Key cap: unknown", self.cli("/usage")[1])
        self.assertNotIn("Free model daily", self.cli("/usage")[1])
        self.http.return_value.json.return_value = {"data": {"limit": 0, "limit_remaining": 0}}
        self.assertIn("Remaining: 0  Key cap: 0", self.cli("/usage")[1])
        for value in (True, -1, "NaN", "Infinity", [], {}, None):
            self.assertEqual(oauth._quota_number(value), "unknown")
        self.http.return_value.json.return_value = {"data": {
            "free_model_daily_requests": {"used": True, "limit": -1, "remaining": 1.5}}}
        self.assertIn("unknown used / unknown limit; unknown remaining", self.cli("/usage")[1])

    def test_errors_are_sanitized_without_retry(self):
        for error in (oauth.requests.ConnectionError("test-secret raw payload"), oauth.requests.Timeout("test-secret")):
            self.http.reset_mock()
            self.http.side_effect = error
            out = self.cli("/usage")[1]
            self.assertIn(type(error).__name__, out)
            self.assertIn("check container connectivity", out)
            self.assertNotIn("test-secret", out)
            self.http.assert_called_once()
        self.http.side_effect = None
        response = oauth.requests.Response()
        response.status_code = 401
        self.http.return_value.raise_for_status.side_effect = oauth.requests.HTTPError("test-secret", response=response)
        self.assertIn("HTTP 401", self.cli("/usage")[1])
        self.http.return_value.raise_for_status.side_effect = None
        self.http.return_value.json.return_value = {"data": []}
        self.assertIn("ValueError", self.cli("/usage")[1])

    def test_redis_outage_with_and_without_key(self):
        self.store.available = False
        code, out, _ = self.cli("/usage")
        self.assertEqual(code, 0)
        self.assertIn("Consumer usage unavailable", out)
        self.assertIn("[openrouter]", out)
        self.store.get_all_tokens.assert_not_called()
        self.http.reset_mock()
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            code, out, _ = self.cli("/usage")
        self.assertEqual(code, 1)
        self.assertIn("cannot reach Redis", out)
        self.http.assert_not_called()

    def test_consumer_usage_still_dispatches_through_fetch_usage(self):
        self.store.get_all_tokens.return_value = {"claude": {"access_token": "consumer-secret"}}
        with patch.object(oauth, "fetch_usage", return_value={"remaining": 10, "limit": 100}) as fetch:
            out = self.cli("/usage")[1]
        fetch.assert_called_once_with(self.store, "claude", {"access_token": "consumer-secret"})
        self.assertIn("[claude]: 10 / 100 remaining", out)
        self.assertIn("[openrouter]", out)
        self.http.side_effect = oauth.requests.Timeout("private")
        with patch.object(oauth, "fetch_usage", return_value={"remaining": None, "limit": None}):
            self.assertIn("[claude]: usage unknown", self.cli("/usage")[1])
        self.store.get_all_tokens.return_value = {}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            self.assertIn("No authenticated providers", self.cli("/usage")[1])


if __name__ == "__main__":
    unittest.main()
