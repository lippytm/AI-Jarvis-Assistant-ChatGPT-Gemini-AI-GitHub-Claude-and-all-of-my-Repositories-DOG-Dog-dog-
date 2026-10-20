from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.improvement import ImprovementLoop, LoopPolicy


class ImprovementLoopTests(unittest.TestCase):
    def test_repeated_evidence_creates_reviewable_proposal(self) -> None:
        payload = {"findings": [
            {"code": "missing-tests", "severity": "high"},
            {"code": "missing-tests", "severity": "medium"},
            {"code": "stale-repository", "severity": "low"},
        ]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            report = ImprovementLoop(
                LoopPolicy(minimum_repeat_count=2),
                output_dir=root / "out",
            ).run(source)
            self.assertEqual("proposal_only", report["mode"])
            self.assertEqual(1, len(report["proposals"]))
            self.assertFalse(report["proposals"][0]["automatic_execution"])
            self.assertFalse(report["learning_contract"]["model_weights_changed"])
            self.assertTrue((root / "out" / "journal.jsonl").exists())

    def test_single_observation_does_not_overfit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(json.dumps({
                "findings": [{"code": "one-off", "severity": "low"}]
            }), encoding="utf-8")
            report = ImprovementLoop(
                LoopPolicy(minimum_repeat_count=2),
                output_dir=root / "out",
            ).run(source)
            self.assertEqual([], report["proposals"])

    def test_observation_limit_stops_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(json.dumps({"findings": [{}, {}]}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Circuit breaker"):
                ImprovementLoop(
                    LoopPolicy(max_observations=1),
                    output_dir=root / "out",
                ).run(source)

    def test_malformed_observation_container_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text('{"findings": "not-a-list"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "findings or observations"):
                ImprovementLoop(output_dir=root / "out").run(source)


if __name__ == "__main__":
    unittest.main()
