"""Offline tests for the stats recorder, the live stats page and the MCP usage summary."""

import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from unittest import mock

import requests

import stats
from stats import report, server, view


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

    def setUp(self) -> None:
        view._catalog_cache = None
        self.addCleanup(setattr, view, "_catalog_cache", None)

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

    def test_catalog_cached_within_ttl(self) -> None:
        with mock.patch("scripts.oauth.list_provider_models", return_value=self.CATALOG) as catalog, \
                mock.patch("stats.view.time.time", return_value=1000.0) as clock:
            view.prices({"claude-sonnet-4-6"})
            clock.return_value = 1000.0 + view.PRICE_TTL - 1
            view.prices({"deepseek/deepseek-chat"})
            self.assertEqual(catalog.call_count, 1)
            clock.return_value = 1000.0 + view.PRICE_TTL + 1
            view.prices({"claude-sonnet-4-6"})
            self.assertEqual(catalog.call_count, 2)

    def test_unreachable_catalog_not_cached(self) -> None:
        with mock.patch("scripts.oauth.list_provider_models", side_effect=[requests.ConnectionError("x"), self.CATALOG]):
            self.assertEqual(view.prices({"claude-sonnet-4-6"}), {})
            self.assertIn("claude-sonnet-4-6", view.prices({"claude-sonnet-4-6"}))


def _page_data(page: str) -> dict:
    """The JSON embedded as ``const D = …;`` in a rendered page."""
    start = page.index("const D = ") + len("const D = ")
    return json.loads(page[start:page.index(";\n", start)])


