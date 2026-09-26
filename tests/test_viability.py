from __future__ import annotations

import unittest

from jarvis.viability import ViabilityEngine


class ViabilityTests(unittest.TestCase):
    def test_complete_design_is_sandbox_ready(self) -> None:
        design = {"name": "safe pilot"}
        for key in (
            "clear_outcome", "evidence", "owner", "dependencies", "observability",
            "testability", "reversibility", "rollback", "cost_cap", "security_privacy",
        ):
            design[key] = f"Documented {key} with measurable controls"
        result = ViabilityEngine().assess(design)
        self.assertEqual(100, result.score)
        self.assertEqual("sandbox_ready", result.status)

    def test_missing_controls_block_design(self) -> None:
        result = ViabilityEngine().assess({
            "name": "unsafe idea",
            "clear_outcome": "short",
        })
        self.assertEqual("blocked", result.status)
        self.assertTrue(any(item["severity"] == "high" for item in result.preventive_findings))

    def test_conflict_applies_penalty_and_gate(self) -> None:
        design = {"name": "conflicted", "conflicts": ["Two systems own the same write"]}
        for key in (
            "clear_outcome", "evidence", "owner", "dependencies", "observability",
            "testability", "reversibility", "rollback", "cost_cap", "security_privacy",
        ):
            design[key] = f"Documented {key} with measurable controls"
        result = ViabilityEngine().assess(design)
        self.assertEqual(90, result.score)
        self.assertEqual("blocked", result.status)

    def test_name_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "name"):
            ViabilityEngine().assess({})


if __name__ == "__main__":
    unittest.main()
