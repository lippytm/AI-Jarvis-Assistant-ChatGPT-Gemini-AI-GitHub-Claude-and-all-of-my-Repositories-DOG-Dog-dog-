from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.outcomes import OutcomeEvidence


class OutcomeEvidenceTests(unittest.TestCase):
    def _file(self, root: Path, records: list[dict]) -> Path:
        path = root / "outcomes.jsonl"
        path.write_text("\n".join(json.dumps(item) for item in records), encoding="utf-8")
        return path

    def test_more_reliable_control_ranks_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = (
                [{"control_id": "A", "success": True}] * 18
                + [{"control_id": "A", "success": False}] * 2
                + [{"control_id": "B", "success": True}] * 5
                + [{"control_id": "B", "success": False}] * 5
            )
            result = OutcomeEvidence().evaluate(self._file(root, records))
            self.assertEqual("A", result["rankings"][0]["control_id"])
            self.assertEqual("limited", result["rankings"][0]["evidence_grade"])

    def test_tiny_perfect_sample_stays_preliminary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = OutcomeEvidence().evaluate(self._file(root, [
                {"control_id": "A", "success": True}
            ]))
            self.assertEqual("preliminary", result["rankings"][0]["evidence_grade"])
            self.assertLess(result["rankings"][0]["wilson_lower_bound"], 0.5)

    def test_invalid_outcome_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "boolean"):
                OutcomeEvidence().evaluate(self._file(root, [
                    {"control_id": "A", "success": "yes"}
                ]))


if __name__ == "__main__":
    unittest.main()
