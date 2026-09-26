import json
import tempfile
import unittest
from pathlib import Path

from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.workflows import WorkflowRunner
from jarvis.safety import find_sensitive, redact


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.workflow_dir = root / "workflows"
        self.workflow_dir.mkdir()
        definition = {"steps": [
            {"id": "draft", "type": "ai", "provider": "mock", "prompt": "Plan: {{input}}"},
            {"id": "handoff", "type": "handoff", "destination": "chatgpt-business",
             "content": "Result: {{steps.draft.output}}"}]}
        (self.workflow_dir / "test.json").write_text(json.dumps(definition), encoding="utf-8")
        tower = ControlTower(Settings("mock", root / "ledger.sqlite3", 5))
        self.runner = WorkflowRunner(tower, self.workflow_dir, root / "outbox", root / "runs")

    def tearDown(self):
        self.temp.cleanup()

    def test_workflow_round_trip_and_draft_handoff(self):
        report = self.runner.run("test", "launch safely")
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["steps"][1]["status"], "drafted")
        self.assertIn("launch safely", report["steps"][1]["output"])
        self.assertTrue(Path(report["steps"][1]["path"]).is_file())

    def test_external_provider_requires_opt_in(self):
        definition = {"steps": [{"id": "x", "type": "ai", "provider": "perplexity",
                                  "prompt": "{{input}}"}]}
        (self.workflow_dir / "external.json").write_text(json.dumps(definition), encoding="utf-8")
        report = self.runner.run("external", "question")
        self.assertEqual(report["steps"][0]["status"], "skipped")

    def test_duplicate_run_is_reused(self):
        first = self.runner.run("test", "same request")
        second = self.runner.run("test", "same request")
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertTrue(second["reused"])

    def test_validation_rejects_duplicate_ids(self):
        errors = self.runner.validate_definition({"steps": [
            {"id": "same", "type": "ai", "prompt": "one"},
            {"id": "same", "type": "handoff", "content": "two"}]})
        self.assertTrue(any("duplicates" in error for error in errors))

    def test_plan_does_not_execute(self):
        plan = self.runner.plan("test", "preview")
        self.assertFalse(plan["will_execute"])
        self.assertEqual(plan["external_calls"], 0)

    def test_sensitive_credentials_are_blocked_and_redacted(self):
        secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
        self.assertTrue(find_sensitive(secret))
        self.assertNotIn(secret, redact(secret))
        with self.assertRaisesRegex(Exception, "Sensitive input"):
            self.runner.run("test", secret)


if __name__ == "__main__":
    unittest.main()
