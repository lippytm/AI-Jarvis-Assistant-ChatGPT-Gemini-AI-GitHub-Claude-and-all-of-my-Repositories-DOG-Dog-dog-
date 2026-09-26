import io
import json
import unittest
from jarvis.workspace_agent import trigger_review

class Response(io.BytesIO):
    status = 202
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

class WorkspaceAgentTests(unittest.TestCase):
    def test_requires_explicit_gates_and_token(self):
        with self.assertRaises(PermissionError):
            trigger_review("Review this affiliate draft")
        with self.assertRaises(ValueError):
            trigger_review("Review this affiliate draft", allow_external=True,
                           approved_for_workspace=True, trigger_id="agtch_example", token="")

    def test_accepted_run_returns_pointer_not_generated_copy(self):
        def opener(request, timeout):
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.get_header("Idempotency-key"), "review_12345678")
            self.assertEqual(json.loads(request.data), {"input": "Review public course descriptions"})
            return Response(json.dumps({"conversation_url": "https://chatgpt.com/c/test123",
                                        "agent_trigger_run_id": "apirun_123"}).encode())
        result = trigger_review("Review public course descriptions", trigger_id="agtch_example",
                                token="test-token", allow_external=True,
                                approved_for_workspace=True, idempotency_key="review_12345678", opener=opener)
        self.assertEqual(result["status"], "accepted")
        self.assertFalse(result["response_text_available"])

    def test_rejects_untrusted_response_url(self):
        def opener(request, timeout):
            return Response(json.dumps({"conversation_url": "https://example.com/c/other"}).encode())
        with self.assertRaises(ValueError):
            trigger_review("Review public copy", trigger_id="agtch_example", token="test-token",
                           allow_external=True, approved_for_workspace=True, opener=opener)

if __name__ == "__main__": unittest.main()
