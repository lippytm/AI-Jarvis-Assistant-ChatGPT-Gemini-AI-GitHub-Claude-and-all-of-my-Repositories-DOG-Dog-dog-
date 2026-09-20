from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class LoopPolicy:
    max_observations: int = 500
    max_proposals: int = 50
    minimum_repeat_count: int = 2
    allow_code_changes: bool = False
    allow_production_actions: bool = False
    allow_secret_access: bool = False
    allow_model_retraining: bool = False

    @classmethod
    def from_env(cls) -> "LoopPolicy":
        observations = int(os.getenv("JARVIS_LOOP_MAX_OBSERVATIONS", "500"))
        proposals = int(os.getenv("JARVIS_LOOP_MAX_PROPOSALS", "50"))
        repeats = int(os.getenv("JARVIS_LOOP_MINIMUM_REPEATS", "2"))
        if not 1 <= observations <= 5000:
            raise ValueError("JARVIS_LOOP_MAX_OBSERVATIONS must be between 1 and 5000")
        if not 1 <= proposals <= 500:
            raise ValueError("JARVIS_LOOP_MAX_PROPOSALS must be between 1 and 500")
        if not 1 <= repeats <= 100:
            raise ValueError("JARVIS_LOOP_MINIMUM_REPEATS must be between 1 and 100")
        return cls(observations, proposals, repeats)


class ImprovementLoop:
    """Deterministic learning from evidence; produces proposals, never production changes."""

    def __init__(self, policy: LoopPolicy | None = None, output_dir: Path | None = None):
        self.policy = policy or LoopPolicy.from_env()
        self.output_dir = output_dir or Path(os.getenv("JARVIS_LOOP_OUTPUT", "data/improvement"))

    def run(self, source: Path) -> dict[str, Any]:
        payload = json.loads(source.read_text(encoding="utf-8"))
        observations = self._observations(payload)
        if len(observations) > self.policy.max_observations:
            raise RuntimeError("Circuit breaker: observation limit exceeded")
        grouped = self._group(observations)
        proposals = self._proposals(grouped)
        report = {
            "schema_version": "1.0",
            "cycle_id": self._cycle_id(payload),
            "created_at": utc_now(),
            "mode": "proposal_only",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "policy": asdict(self.policy),
            "observation_count": len(observations),
            "patterns": grouped,
            "proposals": proposals,
            "learning_contract": {
                "method": "evidence-derived pattern counting",
                "production_mutation": False,
                "model_weights_changed": False,
                "human_approval_required": True,
            },
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        destination = self.output_dir / "latest.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(destination)
        self._append_journal(report)
        report["report_path"] = str(destination)
        return report

    @staticmethod
    def _observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = payload.get("findings", payload.get("observations", []))
        if not isinstance(candidates, list):
            raise ValueError("Input must contain a findings or observations list")
        return [item for item in candidates if isinstance(item, dict)]

    @staticmethod
    def _group(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, dict[str, Any]] = {}
        for item in observations:
            code = str(item.get("code") or item.get("kind") or "unclassified")
            entry = counts.setdefault(code, {"code": code, "count": 0, "severities": {}})
            entry["count"] += 1
            severity = str(item.get("severity") or "unknown")
            entry["severities"][severity] = entry["severities"].get(severity, 0) + 1
        return sorted(counts.values(), key=lambda item: (-item["count"], item["code"]))

    def _proposals(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        proposals = []
        for pattern in patterns:
            if pattern["count"] < self.policy.minimum_repeat_count:
                continue
            proposals.append({
                "proposal_id": "proposal-" + hashlib.sha256(
                    pattern["code"].encode()
                ).hexdigest()[:12],
                "pattern": pattern["code"],
                "evidence_count": pattern["count"],
                "hypothesis": f"A shared diagnostic or template may reduce {pattern['code']} recurrence.",
                "experiment": "Test one reversible change in an isolated branch against the current baseline.",
                "success_metric": "Fewer matching findings with no regression in the full test suite.",
                "rollback": "Discard the experiment branch and preserve the failed result in the journal.",
                "status": "awaiting_owner_review",
                "automatic_execution": False,
            })
            if len(proposals) >= self.policy.max_proposals:
                break
        return proposals

    def _append_journal(self, report: dict[str, Any]) -> None:
        journal = self.output_dir / "journal.jsonl"
        record = {
            "cycle_id": report["cycle_id"],
            "created_at": report["created_at"],
            "source_sha256": report["source_sha256"],
            "observation_count": report["observation_count"],
            "proposal_count": len(report["proposals"]),
        }
        with journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    @staticmethod
    def _cycle_id(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "cycle-" + hashlib.sha256(encoded).hexdigest()[:16]
