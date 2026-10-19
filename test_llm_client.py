"""Offline provider-boundary and compiled-context regression tests."""

import copy
import io
import json
import os
import unittest
from unittest.mock import patch

import httpx
import requests

import llm_client as llm


_OUTPUT = (
    "### FILE: resources/js/NewTaskTable.vue\n```vue\n"
    "<template>  café 😀\n</template>\n```\n\n"
    "### DELETE: resources/js/Obsolete.vue\n"
)
_SYSTEM = "System policy café"
_MESSAGES = [{"role": "user", "content": "Current snapshot 😀\nLatest failure only"}]


def _response(request, data, status=200, stream=False):
    response = requests.Response()
    response.status_code = status
    response.request = request
    body = data if stream else json.dumps(data).encode("utf-8")
    response.raw = io.BytesIO(body)
    if not stream:
        response._content = body
    return response


class ProviderBoundaryTests(unittest.TestCase):
    def test_requests_provider_bodies_content_and_usage(self):
        """Measure Requests' actual bytes, including escaping and provider envelopes."""
        env = {
            "LOCAL_LLM_ENABLED": "true", "LOCAL_LLM_URL": "https://local.invalid/v1",
            "LOCAL_LLM_MODEL": "test-model", "DEEPSEEK_API_ENABLED": "true",
            "DEEPSEEK_API_KEY": "secret-key", "OPENROUTER_API_ENABLED": "true",
            "OPENROUTER_API_KEY": "secret-key",
        }
        with patch.dict(os.environ, env):
            clients = [llm.QwenLLMClient(), llm.OpenRouterLLMClient(),
                       llm.DeepSeekLLMClient(), llm.ClaudeConsumerClient(),
                       llm.ChatGPTConsumerClient(), llm.AntigravityConsumerClient(),
                       llm.CopilotConsumerClient()]
        credentials = {
            "access_token": "secret-token", "session_token": "secret-session",
            "account_id": "secret-account", "project_id": "secret-project",
            "chat_api_base": "https://copilot.invalid",
        }
        for client in clients:
            with self.subTest(provider=client.name):
                captured = []
                expected_system = _SYSTEM
                data = {"choices": [{"message": {"content": _OUTPUT}}],
                        "usage": {"prompt_tokens": 17, "completion_tokens": 29}}
                stream = False
                expected_usage = "'prompt_tokens': 17"
                if isinstance(client, llm.ClaudeConsumerClient):
                    expected_system = client._SYSTEM_PREFIX + "\n\n" + _SYSTEM
                    data = {"content": [{"text": _OUTPUT}],
                            "usage": {"input_tokens": 17, "output_tokens": 29}}
                    expected_usage = "'input_tokens': 17"
                elif isinstance(client, llm.ChatGPTConsumerClient):
                    events = [
                        {"type": "response.output_text.delta", "delta": _OUTPUT[:35]},
                        {"type": "response.output_text.delta", "delta": _OUTPUT[35:]},
                        {"type": "response.completed", "response": {
                            "usage": {"input_tokens": 17, "output_tokens": 29}}},
                    ]
                    data = b"".join(b"data: " + json.dumps(event, ensure_ascii=False).encode()
                                    + b"\n\n" for event in events)
                    stream = True
                    expected_usage = "'input_tokens': 17"
                elif isinstance(client, llm.AntigravityConsumerClient):
                    data = {"response": {"candidates": [{"content": {"parts": [
                        {"text": "private reasoning", "thought": True}, {"text": _OUTPUT},
                    ]}}], "usageMetadata": {"promptTokenCount": 17, "candidatesTokenCount": 29}}}
                    expected_usage = "'promptTokenCount': 17"

                def send(adapter, request, **kwargs):
                    captured.append(request)
                    return _response(request, data, stream=stream)

                original = copy.deepcopy(_MESSAGES)
                with patch.dict(os.environ, env), \
                        patch.object(llm._ConsumerLLMBase, "_credentials", return_value=credentials), \
                        patch.object(llm, "_token_store"), \
                        patch.object(llm, "configured_model", return_value="test-model"), \
                        patch("requests.adapters.HTTPAdapter.send", autospec=True, side_effect=send), \
                        self.assertLogs("llm_client", level="INFO") as logs:
                    result = client.generate_code(_SYSTEM, "UNUSED fallback prompt", _MESSAGES)
                self.assertEqual(result.encode(), _OUTPUT.encode())
                self.assertEqual(_MESSAGES, original)
                self.assertEqual(len(captured), 1)
                body = captured[0].body
                self.assertIsInstance(body, bytes)
                sent = json.loads(body)
                self.assertNotIn("UNUSED fallback prompt", body.decode())
                if isinstance(client, llm.ChatGPTConsumerClient):
                    self.assertEqual(sent["input"][0]["content"][0]["text"], _MESSAGES[0]["content"])
                elif isinstance(client, llm.AntigravityConsumerClient):
                    self.assertEqual(sent["request"]["contents"][0]["parts"][0]["text"], _MESSAGES[0]["content"])
                else:
                    self.assertEqual([msg for msg in sent["messages"] if msg["role"] != "system"], _MESSAGES)
                text = "\n".join(logs.output)
                self.assertIn(f"system_chars={len(expected_system)} content_chars={len(_MESSAGES[0]['content'])} "
                              f"http_body_bytes={len(body)}", text)
                self.assertIn(expected_usage, text)
                self.assertNotEqual(len(body), len(json.dumps(_MESSAGES).encode()))
                for secret in (*credentials.values(), "secret-key", _MESSAGES[0]["content"], _OUTPUT):
                    self.assertNotIn(secret, text)

    def test_anthropic_sdk_uses_actual_httpx_body_and_observed_usage(self):
        captured = []

        def send(request):
            captured.append(request)
            return httpx.Response(200, json={
                "id": "msg_test", "type": "message", "role": "assistant", "model": "test",
                "content": [{"type": "text", "text": _OUTPUT}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 17, "output_tokens": 29},
            })

        default_client = llm.anthropic.DefaultHttpxClient
        with patch.dict(os.environ, {"ANTHROPIC_API_ENABLED": "true", "ANTHROPIC_API_KEY": "secret-key"}), \
                patch.object(llm.anthropic, "DefaultHttpxClient", side_effect=lambda **kwargs:
                             default_client(transport=httpx.MockTransport(send), **kwargs)), \
                self.assertLogs("llm_client", level="INFO") as logs:
            result = llm.AnthropicLLMClient().generate_code(_SYSTEM, "unused", _MESSAGES)
        self.assertEqual(result.encode(), _OUTPUT.encode())
        self.assertEqual(len(captured), 1)
        body = captured[0].content
        self.assertEqual(json.loads(body)["messages"], _MESSAGES)
        text = "\n".join(logs.output)
        self.assertIn(f"http_body_bytes={len(body)}", text)
        self.assertIn("'input_tokens': 17", text)
        self.assertNotIn("secret-key", text)

    def test_missing_usage_is_unavailable_and_never_inferred(self):
        payload = {"choices": [{"message": {"content": _OUTPUT}}]}
        with patch.dict(os.environ, {"DEEPSEEK_API_ENABLED": "true", "DEEPSEEK_API_KEY": "secret"}), \
                patch("requests.adapters.HTTPAdapter.send", autospec=True,
                      side_effect=lambda adapter, request, **kwargs: _response(request, payload)), \
                self.assertLogs("llm_client", level="INFO") as logs:
            result = llm.DeepSeekLLMClient().generate_code(_SYSTEM, "unused", _MESSAGES)
        self.assertEqual(result, _OUTPUT)
        self.assertIn("observed_tokens=unavailable", "\n".join(logs.output))
        with self.assertLogs("llm_client", level="INFO") as logs:
            llm._log_usage("test", {"prompt_tokens": "secret", "input_tokens": True,
                                    "output_tokens": -1, "arbitrary": "secret"})
        self.assertIn("observed_tokens=unavailable", "\n".join(logs.output))
        self.assertNotIn("secret", "\n".join(logs.output))

    def test_transport_failure_measures_prepared_request_without_fabricated_usage(self):
        captured = []

        def send(adapter, request, **kwargs):
            captured.append(request)
            raise requests.ConnectionError("offline", request=request)

        with patch.dict(os.environ, {"DEEPSEEK_API_ENABLED": "true", "DEEPSEEK_API_KEY": "secret"}), \
                patch("requests.adapters.HTTPAdapter.send", autospec=True, side_effect=send), \
                self.assertLogs("llm_client", level="INFO") as logs:
            with self.assertRaisesRegex(RuntimeError, "offline"):
                llm.DeepSeekLLMClient().generate_code(_SYSTEM, "unused", _MESSAGES)
        text = "\n".join(logs.output)
        self.assertIn(f"http_body_bytes={len(captured[0].body)}", text)
        self.assertIn("observed_tokens=unavailable", text)

    def test_fallback_forwards_same_compiled_context_and_keeps_response_bytes(self):
        """Both normal cascade and below-floor fallback reuse caller-owned context."""
        for method, floor in (("generate_plan", 0), ("generate_code", 0), ("generate_code", 1)):
            with self.subTest(method=method, floor=floor):
                seen = []

                class Provider:
                    available = True
                    label = name = "offline test provider"

                    def __init__(self, fail):
                        self.fail = fail

                    def generate_plan(self, system, user, messages):
                        seen.append((system, user, messages, copy.deepcopy(messages)))
                        if self.fail:
                            raise RuntimeError("offline fallback")
                        return _OUTPUT

                    generate_code = generate_plan

                failed, successful = Provider(True), Provider(False)
                chain = llm.LLMClient.__new__(llm.LLMClient)
                providers = [successful, failed] if floor else [failed, successful]
                chain._planners = chain._coders = providers
                chain._min_coder_tier = floor
                chain._api_failed_coders = set()
                original = copy.deepcopy(_MESSAGES)
                with patch.object(llm, "telegram_notify"):
                    result = getattr(chain, method)(_SYSTEM, "unused", _MESSAGES)
                self.assertEqual(result.encode(), _OUTPUT.encode())
                self.assertEqual(len(seen), 2)
                self.assertEqual(_MESSAGES, original)
                for system, user, messages, snapshot in seen:
                    self.assertEqual((system, user), (_SYSTEM, "unused"))
                    self.assertIs(messages, _MESSAGES)
                    self.assertEqual(snapshot, original)


if __name__ == "__main__":
    unittest.main()
