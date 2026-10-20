from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jarvis.audit_evidence import (ANCHOR_PATH, LEDGER_PATH, MANIFEST_PATH, REQUIRED_STEPS,
                                   AuditEvidenceError, create_evidence, main, verify_evidence)


class AuditEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.outcomes = dict.fromkeys(REQUIRED_STEPS, "success")
        self.env = {"GITHUB_REPOSITORY": "lippytm/example", "GITHUB_SHA": "a" * 40,
                    "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
                    "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/main",
                    "UNLISTED_SECRET": "must-never-enter-evidence"}
        self.write("workflow-validation.json", {"valid": True, "workflows": {"safe": []}})
        self.write("jarvis-doctor.json", {"status": "ready_local", "checks": [{"passed": True}]})
        patrol = {"run_id": "patrol-example", "created_at": "2026-10-20T17:00:00+00:00",
                  "mode": "read_only", "repositories_scanned": 2, "findings": [],
                  "policy": dict.fromkeys(("allow_repository_writes", "allow_merges", "allow_deployments",
                                           "allow_external_messages", "allow_spending"), False)}
        patrol["policy"]["max_repositories"] = 250
        self.write("data/patrol/latest.json", patrol)
        self.write("jarvis-patrol.json", patrol | {"report_path": "data/patrol/latest.json"})
        self.improvement = {"cycle_id": "cycle-example", "created_at": "2026-10-20T17:01:00+00:00",
                            "mode": "proposal_only", "observation_count": 0, "proposals": [],
                            "source_sha256": hashlib.sha256((self.root / "data/patrol/latest.json").read_bytes()).hexdigest(),
                            "learning_contract": {"production_mutation": False, "model_weights_changed": False}}
        self.write("data/improvement/latest.json", self.improvement)
        self.write("jarvis-improvement.json", self.improvement | {"report_path": "data/improvement/latest.json"})
        journal = {key: self.improvement[key] for key in ("cycle_id", "created_at", "source_sha256", "observation_count")}
        journal["proposal_count"] = 0
        self.write("data/improvement/journal.jsonl", journal)
        (self.root / "unit-tests.log").write_text("test_example ... ok\n\nRan 2 tests in 0.001s\n\nOK\n")

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=None if relative.endswith(".jsonl") else 2) + "\n",
                        encoding="utf-8")

    def create(self):
        return create_evidence(self.root, self.outcomes, env=self.env)

    def test_success_ties_reports_to_commit_run_and_receipt(self):
        manifest = self.create()
        result = verify_evidence(self.root)
        self.assertIs(result["operational_success"], True)
        self.assertIs(result["integrity_valid"], True)
        self.assertEqual("a" * 40, manifest["payload"]["github"]["sha"])
        self.assertEqual("2", manifest["payload"]["github"]["run_attempt"])
        self.assertEqual("main_public_metadata_audit", result["execution_scope"])
        self.assertEqual(2, manifest["payload"]["summary"]["tests_passed"])
        self.assertIs(manifest["payload"]["scope"]["deployment_performed"], False)
        self.assertNotIn(self.env["UNLISTED_SECRET"], json.dumps(manifest))
        self.assertTrue((self.root / ANCHOR_PATH).is_file())

    def test_pull_request_records_checkout_and_head_separately(self):
        self.env.update(GITHUB_EVENT_NAME="pull_request", GITHUB_REF="refs/pull/6/merge",
                        JARVIS_AUDIT_PR_HEAD_SHA="b" * 40)
        payload = self.create()["payload"]
        self.assertEqual("pull_request_public_metadata_audit", payload["execution_scope"])
        self.assertEqual("a" * 40, payload["github"]["sha"])
        self.assertEqual("b" * 40, payload["github"]["pr_head_sha"])
        self.assertIs(payload["scope"]["deployment_performed"], False)

    def test_failed_skipped_cancelled_or_missing_step_never_succeeds(self):
        for outcome in ("failure", "skipped", "cancelled", ""):
            with self.subTest(outcome=outcome):
                self.outcomes["patrol"] = outcome
                manifest = self.create()
                self.assertIs(manifest["payload"]["operational_success"], False)
                self.assertIs(verify_evidence(self.root)["integrity_valid"], True)

    def test_missing_report_is_preserved_as_failure_evidence(self):
        (self.root / "jarvis-doctor.json").unlink()
        payload = self.create()["payload"]
        self.assertIs(payload["operational_success"], False)
        self.assertIn("missing_or_unsafe_artifact:jarvis-doctor.json", payload["issues"])
        self.assertIs(verify_evidence(self.root)["integrity_valid"], True)

    def test_skipped_tests_are_not_reported_as_all_passed(self):
        (self.root / "unit-tests.log").write_text("Ran 2 tests in 0.001s\n\nOK (skipped=1)\n")
        payload = self.create()["payload"]
        self.assertIs(payload["operational_success"], False)
        self.assertIn("unit_test_summary_not_all_passed", payload["issues"])

    def test_false_json_gate_cannot_be_overridden_by_successful_step(self):
        self.write("workflow-validation.json", {"valid": False, "workflows": {"broken": ["error"]}})
        self.assertIs(self.create()["payload"]["operational_success"], False)

    def test_improvement_must_use_the_exact_patrol_bytes(self):
        self.improvement["source_sha256"] = "0" * 64
        self.write("data/improvement/latest.json", self.improvement)
        payload = self.create()["payload"]
        self.assertIs(payload["operational_success"], False)
        self.assertIn("improvement_source_mismatch", payload["issues"])

    def test_artifact_mutation_is_detected(self):
        self.create()
        (self.root / "unit-tests.log").write_text("changed")
        with self.assertRaises(AuditEvidenceError):
            verify_evidence(self.root)

    def test_manifest_and_ledger_mutation_are_detected(self):
        for relative in (MANIFEST_PATH, LEDGER_PATH):
            with self.subTest(relative=relative):
                self.create()
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(b"changed")
                with self.assertRaises(AuditEvidenceError):
                    verify_evidence(self.root)
                path.write_bytes(original)

    def test_missing_pull_request_head_prevents_success(self):
        self.env.update(GITHUB_EVENT_NAME="pull_request", GITHUB_REF="refs/pull/6/merge")
        self.assertIs(self.create()["payload"]["operational_success"], False)

    def test_cli_returns_nonzero_but_keeps_failure_manifest(self):
        self.outcomes["patrol"] = "skipped"
        args = ["create", "--root", str(self.root)]
        for key, value in self.outcomes.items():
            args.extend(["--step", f"{key}={value}"])
        with patch.dict("os.environ", self.env, clear=True), redirect_stdout(io.StringIO()):
            self.assertEqual(1, main(args))
            self.assertEqual(1, main(["verify", "--root", str(self.root), "--require-success"]))
        self.assertTrue((self.root / MANIFEST_PATH).is_file())


if __name__ == "__main__":
    unittest.main()
