import json
import tempfile
import unittest
from pathlib import Path

from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.workflows import WorkflowRunner


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
        self.runner = WorkflowRunner(tower, self.workflow_dir, root / "outbox")

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


if __name__ == "__main__":
    unittest.main()
