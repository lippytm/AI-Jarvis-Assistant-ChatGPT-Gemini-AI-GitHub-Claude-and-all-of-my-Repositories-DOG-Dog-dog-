"""Regression checks for approval stops, truthful status, and CLI failure gates."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.providers import ProviderError
from jarvis.workflows import WorkflowRunner


class OperationalGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        self.tower = ControlTower(Settings("mock", self.root / "ledger.sqlite3", 5))
        self.runner = WorkflowRunner(self.tower, self.workflows,
                                     self.root / "outbox", self.root / "runs")

    def write(self, steps, name="case"):
        (self.workflows / f"{name}.json").write_text(json.dumps({"steps": steps}), encoding="utf-8")

    def test_pending_approval_stops_every_downstream_step(self):
        self.write([
            {"id": "release", "type": "approval", "summary": "Review before release"},
            {"id": "provider", "type": "ai", "provider": "mock", "prompt": "Do not run"},
            {"id": "delivery", "type": "handoff", "content": "Do not write"},
        ])
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            report = self.runner.run("case", "test")
        invoke.assert_not_called()
        self.assertEqual("pending_approval", report["status"])
        self.assertEqual(["delivery", "provider"], sorted(report["not_run_steps"]))
        self.assertEqual(1, len(report["steps"]))
        self.assertEqual([], list((self.root / "outbox").glob("*.md")))
        repeated = self.runner.run("case", "test")
        self.assertEqual(report["run_id"], repeated["run_id"])
        self.assertEqual(1, len(list((self.root / "approvals").glob("*.json"))))

    def test_disabled_external_step_blocks_handoff_and_is_not_completed(self):
        self.write([
            {"id": "provider", "type": "ai", "provider": "chatgpt", "prompt": "{{input}}"},
            {"id": "delivery", "type": "handoff", "content": "{{steps.provider.output}}"},
        ])
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            report = self.runner.run("case", "test")
        invoke.assert_not_called()
        self.assertEqual("blocked", report["status"])
        self.assertEqual("skipped", report["steps"][0]["status"])
        self.assertEqual(["delivery"], report["not_run_steps"])
        self.assertEqual([], list((self.root / "outbox").glob("*.md")))

    def test_opt_in_change_does_not_reuse_a_skipped_run(self):
        self.write([{"id": "provider", "type": "ai", "provider": "chatgpt", "prompt": "{{input}}"}])
        # Explicit local test double; no provider HTTP request is made.
        self.tower.providers["chatgpt"] = self.tower.providers["mock"]
        first = self.runner.run("case", "test")
        second = self.runner.run("case", "test", allow_external=True)
        self.assertEqual("blocked", first["status"])
        self.assertEqual("completed", second["status"])
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertNotEqual(first["idempotency_key"], second["idempotency_key"])

    def test_changed_definition_gets_a_fresh_result(self):
        self.write([{"id": "draft", "type": "handoff", "content": "version one"}])
        first = self.runner.run("case", "test")
        self.write([{"id": "draft", "type": "handoff", "content": "version two"}])
        second = self.runner.run("case", "test")
        self.assertEqual("version two", second["steps"][0]["output"])
        self.assertNotEqual(first["workflow_sha256"], second["workflow_sha256"])
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_provider_failure_is_recorded_without_exception_body(self):
        self.write([
            {"id": "provider", "type": "ai", "provider": "mock", "prompt": "test"},
            {"id": "draft", "type": "handoff", "content": "Do not write"},
        ])
        with patch.object(self.tower, "run", side_effect=ProviderError("sensitive response body")):
            report = self.runner.run("case", "test")
        self.assertEqual("failed", report["status"])
        self.assertEqual("ProviderError", report["steps"][0]["error_type"])
        self.assertEqual(["draft"], report["not_run_steps"])
        saved = (self.root / "outbox" / f"{report['run_id']}-report.json").read_text()
        self.assertNotIn("sensitive response body", saved)
        self.assertEqual("failed", json.loads(saved)["status"])
        retried = self.runner.run("case", "test")
        self.assertEqual("completed", retried["status"])

    def test_definition_rejects_invalid_fields_before_execution(self):
        bad = [[], {"steps": [{"id": [], "type": "ai", "prompt": "x"}]},
               {"steps": [{"id": "draft", "type": "handoff"}]},
               {"steps": [{"id": "approval", "type": "approval", "summary": []}]},
               {"steps": [{"id": "badtype", "type": []}]},
               {"steps": [{"id": "badtype", "type": {}}]}]
        for definition in bad:
            with self.subTest(definition=definition):
                self.assertTrue(self.runner.validate_definition(definition))

    def test_catalog_rejects_filenames_that_cannot_be_loaded(self):
        self.write([{"id": "draft", "type": "handoff", "content": "test"}], "case.with-dot")
        self.assertTrue(self.runner.validate_all()["case.with-dot"])
        self.assertNotIn("case.with-dot", self.runner.list())


class CLIGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "workflows").mkdir()
        (self.root / ".gitignore").write_text(".env\ndata/\n*.sqlite3\n", encoding="utf-8")
        self.env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
                        JARVIS_DEFAULT_PROVIDER="mock", JARVIS_DB_PATH=str(self.root / "test.sqlite3"))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "jarvis", *args, "--json"],
                              cwd=self.root, env=self.env, capture_output=True, text=True, timeout=15)

    def write(self, definition):
        (self.root / "workflows" / "case.json").write_text(json.dumps(definition), encoding="utf-8")

    def test_invalid_or_empty_workflow_catalog_fails_command(self):
        empty = self.run_cli("validate-workflows")
        self.assertNotEqual(0, empty.returncode)
        self.assertFalse(json.loads(empty.stdout)["valid"])
        for bad in [[], {"steps": []}, {"steps": [{"id": "one", "type": "handoff"}]},
                    {"steps": [{"id": "one", "type": []}]}]:
            with self.subTest(definition=bad):
                self.write(bad)
                result = self.run_cli("validate-workflows")
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(json.loads(result.stdout)["valid"])

    def test_invalid_catalog_filename_fails_doctor(self):
        self.write({"steps": [{"id": "one", "type": "handoff", "content": "test"}]})
        (self.root / "workflows" / "case.json").rename(self.root / "workflows" / "case.with-dot.json")
        result = self.run_cli("doctor")
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertEqual("attention_required", json.loads(result.stdout)["status"])

    def test_doctor_attention_required_fails_command(self):
        result = self.run_cli("doctor")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("attention_required", json.loads(result.stdout)["status"])

    def test_healthy_doctor_does_not_claim_live_readiness(self):
        self.write({"steps": [{"id": "one", "type": "ai", "provider": "mock", "prompt": "test"}]})
        result = self.run_cli("doctor")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ready_local", json.loads(result.stdout)["status"])
        self.assertFalse(json.loads(result.stdout)["live_workflows_ready"])

    def test_pending_and_blocked_runs_have_nonzero_exit(self):
        for step in [
            {"id": "gate", "type": "approval", "summary": "Review first"},
            {"id": "provider", "type": "ai", "provider": "chatgpt", "prompt": "test"},
        ]:
            with self.subTest(step=step):
                self.write({"steps": [step]})
                result = self.run_cli("run", "case", "test")
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertIn(json.loads(result.stdout)["status"], {"pending_approval", "blocked"})


if __name__ == "__main__":
    unittest.main()
