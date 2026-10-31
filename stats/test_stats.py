"""Offline tests for the stats recorder and the /stats price lookup."""

import unittest
from types import SimpleNamespace
from unittest import mock

import requests

import stats
from stats import view


class StatsTestCase(unittest.TestCase):
    """Captures emitted events instead of writing to Redis."""

    def setUp(self) -> None:
        stats.end()
        self.events: list[dict] = []
        patcher = mock.patch.object(stats, "_emit", self.events.append)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        stats.end()


class TokensTest(unittest.TestCase):
    def test_shapes(self) -> None:
        cases = [
            ({"input_tokens": 10, "cache_read_input_tokens": 80, "cache_creation_input_tokens": 5, "output_tokens": 3}, [10, 80, 5, 3]),
            ({"prompt_tokens": 100, "completion_tokens": 7, "prompt_tokens_details": {"cached_tokens": 60}}, [40, 60, 0, 7]),
            ({"prompt_tokens": 100, "completion_tokens": 7, "prompt_cache_hit_tokens": 30}, [70, 30, 0, 7]),
            ({"input_tokens": 50, "output_tokens": 4, "input_tokens_details": {"cached_tokens": 20}}, [30, 20, 0, 4]),
            ({"promptTokenCount": 90, "cachedContentTokenCount": 40, "candidatesTokenCount": 6, "thoughtsTokenCount": 2}, [50, 40, 0, 8]),
        ]
        for usage, expected in cases:
            with self.subTest(usage=usage):
                self.assertEqual(stats._tokens(usage), expected)


class LlmRequestTest(StatsTestCase):
    def test_usage_summed_within_attempt(self) -> None:
        with stats.llm_request("plan", SimpleNamespace(name="P", model="m", billing="b")):
            stats.usage({"input_tokens": 1, "output_tokens": 2})
            stats.usage({"input_tokens": 3, "output_tokens": 4})
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["tok"], [4, 0, 0, 6])
        self.assertTrue(self.events[0]["ok"])

    def test_exception_propagates_and_is_recorded(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with stats.llm_request("code", SimpleNamespace(name="P")):
                raise RuntimeError("boom")
        self.assertFalse(self.events[0]["ok"])
        self.assertEqual(self.events[0]["error"], "boom")

    def test_provider_without_model_falls_back_to_name(self) -> None:
        with stats.llm_request("plan", SimpleNamespace(name="P")):
            pass
        self.assertEqual(self.events[0]["model"], "P")
        self.assertEqual(self.events[0]["billing"], "")

    def test_usage_outside_attempt_records_nothing(self) -> None:
        stats.usage({"input_tokens": 5})
        self.assertEqual(self.events, [])


class InstrumentTest(StatsTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.result = {"success": True, "result": {"passed": False}}

        def tool_docker_run_tests() -> dict:
            return self.result

        def helper() -> None:
            return None

        self.helper = helper
        self.ns = {"tool_docker_run_tests": tool_docker_run_tests, "helper": helper}
        stats.instrument(self.ns)

    def test_helper_unwrapped(self) -> None:
        self.assertIs(self.ns["helper"], self.helper)

    def test_no_run_passes_through(self) -> None:
        self.assertIs(self.ns["tool_docker_run_tests"](), self.result)
        self.assertEqual(self.events, [])

    def test_failed_layer_recorded_with_last_model(self) -> None:
        stats.begin(7, "Title")
        with stats.llm_request("code", SimpleNamespace(name="P", model="m", billing="b")):
            pass
        self.assertIs(self.ns["tool_docker_run_tests"](), self.result)
        event = self.events[-1]
        self.assertEqual(
            {k: event[k] for k in ("kind", "tool", "ok", "error", "model", "issue", "title")},
            {"kind": "tool", "tool": "docker_run_tests", "ok": False, "error": "test layer failed",
             "model": "m", "issue": 7, "title": "Title"},
        )


class PricesTest(unittest.TestCase):
    CATALOG = [
        {"id": "anthropic/claude-sonnet-4.6", "pricing": {"prompt": "0.000003", "completion": "0.000015",
                                                         "input_cache_read": "0.0000003", "input_cache_write": "0.00000375"}},
        {"id": "anthropic/claude-sonnet-4.6:free", "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "deepseek/deepseek-chat", "pricing": {"prompt": "0.00000027", "completion": "0.0000011"}},
        {"id": "openrouter/auto", "pricing": {"prompt": "-1", "completion": "-1"}},
    ]

    def test_catalog_matching(self) -> None:
        with mock.patch("scripts.oauth.list_provider_models", return_value=self.CATALOG):
            table = view.prices({"claude-sonnet-4-6", "deepseek/deepseek-chat", "openrouter/auto", "qwen3:30b"})
        expected = {"claude-sonnet-4-6": [3e-6, 3e-7, 3.75e-6, 1.5e-5],
                    "deepseek/deepseek-chat": [2.7e-7, 2.7e-7, 2.7e-7, 1.1e-6]}
        self.assertEqual(table.keys(), expected.keys())
        for model, row in expected.items():
            for got, want in zip(table[model], row, strict=True):
                self.assertAlmostEqual(got, want, places=12)

    def test_unreachable_catalog(self) -> None:
        with mock.patch("scripts.oauth.list_provider_models", side_effect=requests.ConnectionError("x")):
            self.assertEqual(view.prices({"claude-sonnet-4-6"}), {})


if __name__ == "__main__":
    unittest.main()
