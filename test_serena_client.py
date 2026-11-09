"""Offline tests for serena_client.research, the planner's read-only Serena loop."""

import json
import os
import unittest
from unittest.mock import patch

import serena_client

_LAYOUT = {
    "layout": {"backend": "backend", "frontend": "frontend"},
    "mode": "separated",
    "architecture": {
        "backend": {"php": "^8.4", "laravel": "^13.0"},
        "frontend": {"packages": {"vue": "^3.5"}, "typescript": True},
        "summary": ["Domains live under backend/app/Domains."],
    },
}
_FIND = {"tool": "find_symbol", "args": {"name_path_pattern": "Apartment"}}


class ScriptedLLM:
    """Scripted ``generate_plan`` replies; repeats the last one and keeps each call's messages."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.calls = 0
        self.messages: list[list[dict]] = []

    def generate_plan(self, system: str, user: str, messages=None) -> str:
        self.calls += 1
        self.messages.append(list(messages))  # research extends history in place
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.batches: list[list[tuple[str, dict]]] = []
        self.result = None

        def fake_call_tools(batch):
            self.batches.append(batch)
            if self.result is not None:
                return [self.result for _ in batch]
            return [f"result of {name}" for name, _ in batch]

        for patcher in (
            patch.dict(os.environ, {"NESTI_SERENA_ENABLE": "TRUE"}),
            patch("project_layout.load_layout", return_value=_LAYOUT),
            patch("serena_client.call_tools", side_effect=fake_call_tools),
        ):
            self.mock = patcher.start()
            self.addCleanup(patcher.stop)

    def test_only_read_tools_reach_serena(self):
        llm = ScriptedLLM(
            json.dumps({"actions": [_FIND, {"tool": "replace_symbol_body",
                                            "args": {"name_path": "x", "relative_path": "y", "body": ""}},
                                    {"tool": [], "args": {}}]}),
            json.dumps({"done": True}),
        )
        findings = serena_client.research(llm, "Add a block filter")
        (write,) = self.batches[0]
        self.assertEqual(write[0], "write_memory")
        self.assertEqual(write[1]["memory_name"], "nesti/architecture")
        self.assertIn("# Project Architecture", write[1]["content"])
        self.assertIn("`backend/`", write[1]["content"])
        self.assertEqual(self.batches[1], [("find_symbol", {"name_path_pattern": "Apartment"})])
        self.assertIn("result of find_symbol", findings)
        self.assertNotIn("replace_symbol_body", findings)
        self.assertIn("refused", llm.messages[1][-1]["content"])
        self.assertEqual(llm.calls, 2)

    def test_turn_cap(self):
        llm = ScriptedLLM(json.dumps({"actions": [_FIND]}))
        serena_client.research(llm, "x")
        self.assertEqual(llm.calls, 4)
        self.assertEqual(len(self.batches), 5)

    def test_unreachable_serena_skips_planner(self):
        self.mock.side_effect = ConnectionError("no route to nesti-serena")
        llm = ScriptedLLM(json.dumps({"actions": [_FIND]}))
        self.assertEqual(serena_client.research(llm, "x"), "")
        self.assertEqual(llm.calls, 0)

    def test_disabled_flag(self):
        os.environ["NESTI_SERENA_ENABLE"] = "false"
        llm = ScriptedLLM(json.dumps({"actions": [_FIND]}))
        self.assertEqual(serena_client.research(llm, "x"), "")
        self.assertEqual(self.batches, [])
        self.assertEqual(llm.calls, 0)

    def test_findings_capped(self):
        self.result = "x" * 50_000
        llm = ScriptedLLM(json.dumps({"actions": [_FIND] * 8}))
        findings = serena_client.research(llm, "x")
        self.assertLessEqual(
            len(findings), serena_client._MAX_FINDINGS_CHARS + len("\n… findings truncated"),
        )


if __name__ == "__main__":
    unittest.main()
