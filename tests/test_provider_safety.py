"""Exercise provider configuration and bounded transports without network access."""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import shutil
import tempfile
import unittest
from email.message import Message
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, build_opener
from urllib.response import addinfourl

from jarvis import providers
from jarvis.cli import main
from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.models import Task
from jarvis.prompt_profiles import PROFILE_ID, PROFILE_PATH, PROFILE_REVISION
from jarvis.workflows import WorkflowRunner


class Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.read_limits = []

    def read(self, size=-1):
        self.read_limits.append(size)
        return super().read(size)


class ProviderSafetyTests(unittest.TestCase):
    adapters = (
        (providers.OpenAIProvider, "OPENAI"),
        (providers.ChatGPTProvider, "OPENAI"),
        (providers.AnthropicProvider, "ANTHROPIC"),
        (providers.GeminiProvider, "GEMINI"),
        (providers.GeminiJarvisProvider, "GEMINI"),
        (providers.PerplexityProvider, "PERPLEXITY"),
    )

    @staticmethod
    def successful_response(prefix):
        if prefix == "OPENAI":
            return {"status": "completed", "output": [{"type": "message", "content": [
                {"type": "output_text", "text": "Verified test draft"}]}]}
        if prefix == "ANTHROPIC":
            return {"stop_reason": "end_turn", "content": [
                {"type": "text", "text": "Verified test draft"}]}
        if prefix == "GEMINI":
            return {"candidates": [{"finishReason": "STOP", "content": {
                "parts": [{"text": "Verified test draft"}]}}]}
        return {"choices": [{"finish_reason": "stop", "message": {"content": "Verified test draft"}}]}

    def test_model_selection_is_required_before_transport(self):
        for adapter, prefix in self.adapters:
            with self.subTest(provider=adapter.__name__), patch.dict(
                "os.environ", {f"{prefix}_API_KEY": "test-only-key"}, clear=True
            ), patch("jarvis.providers._post") as network:
                instance = adapter()
                self.assertFalse(instance.configured())
                with self.assertRaisesRegex(providers.ProviderError, prefix + "_MODEL"):
                    instance.complete(Task("probe", instance.name), 5)
                network.assert_not_called()

    def test_presence_check_requires_both_key_and_valid_model_setting(self):
        for adapter, prefix in self.adapters:
            for key, model, expected in (
                ("", "test-model", False),
                ("   ", "test-model", False),
                ("test-only-key", "", False),
                ("test-only-key", "  ", False),
                ("test-only-key", "not a model", False),
                ("test-only-key", " leading-space", False),
                ("test-only-key", "model\x01name", False),
                ("test-only-key", "x" * 257, False),
                ("test-only-key", "test-model", True),
            ):
                with self.subTest(provider=adapter.__name__, key=bool(key), model=model), patch.dict(
                    "os.environ", {f"{prefix}_API_KEY": key, f"{prefix}_MODEL": model}, clear=True
                ):
                    self.assertEqual(expected, adapter().configured())

    def test_selected_model_shared_guidance_and_output_cap_reach_each_adapter(self):
        for adapter, prefix in self.adapters:
            with self.subTest(provider=adapter.__name__), patch.dict(
                "os.environ", {f"{prefix}_API_KEY": "test-only-key", f"{prefix}_MODEL": "test-model"}, clear=True
            ), patch("jarvis.providers._post", return_value=self.successful_response(prefix)) as network:
                instance = adapter()
                result = instance.complete(Task("probe", instance.name, system="reviewed profile guidance"), 5)
                self.assertEqual("test-model", result.model)
                self.assertEqual("Verified test draft", result.content)
                payload = network.call_args.args[2]
                if prefix == "GEMINI":
                    self.assertIn("models/test-model:generateContent", network.call_args.args[0])
                    self.assertEqual(providers.MAX_OUTPUT_TOKENS, payload["generationConfig"]["maxOutputTokens"])
                    self.assertEqual("reviewed profile guidance", payload["systemInstruction"]["parts"][0]["text"])
                else:
                    self.assertEqual("test-model", payload["model"])
                    limit_key = "max_output_tokens" if prefix == "OPENAI" else "max_tokens"
                    self.assertEqual(providers.MAX_OUTPUT_TOKENS, payload[limit_key])
                    if prefix == "OPENAI":
                        self.assertEqual("reviewed profile guidance", payload["instructions"])
                    elif prefix == "ANTHROPIC":
                        self.assertEqual("reviewed profile guidance", payload["system"])
                    else:
                        self.assertEqual({"role": "system", "content": "reviewed profile guidance"}, payload["messages"][0])

    def test_invalid_credentials_stop_before_transport_without_cli_disclosure(self):
        for adapter, prefix in self.adapters:
            for bad_key in ("SYNTHETIC_REVIEW_SECRET\ninvalid-tail", "bad\rkey", "bad\x01key", "bad\u00e9key", "   "):
                with self.subTest(provider=adapter.__name__), tempfile.TemporaryDirectory() as temp, patch.dict(
                    "os.environ", {f"{prefix}_API_KEY": bad_key, f"{prefix}_MODEL": "test-model",
                                   "JARVIS_DB_PATH": str(Path(temp) / "ledger.sqlite3")}, clear=True
                ), patch("jarvis.providers._post") as network:
                    self.assertFalse(adapter().configured())
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        code = main(["ask", "offline review probe", "--provider", adapter().name, "--json"])
                    self.assertEqual(2, code)
                    self.assertIn(prefix + "_API_KEY is missing or invalid", err.getvalue())
                    self.assertNotIn(bad_key, out.getvalue() + err.getvalue())
                    self.assertNotIn("SYNTHETIC_REVIEW_SECRET", out.getvalue() + err.getvalue())
                    network.assert_not_called()

    def test_request_construction_and_header_errors_are_sanitized(self):
        for stage in ("construction", "header"):
            with self.subTest(stage=stage):
                error = ValueError("SYNTHETIC_REVIEW_SECRET must not reach callers")
                target = "jarvis.providers.Request" if stage == "construction" else "jarvis.providers.build_opener"
                with patch(target) as mocked:
                    if stage == "construction":
                        mocked.side_effect = error
                    else:
                        mocked.return_value.open.side_effect = error
                    with self.assertRaises(providers.ProviderError) as caught:
                        providers._post("https://provider.invalid", {}, {}, 5)
                self.assertEqual("Provider request failed: ValueError", str(caught.exception))
                self.assertNotIn("SYNTHETIC_REVIEW_SECRET", str(caught.exception))

    def test_missing_malformed_and_empty_native_text_is_rejected(self):
        for adapter, prefix in self.adapters:
            empty = json.loads(json.dumps(self.successful_response(prefix)).replace("Verified test draft", "   "))
            malformed = json.loads(json.dumps(self.successful_response(prefix)).replace('"Verified test draft"', '{}'))
            for response in ({}, {"error": {"message": "private upstream explanation"}}, empty, malformed):
                with self.subTest(provider=adapter.__name__, response=response), patch.dict(
                    "os.environ", {f"{prefix}_API_KEY": "test-only-key", f"{prefix}_MODEL": "test-model"}, clear=True
                ), patch("jarvis.providers._post", return_value=response):
                    with self.assertRaises(providers.ProviderError) as caught:
                        adapter().complete(Task("probe", adapter().name), 5)
                    self.assertNotIn("private upstream explanation", str(caught.exception))

    def test_truncated_blocked_or_unfinished_native_text_is_rejected(self):
        failures = {
            "OPENAI": [("status", "incomplete"), ("status", "failed"), ("status", "in_progress")],
            "ANTHROPIC": [("stop_reason", "max_tokens"), ("stop_reason", "tool_use"),
                          ("stop_details", {"type": "refusal"})],
            "GEMINI": [("finishReason", "MAX_TOKENS"), ("finishReason", "SAFETY"),
                       ("safetyRatings", [{"blocked": True}]), ("promptFeedback", {"blockReason": "SAFETY"}),
                       ("promptFeedback", {"safetyRatings": [{"blocked": True}]})],
            "PERPLEXITY": [("finish_reason", "length"), ("finish_reason", "content_filter")],
        }
        for adapter, prefix in self.adapters:
            for field, value in failures[prefix]:
                response = self.successful_response(prefix)
                target = response
                if prefix == "GEMINI" and field != "promptFeedback":
                    target = response["candidates"][0]
                elif prefix == "PERPLEXITY":
                    target = response["choices"][0]
                target[field] = value
                with self.subTest(provider=adapter.__name__, field=field, value=value), patch.dict(
                    "os.environ", {f"{prefix}_API_KEY": "test-only-key", f"{prefix}_MODEL": "test-model"}, clear=True
                ), patch("jarvis.providers._post", return_value=response):
                    with self.assertRaises(providers.ProviderError):
                        adapter().complete(Task("probe", adapter().name), 5)

    def test_empty_provider_result_stops_handoff_and_success_cache(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ", {"GEMINI_API_KEY": "test-only-key", "GEMINI_MODEL": "test-model"}, clear=True
        ), patch("jarvis.providers._post", return_value={}) as network:
            root = Path(temp)
            workflow_dir = root / "workflows"
            workflow_dir.mkdir()
            (root / "config").mkdir()
            shutil.copyfile(Path(__file__).resolve().parents[1] / PROFILE_PATH, root / PROFILE_PATH)
            definition = {"prompt_profile": {"id": PROFILE_ID, "revision": PROFILE_REVISION}, "steps": [
                {"id": "draft", "type": "ai", "provider": "gemini", "prompt": "{{input}}"},
                {"id": "handoff", "type": "handoff", "content": "{{steps.draft.output}}"}]}
            (workflow_dir / "case.json").write_text(json.dumps(definition))
            tower = ControlTower(Settings("mock", root / "ledger.sqlite3", 5))
            runner = WorkflowRunner(tower, workflow_dir, root / "outbox", root / "runs")
            report = runner.run("case", "offline validation", allow_external=True)
            self.assertEqual("failed", report["status"])
            self.assertEqual("ProviderError", report["steps"][0]["error_type"])
            self.assertEqual(["handoff"], report["not_run_steps"])
            self.assertEqual([], list((root / "outbox").glob("*.md")))
            self.assertEqual([], list((root / "runs").glob("*.json")))
            repeated = runner.run("case", "offline validation", allow_external=True)
            self.assertNotEqual(report["run_id"], repeated["run_id"])
            self.assertEqual(2, network.call_count)

    def test_explicit_refusal_with_partial_text_cannot_pass_success(self):
        for adapter, prefix in self.adapters:
            if prefix not in ("OPENAI", "PERPLEXITY"):
                continue
            for convenience_text in (False, True):
                response = self.successful_response(prefix)
                if prefix == "OPENAI":
                    response["output"][0]["content"].append(
                        {"type": "refusal", "refusal": "private refusal explanation"})
                    if convenience_text:
                        response["output_text"] = "Partial introductory text."
                else:
                    response["choices"][0]["message"]["refusal"] = "private refusal explanation"
                with self.subTest(provider=adapter.__name__, convenience_text=convenience_text), patch.dict(
                    "os.environ", {f"{prefix}_API_KEY": "test-only-key", f"{prefix}_MODEL": "test-model"}, clear=True
                ), patch("jarvis.providers._post", return_value=response):
                    with self.assertRaises(providers.ProviderError) as caught:
                        adapter().complete(Task("probe", adapter().name), 5)
                    self.assertNotIn("private refusal explanation", str(caught.exception))

    def test_mock_needs_no_external_configuration(self):
        with patch.dict("os.environ", {}, clear=True), patch("jarvis.providers._post") as network:
            instance = providers.MockProvider()
            self.assertTrue(instance.configured())
            self.assertEqual("mock-v1", instance.complete(Task("probe", "mock"), 5).model)
            network.assert_not_called()

    def test_successful_transport_has_a_bounded_read_and_closes_response(self):
        response = Response(b'{"answer":"ok"}')
        opener = Mock()
        opener.open.return_value = response
        with patch("jarvis.providers.build_opener", return_value=opener):
            self.assertEqual({"answer": "ok"}, providers._post("https://provider.invalid", {}, {}, 5))
        self.assertEqual([providers.MAX_RESPONSE_BYTES + 1], response.read_limits)
        self.assertTrue(response.closed)
        self.assertEqual(5, opener.open.call_args.kwargs["timeout"])

    def test_oversized_response_is_rejected_before_json_parsing(self):
        response = Response(b"x" * (providers.MAX_RESPONSE_BYTES + 2))
        opener = Mock()
        opener.open.return_value = response
        with patch("jarvis.providers.build_opener", return_value=opener):
            with self.assertRaisesRegex(providers.ProviderError, "exceeded the local pilot limit"):
                providers._post("https://provider.invalid", {}, {}, 5)
        self.assertEqual([providers.MAX_RESPONSE_BYTES + 1], response.read_limits)
        self.assertTrue(response.closed)

    def test_upstream_http_body_is_never_read_or_reported(self):
        body = Response(b"private upstream content")
        error = HTTPError("https://provider.invalid", 403, "private reason", Message(), body)
        opener = Mock()
        opener.open.side_effect = error
        with patch("jarvis.providers.build_opener", return_value=opener):
            with self.assertRaises(providers.ProviderError) as caught:
                providers._post("https://provider.invalid", {}, {}, 5)
        self.assertEqual("Provider returned HTTP 403", str(caught.exception))
        self.assertEqual([], body.read_limits)
        self.assertTrue(body.closed)

    def test_invalid_json_encodings_and_nonobject_results_fail_closed(self):
        for raw in (b"not-json", b"\xff", b"[]", b"null"):
            with self.subTest(raw=raw):
                opener = Mock()
                opener.open.return_value = Response(raw)
                with patch("jarvis.providers.build_opener", return_value=opener):
                    with self.assertRaises(providers.ProviderError):
                        providers._post("https://provider.invalid", {}, {}, 5)

    def test_redirect_does_not_request_a_second_destination(self):
        class FakeHTTP(HTTPHandler):
            def __init__(self):
                super().__init__()
                self.requests = []

            def http_open(self, request):
                self.requests.append(request.full_url)
                headers = Message()
                headers["Location"] = "http://redirect.invalid/target"
                reply = addinfourl(io.BytesIO(b"upstream body"), headers, request.full_url, code=302)
                reply.msg = "Found"
                return reply

        fake = FakeHTTP()
        with patch("jarvis.providers.build_opener", side_effect=lambda *handlers: build_opener(*handlers, fake)):
            with self.assertRaisesRegex(providers.ProviderError, "HTTP 302"):
                providers._post("http://source.invalid", {"Authorization": "Bearer test-only-key"}, {}, 5)
        self.assertEqual(["http://source.invalid"], fake.requests)

    def test_network_error_reports_only_exception_type(self):
        opener = Mock()
        opener.open.side_effect = URLError("private network detail")
        with patch("jarvis.providers.build_opener", return_value=opener):
            with self.assertRaises(providers.ProviderError) as caught:
                providers._post("https://provider.invalid", {}, {}, 5)
        self.assertEqual("Provider request failed: URLError", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
