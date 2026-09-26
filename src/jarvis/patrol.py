from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .github_inventory import list_repositories


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Finding:
    repository: str
    code: str
    severity: str
    summary: str
    safe_action: str
    requires_approval: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PatrolPolicy:
    max_repositories: int = 250
    stale_days: int = 120
    allow_repository_writes: bool = False
    allow_merges: bool = False
    allow_deployments: bool = False
    allow_external_messages: bool = False
    allow_spending: bool = False

    @classmethod
    def from_env(cls) -> "PatrolPolicy":
        max_repositories = int(os.getenv("JARVIS_PATROL_MAX_REPOSITORIES", "250"))
        stale_days = int(os.getenv("JARVIS_PATROL_STALE_DAYS", "120"))
        if not 1 <= max_repositories <= 1000:
            raise ValueError("JARVIS_PATROL_MAX_REPOSITORIES must be between 1 and 1000")
        if not 1 <= stale_days <= 3650:
            raise ValueError("JARVIS_PATROL_STALE_DAYS must be between 1 and 3650")
        return cls(max_repositories=max_repositories, stale_days=stale_days)


class Patrol:
    """A bounded, read-only repository patrol that produces reviewable proposals."""

    def __init__(
        self,
        policy: PatrolPolicy | None = None,
        inventory: Callable[..., list[dict[str, Any]]] = list_repositories,
        output_dir: Path | None = None,
    ):
        self.policy = policy or PatrolPolicy.from_env()
        self.inventory = inventory
        self.output_dir = output_dir or Path(os.getenv("JARVIS_PATROL_OUTPUT", "data/patrol"))

    def run(self, owner: str | None = None) -> dict[str, Any]:
        repositories = self.inventory(owner=owner)
        if len(repositories) > self.policy.max_repositories:
            raise RuntimeError(
                f"Circuit breaker: {len(repositories)} repositories exceeds "
                f"limit {self.policy.max_repositories}"
            )
        findings: list[Finding] = []
        for repository in repositories:
            findings.extend(self._inspect(repository))
        report = {
            "schema_version": "1.0",
            "run_id": self._run_id(repositories),
            "created_at": utc_now(),
            "mode": "read_only",
            "policy": asdict(self.policy),
            "repositories_scanned": len(repositories),
            "findings": [finding.as_dict() for finding in findings],
            "summary": self._summary(findings),
            "next_step": "Review proposals; approve a dedicated branch and draft PR per repository.",
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "latest.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
        report["report_path"] = str(path)
        return report

    def _inspect(self, repository: dict[str, Any]) -> list[Finding]:
        name = str(repository.get("full_name") or "unknown")
        findings: list[Finding] = []
        if not repository.get("default_branch"):
            findings.append(Finding(
                name, "missing-default-branch", "high",
                "Repository metadata has no default branch.",
                "Inspect repository initialization and branch protection.",
            ))
        updated_at = repository.get("updated_at")
        age = self._age_days(updated_at)
        if age is not None and age >= self.policy.stale_days:
            findings.append(Finding(
                name, "stale-repository", "low",
                f"No repository update recorded for {age} days.",
                "Classify as active, incubating, archived, or consolidation candidate.",
            ))
        if repository.get("private"):
            findings.append(Finding(
                name, "private-data-boundary", "info",
                "Repository is private and requires minimum-necessary access.",
                "Keep reports redacted and do not export private code to unapproved providers.",
            ))
        return findings

    @staticmethod
    def _age_days(value: Any) -> int | None:
        if not isinstance(value, str):
            return None
        try:
            then = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return max(0, (datetime.now(timezone.utc) - then).days)

    @staticmethod
    def _summary(findings: list[Finding]) -> dict[str, int]:
        counts = {"total": len(findings), "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    @staticmethod
    def _run_id(repositories: list[dict[str, Any]]) -> str:
        payload = json.dumps(repositories, sort_keys=True, separators=(",", ":")).encode()
        return "patrol-" + hashlib.sha256(payload).hexdigest()[:16]