class LivePageTest(unittest.TestCase):
    """The page is rendered from the events recorded at request time."""

    def setUp(self) -> None:
        patcher = mock.patch("stats.view.prices", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.StatsHandler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def get(self, path: str) -> tuple[int, str]:
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, ""

    def test_each_request_reflects_current_events(self) -> None:
        first = [{"t": 1.0, "kind": "llm", "model": "m", "tok": [1, 0, 0, 1], "ok": True}]
        with mock.patch("stats.load", side_effect=[first, first * 3]):
            status_a, page_a = self.get("/")
            status_b, page_b = self.get("/")
        self.assertEqual((status_a, status_b), (200, 200))
        a, b = _page_data(page_a), _page_data(page_b)
        self.assertEqual((len(a["events"]), len(b["events"])), (1, 3))
        self.assertLess(a["generated"], b["generated"])

    def test_other_paths_are_404(self) -> None:
        with mock.patch("stats.load", return_value=[]) as load:
            self.assertEqual(self.get("/stats.html")[0], 404)
        load.assert_not_called()

    def test_render_failure_is_500(self) -> None:
        with mock.patch("stats.load", side_effect=RuntimeError("boom")):
            self.assertEqual(self.get("/")[0], 500)

    def test_render_retries_redis_after_an_outage(self) -> None:
        self.addCleanup(setattr, stats, "_redis", stats._redis)
        stats._redis = False  # an earlier ping failed: the recorder degraded for the process
        client = mock.Mock()
        client.lrange.return_value = [json.dumps({"t": 1.0, "kind": "tool", "tool": "x"})]
        with mock.patch("stats.redis.from_url", return_value=client):
            page = view.render()
        client.ping.assert_called_once()
        self.assertEqual(len(_page_data(page)["events"]), 1)

    def test_script_breakout_is_escaped(self) -> None:
        hostile = [{"t": 1.0, "kind": "tool", "tool": "x", "title": "</script><img src=x onerror=alert(1)>"}]
        with mock.patch("stats.load", return_value=hostile):
            page = view.render()
        self.assertNotIn("</script><img", page)
        self.assertIn("\\u003c/script>\\u003cimg", page)
        self.assertEqual(_page_data(page)["events"][0]["title"], hostile[0]["title"])


class CliStatsTest(unittest.TestCase):
    def test_prints_live_url(self) -> None:
        with mock.patch("stats.load", return_value=[]), mock.patch("stats.view._server_up", return_value=True), \
                mock.patch("stats.view.os.path.exists", return_value=True), \
                mock.patch("builtins.print") as out:
            self.assertEqual(view.cli_stats([]), 0)
        self.assertIn(mock.call(f"Stats page: {view.URL}"), out.call_args_list)

    def test_server_down_is_an_error(self) -> None:
        with mock.patch("stats.load", return_value=[]), mock.patch("stats.view._server_up", return_value=False), \
                mock.patch("builtins.print"):
            self.assertEqual(view.cli_stats([]), 1)


class SummaryTest(unittest.TestCase):
    PRICES = {"claude-sonnet-4-6": [1e-6, 1e-7, 2e-6, 1e-5]}

    def setUp(self) -> None:
        now = time.time()
        run = {"run": "7@1", "issue": 7, "title": "T", "project": "www/a"}
        self.events = [
            {"t": now - 3 * 86400, "kind": "llm", "model": "claude-sonnet-4-6", "provider": "Claude", "billing": "consumer subscription",
             "ok": True, "error": None, "dur": 5.0, "tok": [100, 0, 0, 10], "project": "www/old"},
            {"t": now - 600, "kind": "llm", "model": "claude-sonnet-4-6", "provider": "Claude", "billing": "consumer subscription",
             "ok": True, "error": None, "dur": 2.0, "tok": [10, 80, 10, 20], **run},
            {"t": now - 500, "kind": "llm", "model": "qwen3:30b", "provider": "Ollama", "billing": "local model",
             "ok": False, "error": "HTTP 500 id deadbeef01", "dur": 1.0, "tok": [0, 0, 0, 0], **run},
            {"t": now - 400, "kind": "llm", "model": "qwen3:30b", "provider": "Ollama", "billing": "local model",
             "ok": False, "error": "HTTP 502 id cafebabe02", "dur": 1.0, "tok": [0, 0, 0, 0], "project": "www/b"},
            {"t": now - 300, "kind": "tool", "tool": "docker_run_tests", "model": "claude-sonnet-4-6", "provider": "Claude",
             "ok": False, "error": "test layer failed", "dur": 30.0, **run},
        ]

    def run_summary(self, prices: dict | None = None, **kwargs) -> dict:
        with mock.patch("stats.load", return_value=self.events), \
                mock.patch("stats.view.prices", return_value=self.PRICES if prices is None else prices):
            out = report.summary(**kwargs)
        self.assertTrue(out["success"], out)
        return out["result"]

    def test_window_totals_and_sort(self) -> None:
        r = self.run_summary(since_hours=24)
        t = r["totals"]
        self.assertEqual((t["requests"], t["failed"], t["issue_runs"], t["tool_runs"], t["unpriced_requests"]), (3, 2, 1, 1, 2))
        self.assertEqual(t["tokens"], {"uncached": 10, "cache_read": 80, "cache_write": 10, "output": 20})
        self.assertAlmostEqual(t["cache_rate"], 0.8)
        self.assertAlmostEqual(t["avg_duration"], 2.0)
        self.assertAlmostEqual(t["cost_usd"], 10e-6 + 80e-7 + 10 * 2e-6 + 20e-5)
        self.assertEqual([m["model"] for m in r["models"]], ["qwen3:30b", "claude-sonnet-4-6"])
        self.assertIsNone(r["models"][0]["cost_usd"])
        self.assertEqual(r["providers"][0]["billing"], "local model")
        self.assertEqual([p["project"] for p in r["projects"]], ["www/a", "www/b"])
        self.assertEqual(r["tools"], [{"tool": "docker_run_tests", "model": "claude-sonnet-4-6", "calls": 1, "errors": 1}])
        self.assertEqual([(e["signature"], e["count"]) for e in r["errors"]], [("HTTP # id #", 2)])
        self.assertEqual(r["runs"][0]["run"], "7@1")
        self.assertEqual((r["runs"][0]["llm_requests"], r["runs"][0]["tool_runs"], r["runs"][0]["tokens"]), (2, 1, 120))

    def test_all_time_and_project_filter(self) -> None:
        self.assertEqual(self.run_summary(since_hours=0)["totals"]["requests"], 4)
        r = self.run_summary(since_hours=0, project="www/old")
        self.assertEqual((r["totals"]["requests"], r["totals"]["tool_runs"], r["window"]["since"]), (1, 0, None))

    def test_unreachable_catalog_cost_is_unknown(self) -> None:
        t = self.run_summary(prices={}, since_hours=24)["totals"]
        self.assertIsNone(t["cost_usd"])
        self.assertEqual(t["unpriced_requests"], 3)

    def test_without_redis_zero_totals(self) -> None:
        self.events = []
        r = self.run_summary()
        self.assertEqual((r["totals"]["requests"], r["totals"]["cost_usd"], r["models"], r["runs"]), (0, 0.0, [], []))

    def test_exception_is_reported(self) -> None:
        with mock.patch("stats.load", side_effect=RuntimeError("boom")):
            self.assertEqual(report.summary(), {"success": False, "error": "boom"})


if __name__ == "__main__":
    unittest.main()
