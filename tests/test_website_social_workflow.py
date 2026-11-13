import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.models import ProviderResponse
from jarvis.workflows import WorkflowRunner


ROOT = Path(__file__).resolve().parents[1]


class WebsiteSocialWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tower = ControlTower(Settings("mock", self.root / "ledger.sqlite3", 5))
        self.runner = WorkflowRunner(self.tower, ROOT / "workflows",
                                     self.root / "outbox", self.root / "runs")

    def test_external_opt_in_is_required_before_any_draft(self):
        with patch.object(self.tower, "run") as invoke:
            report = self.runner.run("website_social_draft", "A supplied publication")
        invoke.assert_not_called()
        self.assertEqual("blocked", report["status"])
        self.assertEqual("skipped", report["steps"][0]["status"])
        self.assertIn("review_handoff", report["not_run_steps"])
        self.assertFalse(list((self.root / "outbox").glob("*.md")))

    def test_provider_handoffs_end_at_owner_review(self):
        outputs = ["Summary of source", "Reviewed summary", "LinkedIn and X drafts"]

        def fake_provider(prompt, provider, system):
            output = outputs.pop(0)
            return ProviderResponse(task_id=provider, provider=provider, model="test", content=output)

        with patch.object(self.tower, "run", side_effect=fake_provider) as invoke:
            report = self.runner.run("website_social_draft", "Source publication", allow_external=True)
        self.assertEqual(["gemini-jarvis", "anthropic", "chatgpt"],
                         [call.args[1] for call in invoke.call_args_list])
        self.assertIn("Summary of source", invoke.call_args_list[1].args[0])
        self.assertIn("Reviewed summary", invoke.call_args_list[2].args[0])
        self.assertEqual("pending_approval", report["status"])
        handoff = report["steps"][3]
        self.assertEqual("drafted", handoff["status"])
        draft = Path(handoff["path"]).read_text(encoding="utf-8")
        self.assertIn("Reviewed summary", draft)
        self.assertIn("LinkedIn and X drafts", draft)
        self.assertIn("No website, workspace, GitHub repository or social platform was modified", draft)
        self.assertEqual("pending_approval", report["steps"][4]["status"])

    def test_provider_failure_stops_downstream_work(self):
        with patch.object(self.tower, "run", side_effect=RuntimeError("provider failure")) as invoke:
            report = self.runner.run("website_social_draft", "Source", allow_external=True)
        self.assertEqual(1, invoke.call_count)
        self.assertEqual("failed", report["status"])
        self.assertIn("review_handoff", report["not_run_steps"])
        self.assertFalse(list((self.root / "outbox").glob("*.md")))


if __name__ == "__main__":
    unittest.main()
