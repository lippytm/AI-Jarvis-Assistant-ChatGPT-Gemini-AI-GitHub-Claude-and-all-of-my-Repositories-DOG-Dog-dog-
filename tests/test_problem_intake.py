from __future__ import annotations

import unittest

from jarvis.problem_intake import Problem, SolvabilityEngine


class ProblemIntakeTests(unittest.TestCase):
    def test_underdefined_problem_requests_definition(self) -> None:
        assessment = SolvabilityEngine().assess(Problem.from_dict({
            "statement": "Fix everything",
            "desired_outcome": "Everything works",
        }))
        self.assertEqual("needs_definition", assessment["status"])
        self.assertEqual("clarification", assessment["recommended_route"])
        self.assertGreaterEqual(len(assessment["known_unknowns"]), 3)

    def test_technical_problem_routes_to_sandbox(self) -> None:
        assessment = SolvabilityEngine().assess(Problem.from_dict({
            "statement": "CI fails intermittently",
            "desired_outcome": "Reliable test runs",
            "domain": "software",
            "evidence": ["three failed run IDs"],
            "constraints": ["no production writes"],
            "stakeholders": ["repository owner"],
            "success_metric": "30 consecutive green runs",
        }))
        self.assertEqual("ready_for_analysis", assessment["status"])
        self.assertEqual("diagnostics_then_sandbox", assessment["recommended_route"])

    def test_high_stakes_problem_requires_expert(self) -> None:
        assessment = SolvabilityEngine().assess(Problem.from_dict({
            "statement": "Choose a medical treatment",
            "desired_outcome": "Improve health",
            "domain": "medical",
            "evidence": ["clinical records"],
            "constraints": ["patient consent"],
            "stakeholders": ["patient", "licensed clinician"],
            "success_metric": "clinician-defined outcome",
        }))
        self.assertEqual("restricted", assessment["status"])
        self.assertEqual("high", assessment["risk"])
        self.assertIn("expert_review", assessment["recommended_route"])

    def test_required_fields_are_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "required"):
            Problem.from_dict({"statement": "Missing outcome"})


if __name__ == "__main__":
    unittest.main()
