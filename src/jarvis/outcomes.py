from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


class OutcomeEvidence:
    """Rank prevention controls using transparent, conservative observed outcomes."""

    def evaluate(self, path: Path) -> dict[str, Any]:
        trials = self._load(path)
        grouped: dict[str, list[bool]] = defaultdict(list)
        for trial in trials:
            control_id = str(trial.get("control_id", "")).strip()
            outcome = trial.get("success")
            if not control_id or not isinstance(outcome, bool):
                raise ValueError("Each outcome requires control_id and boolean success")
            grouped[control_id].append(outcome)
        rankings = []
        for control_id, outcomes in grouped.items():
            successes = sum(outcomes)
            total = len(outcomes)
            rankings.append({
                "control_id": control_id,
                "trials": total,
                "successes": successes,
                "observed_rate": round(successes / total, 4),
                "wilson_lower_bound": round(self._wilson(successes, total), 4),
                "evidence_grade": self._grade(total),
            })
        rankings.sort(key=lambda item: (-item["wilson_lower_bound"], -item["trials"], item["control_id"]))
        return {
            "method": "Wilson 95% lower confidence bound",
            "trial_count": len(trials),
            "rankings": rankings,
            "limitations": [
                "Association is not proof of causation.",
                "Results may not transfer across systems or contexts.",
                "Small samples remain low-grade evidence even when all trials succeed.",
                "Failed and negative outcomes must be retained to avoid survivorship bias.",
            ],
        }

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        records = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Outcome line {line_number} must be an object")
            records.append(value)
        if not records:
            raise ValueError("At least one outcome record is required")
        return records

    @staticmethod
    def _wilson(successes: int, total: int, z: float = 1.96) -> float:
        proportion = successes / total
        denominator = 1 + z * z / total
        centre = proportion + z * z / (2 * total)
        margin = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total)
        return max(0.0, (centre - margin) / denominator)

    @staticmethod
    def _grade(total: int) -> str:
        if total >= 30:
            return "moderate"
        if total >= 10:
            return "limited"
        return "preliminary"
