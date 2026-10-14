"""Offline tests only. No authenticated provider or affiliate account is contacted."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from jarvis.hermes import AccessBlocked, MemPalace, Stage, run_swarm
from jarvis.referral_review import build_review, digest, load_registry, validate_registry

ROOT = Path(__file__).resolve().parents[1]


class ReferralReviewTests(unittest.TestCase):
    def setUp(self):
        self.data = load_registry(ROOT / "config/referral-programs.public.json")

    def test_three_channels_are_preserved(self):
        report = build_review(self.data)
        self.assertEqual(len(report["programs"]), 3)
        self.assertEqual(report["programs"][0]["purpose"], "customer_referral")
        self.assertEqual(report["programs"][1]["purpose"], "partner_recruitment")
        self.assertTrue(report["programs"][2]["original_url"].endswith("/lippytmai"))
        self.assertEqual(sum(len(p["unresolved_gates"]) for p in report["programs"]), 18)

    def test_changed_attribution_is_rejected(self):
        for index in range(3):
            data = copy.deepcopy(self.data)
            data["programs"][index]["original_url"] += "x"
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_registry(data)

    def test_https_candidate_cannot_change_destination(self):
        self.data["programs"][0]["https_candidate_url"] = "https://example.org/"
        with self.assertRaises(ValueError):
            validate_registry(self.data)

    def test_duplicate_or_missing_channel_is_rejected(self):
        duplicate = copy.deepcopy(self.data)
        duplicate["programs"][2] = copy.deepcopy(duplicate["programs"][1])
        missing = copy.deepcopy(self.data)
        missing["programs"].pop()
        for data in (duplicate, missing):
            with self.assertRaises(ValueError):
                validate_registry(data)

    def test_side_effect_flags_require_literal_false(self):
        for key in ("network_enabled", "auto_publish", "spend_authorized"):
            for value in (True, 0, "false"):
                data = copy.deepcopy(self.data)
                data[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_registry(data)

    def test_gate_flags_alone_cannot_authorize_release(self):
        for p in self.data["programs"]:
            p["gates"] = dict.fromkeys(p["gates"], "verified")
        report = build_review(self.data)
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["spending_authorized"])
        self.assertFalse(report["live_execution"])
        self.assertEqual(report["provider_calls"], 0)
        self.assertEqual(report["status"], "pending_independent_review")

    def test_unknown_private_field_is_rejected(self):
        self.data["programs"][0]["customer_ssn"] = "synthetic-test-only"
        with self.assertRaises(ValueError):
            validate_registry(self.data)

    def test_invented_commission_is_rejected(self):
        self.data["programs"][0]["commission_rate"] = "50%"
        with self.assertRaises(ValueError):
            validate_registry(self.data)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"auto_publish": true, "auto_publish": false}')
            with self.assertRaises(ValueError):
                load_registry(path)

    def test_large_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b" " * 1_000_001)
            with self.assertRaises(ValueError):
                load_registry(path)

    def test_evidence_persists_and_has_no_raw_referral_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite"
            report = build_review(self.data, MemPalace(path))
            receipt = report.pop("receipt")
            events = MemPalace(path).history(receipt["run_id"], expected_head=receipt["head_sha256"])
            self.assertEqual(events[0]["evidence"]["output_sha256"], digest(report))
            self.assertNotIn("http", json.dumps(events))
            self.assertTrue(receipt["chain_valid"])

    def test_changed_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            receipt = build_review(self.data, ledger)["receipt"]
            db = sqlite3.connect(ledger.path)
            try:
                with db:
                    db.execute("UPDATE events SET evidence_json=?", ('{"forged":true}',))
            finally:
                db.close()
            self.assertFalse(ledger.verify(receipt["run_id"]))
            with self.assertRaises(ValueError):
                ledger.history(receipt["run_id"], expected_head=receipt["head_sha256"])

    def test_blocked_provider_stops_handoff_without_leaking_error(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            calls = []
            def blocked(value):
                raise AccessBlocked("PRIVATE_ERROR_FIXTURE")
            report = run_swarm([Stage("first", "claude-coworker"), Stage("second", "github")], {},
                               {"claude-coworker": blocked, "github": lambda x: calls.append(x)}, ledger)
            self.assertEqual(calls, [])
            self.assertEqual(report["receipts"][0]["status"], "blocked_access")
            self.assertNotIn("PRIVATE_ERROR_FIXTURE", json.dumps(report))

    def test_publication_stops_for_owner_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = MemPalace(Path(directory) / "memory.sqlite")
            calls = []
            report = run_swarm([Stage("release", "hostinger", "publish")], {},
                               {"hostinger": lambda x: calls.append(x)}, ledger)
            self.assertEqual(calls, [])
            self.assertEqual(report["receipts"][0]["status"], "pending_owner_approval")


if __name__ == "__main__":
    unittest.main()
