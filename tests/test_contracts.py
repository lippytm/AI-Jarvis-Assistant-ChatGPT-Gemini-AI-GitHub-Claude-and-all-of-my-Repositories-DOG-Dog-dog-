import copy
import unittest

from jsonschema import ValidationError

from engine.contracts import digest, validate, verify_round_trip
from engine.jarvis_engine import WorkEnvelope


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.envelope = {
            "schema_version": "1.0.0", "bundle_id": "offline-example-001",
            "repository": "lippytm/example", "goal": "Review README wording",
            "scope": "README.md only", "risk_class": "reversible-draft",
            "allowed_tools": ["read"], "prohibited_actions": ["merge", "deploy", "external_message"],
            "acceptance_tests": ["Compare both receipts"], "approval_state": "pending",
            "input_hash": digest({"README.md": "example input"}),
        }
        self.results = {
            "openai-codex": {"proposal": "Clarify the setup sentence"},
            "github-copilot": {"proposal": "Clarify the setup sentence"},
        }
        self.receipts = [self.receipt(provider) for provider in self.results]

    def receipt(self, provider):
        return {
            "schema_version": "1.0.0", "bundle_id": self.envelope["bundle_id"],
            "provider": provider, "repository": self.envelope["repository"],
            "branch": "example-draft", "commit": "uncommitted", "files_changed": [],
            "reproduction": "Offline example; no model invoked", "findings": [],
            "checks_run": ["local contract validation"], "check_results": ["pass"],
            "input_hash": self.envelope["input_hash"],
            "result_hash": digest(self.results[provider]), "limitations": "Synthetic receipt; provider identity unverified",
            "rollback": "Discard offline example", "approval_state": "pending", "simulation": True,
        }

    def test_offline_example_passes_and_discloses_simulation(self):
        report = verify_round_trip(self.envelope, self.receipts, self.results)
        self.assertTrue(report["result_agreement"])
        self.assertTrue(report["simulated"])

    def test_engine_work_envelope_matches_shared_schema(self):
        source = self.envelope
        value = WorkEnvelope(
            bundle_id=source["bundle_id"], repository=source["repository"],
            goal=source["goal"], scope=source["scope"], risk_class=source["risk_class"],
            allowed_tools=tuple(source["allowed_tools"]),
            prohibited_actions=tuple(source["prohibited_actions"]),
            acceptance_tests=tuple(source["acceptance_tests"]),
            approval_state=source["approval_state"], input_hash=source["input_hash"],
        ).to_dict()
        validate("work-envelope", value)

    def test_changed_result_is_rejected(self):
        self.results["github-copilot"]["proposal"] = "Tampered"
        with self.assertRaisesRegex(ValueError, "Result hash mismatch"):
            verify_round_trip(self.envelope, self.receipts, self.results)

    def test_cross_bundle_receipt_is_rejected(self):
        self.receipts[0]["bundle_id"] = "other"
        with self.assertRaisesRegex(ValueError, "does not belong"):
            verify_round_trip(self.envelope, self.receipts, self.results)

    def test_duplicate_provider_is_rejected(self):
        self.receipts[1] = copy.deepcopy(self.receipts[0])
        with self.assertRaisesRegex(ValueError, "Exactly one receipt"):
            verify_round_trip(self.envelope, self.receipts, self.results)

    def test_missing_or_invalid_fields_fail_schema(self):
        del self.receipts[0]["rollback"]
        with self.assertRaises(ValidationError):
            validate("diagnostic-receipt", self.receipts[0])
        self.envelope["input_hash"] = "not-a-digest"
        with self.assertRaises(ValidationError):
            validate("work-envelope", self.envelope)


if __name__ == "__main__":
    unittest.main()
