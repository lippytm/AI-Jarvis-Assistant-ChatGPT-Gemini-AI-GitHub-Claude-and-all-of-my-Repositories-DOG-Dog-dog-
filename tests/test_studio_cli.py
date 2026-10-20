"""Exercise real public pilot inputs, CLI boundaries, and source-change recovery."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jarvis.cli import main


REPOSITORY = Path(__file__).resolve().parents[1]


class StudioCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        for name in ("creative-studio.public.json", "prompt-11-profile.json"):
            shutil.copyfile(REPOSITORY / "config" / name, self.root / "config" / name)
        self.example = self.root / "pilot"
        shutil.copytree(REPOSITORY / "examples/studio-workforce-pilot", self.example)
        self.brief = self.example / "production-brief.json"
        self.ledger = self.root / "unexpected-ledger.sqlite3"
        self.env = dict(os.environ, PYTHONPATH=str(REPOSITORY / "src"),
                        JARVIS_DEFAULT_PROVIDER="invalid-provider-must-not-be-initialized",
                        JARVIS_DB_PATH=str(self.ledger))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "jarvis", *map(str, args), "--json"],
                              cwd=self.root, env=self.env, capture_output=True,
                              text=True, timeout=30)

    def packet(self, name="packet"):
        path = self.root / name
        result = self.run_cli("studio-plan", self.brief, "--output", path)
        return path, result

    def write_brief(self, value):
        self.brief.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_all_new_commands_bypass_control_tower_and_network(self):
        commands = [
            ["studio-plan", str(self.brief), "--output", str(self.root / "direct"), "--json"],
            ["verify-studio-plan", str(self.root / "direct"), "--json"],
            ["studio-economics", str(self.example / "economics.json"), "--json"],
        ]
        with patch("jarvis.cli.ControlTower", side_effect=AssertionError("No runtime initialization")), \
                patch("pathlib.Path.cwd", return_value=self.root), \
                patch("urllib.request.urlopen", side_effect=AssertionError("No network")), \
                patch("socket.create_connection", side_effect=AssertionError("No network")):
            for command in commands:
                with self.subTest(command=command[0]), redirect_stdout(StringIO()) as out:
                    self.assertEqual(0, main(command))
                    result = json.loads(out.getvalue())
                    self.assertIn("status", result)
        self.assertFalse(self.ledger.exists())
        self.assertFalse((self.root / "data").exists())

    def test_real_four_asset_pilot_round_trip_keeps_source_bytes_and_limits(self):
        path, result = self.packet()
        self.assertEqual(0, result.returncode, result.stderr)
        built = json.loads(result.stdout)
        self.assertEqual("prepared_for_review", built["status"])
        self.assertEqual("release_blocked", built["release_status"])
        self.assertEqual(13, built["file_count"])
        self.assertEqual(["chapter", "narration", "short_video", "video_book"], built["dependency_order"])
        self.assertEqual([], built["blockers"])
        self.assertEqual(4, len(built["formats"]))
        self.assertTrue(all(item["status"] == "prepared_for_review" for item in built["formats"]))
        self.assertEqual({"provider_calls": 0, "media_rendered": False, "published": False,
                          "external_handoff_sent": False, "approval_granted": False,
                          "shared_memory_sync": False}, built["execution"])
        brief = json.loads(self.brief.read_text())
        for source in brief["assets"]:
            observed = next(asset for asset in built["assets"] if asset["id"] == source["id"])
            self.assertEqual((self.example / source["path"]).read_bytes(),
                             (path / observed["packet_path"]).read_bytes())
            self.assertEqual("not_reviewed", observed["review_status"])
        checked = self.run_cli("verify-studio-plan", path)
        self.assertEqual(0, checked.returncode, checked.stderr)
        self.assertEqual(built, json.loads(checked.stdout))
        self.assertFalse(self.ledger.exists())

    def test_changed_source_returns_blocked_packet_that_still_verifies(self):
        source = self.example / "assets/chapter-06.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nA changed-source exercise.\n", encoding="utf-8")
        path, result = self.packet()
        self.assertEqual(1, result.returncode, result.stderr)
        blocked = json.loads(result.stdout)
        self.assertEqual("blocked", blocked["status"])
        self.assertEqual("stale_source", blocked["assets"][0]["status"])
        self.assertTrue(all(asset["status"] != "prepared_for_review" for asset in blocked["assets"]))
        checked = self.run_cli("verify-studio-plan", path)
        self.assertEqual(0, checked.returncode, checked.stderr)
        self.assertEqual("blocked", json.loads(checked.stdout)["status"])
        self.assertEqual("release_blocked", json.loads(checked.stdout)["release_status"])

    def test_updating_only_parent_declaration_does_not_refresh_adaptations(self):
        source = self.example / "assets/chapter-06.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nA revised source.\n", encoding="utf-8")
        brief = json.loads(self.brief.read_text())
        brief["assets"][0]["sha256"] = sha256(source.read_bytes()).hexdigest()
        self.write_brief(brief)
        _, result = self.packet()
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("prepared_for_review", report["assets"][0]["status"])
        for asset in report["assets"][1:]:
            self.assertEqual("blocked", asset["status"])
            self.assertIn("parent_declared_hash_mismatch:chapter", asset["blockers"])

    def test_verifier_cli_fails_after_readiness_or_source_tampering(self):
        path, result = self.packet()
        self.assertEqual(0, result.returncode, result.stderr)
        plan_path = path / "production-plan.json"
        plan = json.loads(plan_path.read_text())
        plan["release_status"] = "published"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        checked = self.run_cli("verify-studio-plan", path)
        self.assertEqual(2, checked.returncode)
        self.assertEqual("", checked.stdout)
        self.assertIn("Jarvis error:", checked.stderr)
        self.assertNotIn("Traceback", checked.stderr)
        self.assertFalse(self.ledger.exists())

    def test_overwrite_and_invalid_brief_fail_without_runtime_initialization(self):
        path, first = self.packet()
        self.assertEqual(0, first.returncode, first.stderr)
        original_manifest = (path / "manifest.json").read_bytes()
        duplicate = self.run_cli("studio-plan", self.brief, "--output", path)
        self.assertEqual(2, duplicate.returncode)
        self.assertEqual(original_manifest, (path / "manifest.json").read_bytes())
        value = json.loads(self.brief.read_text())
        value["published"] = True
        self.write_brief(value)
        _, invalid = self.packet("invalid")
        self.assertEqual(2, invalid.returncode)
        self.assertFalse((self.root / "invalid").exists())
        self.assertFalse(self.ledger.exists())

    def test_example_economics_preserves_hypotheses_and_cash_labor_difference(self):
        result = self.run_cli("studio-economics", self.example / "economics.json")
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("hypothetical_scenarios_only", report["status"])
        self.assertEqual("provided_unverified_assumptions", report["qualifications"]["assumptions_status"])
        self.assertFalse(report["qualifications"]["measured_actuals_included"])
        self.assertFalse(report["qualifications"]["spend_approved"])
        expected = [(0, -6000, -14000), (10, 2050, -5950), (25, 14125, 6125), (50, 34250, 26250)]
        for scenario, (units, cash, after_labor) in zip(report["scenarios"], expected):
            self.assertEqual(units, scenario["assumptions"]["expected_units"])
            self.assertEqual(cash, scenario["calculations"]["expected_cash_result_after_fixed_cost_minor"])
            self.assertEqual(after_labor, scenario["calculations"]["expected_result_after_labor_opportunity_cost_minor"])
            self.assertEqual({"status": "finite", "cash_units": 8, "including_labor_units": 18}, scenario["break_even"])
        self.assertEqual(len(expected), len(report["scenarios"]))
        self.assertFalse(self.ledger.exists())

    def test_invalid_economics_cli_has_controlled_error_and_no_side_effects(self):
        bad = self.root / "bad.json"
        bad.write_text('{"schema":"jarvis.studio-economics.v1","currency":"USD","scenarios":[],"actual_sales":99}')
        result = self.run_cli("studio-economics", bad)
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("Jarvis error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
