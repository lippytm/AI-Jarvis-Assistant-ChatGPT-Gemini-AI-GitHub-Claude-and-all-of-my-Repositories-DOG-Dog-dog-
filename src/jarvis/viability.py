from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


DIMENSIONS = (
    "clear_outcome", "evidence", "owner", "dependencies", "observability",
    "testability", "reversibility", "rollback", "cost_cap", "security_privacy",
)


@dataclass(frozen=True)
class ViabilityResult:
    design_id: str
    score: int
    status: str
    dimension_scores: dict[str, int]
    preventive_findings: list[dict[str, str]]
    unresolved_unknowns: list[str]
    release_gate: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "design_id": self.design_id,
            "score": self.score,
            "status": self.status,
            "dimension_scores": self.dimension_scores,
            "preventive_findings": self.preventive_findings,
            "unresolved_unknowns": self.unresolved_unknowns,
            "release_gate": self.release_gate,
            "claim": "Preventive assessment reduces foreseeable risk; it cannot prove future safety.",
        }


class ViabilityEngine:
    """Score preventive readiness from explicit design evidence."""

    def assess(self, design: dict[str, Any]) -> ViabilityResult:
        name = str(design.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        dimensions: dict[str, int] = {}
        findings: list[dict[str, str]] = []
        unknowns: list[str] = []
        for dimension in DIMENSIONS:
            value = design.get(dimension)
            score = self._score(value)
            dimensions[dimension] = score
            if score == 0:
                findings.append({
                    "dimension": dimension,
                    "severity": "high",
                    "finding": f"{dimension} is missing or unsupported.",
                    "prevention": self._prevention(dimension),
                })
            elif score == 1:
                findings.append({
                    "dimension": dimension,
                    "severity": "medium",
                    "finding": f"{dimension} is only partially defined.",
                    "prevention": self._prevention(dimension),
                })
        raw = round(sum(dimensions.values()) / (2 * len(DIMENSIONS)) * 100)
        conflicts = design.get("conflicts", [])
        if not isinstance(conflicts, list):
            raise ValueError("conflicts must be a list")
        for conflict in conflicts:
            findings.append({
                "dimension": "conflict",
                "severity": "high",
                "finding": str(conflict),
                "prevention": "Resolve ownership, priority, interface, or policy conflict before implementation.",
            })
        assumptions = design.get("assumptions", [])
        if not isinstance(assumptions, list):
            raise ValueError("assumptions must be a list")
        unknowns.extend(str(item) for item in assumptions if str(item).strip())
        conflict_penalty = min(30, 10 * len(conflicts))
        score = max(0, raw - conflict_penalty)
        if conflicts or any(item["severity"] == "high" for item in findings):
            status = "blocked"
            gate = "Do not implement; resolve high-severity preventive findings."
        elif score < 80:
            status = "revise"
            gate = "Revise the design and repeat the assessment."
        else:
            status = "sandbox_ready"
            gate = "Proceed only to an isolated, reversible experiment with monitoring."
        return ViabilityResult(
            self._id(design), score, status, dimensions, findings, unknowns, gate
        )

    @staticmethod
    def _score(value: Any) -> int:
        if value is True:
            return 2
        if value is False or value is None or value == "" or value == []:
            return 0
        if isinstance(value, str):
            return 2 if len(value.strip()) >= 20 else 1
        if isinstance(value, (list, dict)):
            return 2 if len(value) >= 2 else 1
        return 1

    @staticmethod
    def _prevention(dimension: str) -> str:
        actions = {
            "clear_outcome": "Define a measurable desired result and explicit non-goals.",
            "evidence": "Attach current-state evidence and identify its source and freshness.",
            "owner": "Assign one accountable owner and an approval authority.",
            "dependencies": "Inventory upstream and downstream systems, versions, and contracts.",
            "observability": "Define logs, metrics, alerts, provenance, and diagnostic access.",
            "testability": "Define deterministic tests and a baseline before changing anything.",
            "reversibility": "Use an isolated branch, feature flag, or disposable environment.",
            "rollback": "Write and verify restoration steps before implementation.",
            "cost_cap": "Set time, API, compute, and financial budgets with circuit breakers.",
            "security_privacy": "Classify data, minimize access, scan secrets, and threat-model abuse.",
        }
        return actions[dimension]

    @staticmethod
    def _id(design: dict[str, Any]) -> str:
        encoded = json.dumps(design, sort_keys=True, separators=(",", ":")).encode()
        return "design-" + hashlib.sha256(encoded).hexdigest()[:16]
