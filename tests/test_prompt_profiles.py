"""Exercise real profile composition and evidence with local providers only."""

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from jarvis.cli import main
from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.prompt_profiles import (PROFILE_ID, PROFILE_PATH, PROFILE_REVISION,
                                    PromptProfileError, load_prompt_profile)
from jarvis.workflows import WorkflowError, WorkflowRunner


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = {"id": PROFILE_ID, "revision": PROFILE_REVISION}
CATALOG = {"affiliate_site_review", "jarvis_problem_council", "life_business_daily_briefing",
           "multi_ai_business_review", "prompt_11_product_factory", "repository_fleet_review",
           "unified_life_business_creation"}


class PromptProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        (self.root / "config").mkdir()
        self.profile_path = self.root / PROFILE_PATH
        shutil.copyfile(REPO_ROOT / PROFILE_PATH, self.profile_path)
        self.tower = ControlTower(Settings("mock", self.root / "ledger.sqlite3", 5))
        self.runner = WorkflowRunner(self.tower, self.workflows,
                                     self.root / "outbox", self.root / "runs")
        self.write([{"id": "draft", "type": "ai", "provider": "mock",
                     "system": "Existing draft role.", "prompt": "Draft {{input}}"}])

    def write(self, steps, *, name="case", reference=REFERENCE):
        value = {"steps": steps}
        if reference is not None:
            value["prompt_profile"] = reference
        (self.workflows / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")

    def profile(self):
        return load_prompt_profile(REFERENCE, self.root)

    def test_all_seven_shipping_workflows_have_verifiable_coverage(self):
        runner = WorkflowRunner(self.tower, REPO_ROOT / "workflows")
        result = runner.validate_catalog()
        self.assertIs(result["valid"], True, result)
        self.assertEqual(CATALOG, set(result["workflows"]))
        coverage = result["prompt_profile_coverage"]
        self.assertIs(coverage["complete"], True)
        self.assertEqual((7, 7), (coverage["workflow_count"], coverage["covered_count"]))
        self.assertEqual([], coverage["uncovered_workflows"])
        actual_hash = sha256((REPO_ROOT / PROFILE_PATH).read_bytes()).hexdigest()
        for name, item in coverage["workflows"].items():
            self.assertEqual(REFERENCE | {"sha256": actual_hash}, item["prompt_profile"])
            definition = json.loads((REPO_ROOT / "workflows" / f"{name}.json").read_text())
            normalized = json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
            self.assertEqual(sha256(normalized).hexdigest(), item["workflow_sha256"])
        encoded = json.dumps(coverage["workflows"], sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(sha256(encoded).hexdigest(), coverage["catalog_sha256"])

    def test_every_ai_step_receives_shared_guidance_and_its_existing_role(self):
        self.write([
            {"id": "draft", "type": "ai", "provider": "mock", "system": "Existing draft role.",
             "prompt": "Draft {{input}}"},
            {"id": "review", "type": "ai", "provider": "mock", "system": "Independent review role.",
             "prompt": "Review {{steps.draft.output}}"},
        ])
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            report = self.runner.run("case", "test-only source text")
        self.assertEqual("completed", report["status"])
        self.assertEqual(2, invoke.call_count)
        for call, role in zip(invoke.call_args_list, ("Existing draft role.", "Independent review role.")):
            system = call.args[2]
            self.assertIn("Step-specific role:\n" + role, system)
            self.assertNotIn("test-only source text", system)
            for text in self.profile().guidance:
                self.assertIn(text, system)
        self.assertEqual(self.profile().metadata(), report["prompt_profile"])

    def test_plan_resolves_profile_without_calling_providers(self):
        with patch.object(self.tower, "run") as invoke:
            plan = self.runner.plan("case", "preview")
        invoke.assert_not_called()
        self.assertIs(plan["will_execute"], False)
        self.assertEqual("resolved", plan["profile_status"])
        self.assertEqual(self.profile().metadata(), plan["prompt_profile"])
        report = self.runner.run("case", "preview")
        self.assertEqual(plan["workflow_sha256"], report["workflow_sha256"])
        self.assertEqual(plan["prompt_profile"], report["prompt_profile"])

    def test_content_change_invalidates_cache_even_with_same_profile_revision(self):
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            first = self.runner.run("case", "same input")
            repeated = self.runner.run("case", "same input")
            self.assertIs(repeated["reused"], True)
            value = json.loads(self.profile_path.read_text())
            value["guidance"][0]["text"] += " Include the reviewed completion checkpoint."
            self.profile_path.write_text(json.dumps(value), encoding="utf-8")
            changed = self.runner.run("case", "same input")
        self.assertEqual(2, invoke.call_count)
        self.assertEqual(first["workflow_sha256"], changed["workflow_sha256"])
        self.assertNotEqual(first["prompt_profile"]["sha256"], changed["prompt_profile"]["sha256"])
        self.assertNotEqual(first["idempotency_key"], changed["idempotency_key"])
        self.assertNotEqual(first["run_id"], changed["run_id"])
        self.assertIn("reviewed completion checkpoint", invoke.call_args.args[2])

    def test_unknown_reference_fails_before_execution_even_in_ad_hoc_mode(self):
        self.runner.allow_unprofiled = True
        for reference in (REFERENCE | {"id": "unreviewed"}, REFERENCE | {"revision": "future"},
                          REFERENCE | {"path": "other.json"}, None):
            if reference is None:
                # A present null reference is invalid; only an absent key may be opted out.
                path = self.workflows / "case.json"
                value = json.loads(path.read_text())
                value["prompt_profile"] = None
                path.write_text(json.dumps(value))
            else:
                self.write([{"id": "one", "type": "ai", "provider": "mock", "prompt": "test"}],
                           reference=reference)
            with self.subTest(reference=reference), patch.object(self.tower, "run") as invoke:
                with self.assertRaises(WorkflowError):
                    self.runner.run("case", "test")
                with self.assertRaises(WorkflowError):
                    self.runner.plan("case", "test")
                invoke.assert_not_called()

    def test_missing_or_inconsistent_profile_file_fails_closed(self):
        original = self.profile_path.read_bytes()
        broken = json.loads(original)
        broken["revision"] = "unknown"
        for data in (None, b"[]", b'{"id":"one","id":"two"}', json.dumps(broken).encode()):
            with self.subTest(data=data):
                if data is None:
                    self.profile_path.unlink()
                else:
                    self.profile_path.write_bytes(data)
                with patch.object(self.tower, "run") as invoke:
                    with self.assertRaises(WorkflowError):
                        self.runner.run("case", "test")
                    invoke.assert_not_called()
                self.assertIs(self.runner.validate_catalog()["valid"], False)
                self.profile_path.write_bytes(original)

    def test_profile_cannot_drop_required_operating_guidance(self):
        value = json.loads(self.profile_path.read_text())
        value["guidance"] = value["guidance"][:-1]
        self.profile_path.write_text(json.dumps(value))
        with self.assertRaises(PromptProfileError):
            self.profile()

    def test_ad_hoc_opt_out_is_explicit_and_never_exempts_catalog_validation(self):
        self.write([{"id": "draft", "type": "handoff", "content": "local fixture"}], reference=None)
        with self.assertRaises(WorkflowError):
            self.runner.run("case", "test")
        self.runner.allow_unprofiled = True
        plan = self.runner.plan("case", "test")
        report = self.runner.run("case", "test")
        for value in (plan, report):
            self.assertIsNone(value["prompt_profile"])
            self.assertEqual("unprofiled_ad_hoc", value["profile_status"])
        catalog = self.runner.validate_catalog()
        self.assertIs(catalog["valid"], False)
        self.assertEqual(["case"], catalog["prompt_profile_coverage"]["uncovered_workflows"])

    def test_new_unprofiled_catalog_entry_prevents_complete_coverage(self):
        self.write([{"id": "draft", "type": "handoff", "content": "new entry"}],
                   name="new_workflow", reference=None)
        result = self.runner.validate_catalog()
        coverage = result["prompt_profile_coverage"]
        self.assertIs(result["valid"], False)
        self.assertIs(coverage["complete"], False)
        self.assertEqual((2, 1), (coverage["workflow_count"], coverage["covered_count"]))
        self.assertEqual(["new_workflow"], coverage["uncovered_workflows"])

    def test_profile_does_not_authorize_external_calls_or_downstream_drafts(self):
        self.write([
            {"id": "external", "type": "ai", "provider": "chatgpt", "prompt": "test"},
            {"id": "handoff", "type": "handoff", "content": "must not be written"},
        ])
        with patch.object(self.tower, "run") as invoke:
            report = self.runner.run("case", "test")
        invoke.assert_not_called()
        self.assertEqual("blocked", report["status"])
        self.assertEqual(["handoff"], report["not_run_steps"])
        self.assertEqual([], list((self.root / "outbox").glob("*.md")))
        self.assertEqual(self.profile().metadata(), report["prompt_profile"])

    def test_profile_does_not_bypass_approval_or_duplicate_its_handoff(self):
        self.write([
            {"id": "gate", "type": "approval", "summary": "Owner release decision needed"},
            {"id": "ai", "type": "ai", "provider": "mock", "prompt": "must not run"},
            {"id": "handoff", "type": "handoff", "content": "must not be written"},
        ])
        with patch.object(self.tower, "run") as invoke:
            first = self.runner.run("case", "test")
            repeated = self.runner.run("case", "test")
        invoke.assert_not_called()
        self.assertEqual("pending_approval", first["status"])
        self.assertEqual(first["run_id"], repeated["run_id"])
        self.assertEqual(["ai", "handoff"], first["not_run_steps"])
        self.assertEqual(1, len(list((self.root / "approvals").glob("*.json"))))

    def test_existing_sensitive_input_and_call_budget_gates_remain(self):
        with patch.object(self.tower, "run") as invoke:
            with self.assertRaisesRegex(WorkflowError, "Sensitive input"):
                self.runner.run("case", "sk-abcdefghijklmnopqrstuvwxyz123456")
            self.write([{"id": f"call{index}", "type": "ai", "provider": "chatgpt", "prompt": "test"}
                        for index in range(7)])
            with self.assertRaisesRegex(WorkflowError, "budget"):
                self.runner.run("case", "test", allow_external=True)
        invoke.assert_not_called()

    def test_non_ai_workflow_gets_metadata_without_provider_calls(self):
        self.write([{"id": "draft", "type": "handoff", "content": "draft only"}])
        with patch.object(self.tower, "run") as invoke:
            report = self.runner.run("case", "test")
        invoke.assert_not_called()
        self.assertEqual("drafted", report["steps"][0]["status"])
        self.assertEqual(self.profile().metadata(), report["prompt_profile"])
        self.assertEqual("draft only", Path(report["steps"][0]["path"]).read_text())

    def test_cli_reports_coverage_and_returns_nonzero_for_missing_reference(self):
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(self.root)
        with patch.dict(os.environ, {"JARVIS_DB_PATH": str(self.root / "cli.sqlite3")}):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(0, main(["validate-workflows", "--json"]))
            result = json.loads(output.getvalue())
            self.assertIs(result["valid"], True)
            self.assertEqual({"case": []}, result["workflows"])
            self.assertIs(result["prompt_profile_coverage"]["complete"], True)
            self.write([{"id": "draft", "type": "handoff", "content": "test"}], reference=None)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(1, main(["validate-workflows", "--json"]))
            self.assertIs(json.loads(output.getvalue())["valid"], False)


if __name__ == "__main__":
    unittest.main()
