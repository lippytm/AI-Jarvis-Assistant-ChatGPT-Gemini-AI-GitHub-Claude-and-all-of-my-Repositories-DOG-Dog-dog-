from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


HIGH_STAKES = {"medical", "legal", "financial", "security", "physical_safety", "identity"}
IRREVERSIBLE = {"delete", "publish", "deploy", "merge", "spend", "message", "install"}


@dataclass(frozen=True)
class Problem:
    statement: str
    desired_outcome: str
    domain: str = "general"
    evidence: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    stakeholders: tuple[str, ...] = ()
    proposed_actions: tuple[str, ...] = ()
    success_metric: str = ""
    deadline: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Problem":
        statement = str(value.get("statement", "")).strip()
        outcome = str(value.get("desired_outcome", "")).strip()
        if not statement or not outcome:
            raise ValueError("statement and desired_outcome are required")
        def items(name: str) -> tuple[str, ...]:
            raw = value.get(name, [])
            if not isinstance(raw, list):
                raise ValueError(f"{name} must be a list")
            return tuple(str(item).strip() for item in raw if str(item).strip())
        return cls(
            statement=statement,
            desired_outcome=outcome,
            domain=str(value.get("domain", "general")).strip().lower(),
            evidence=items("evidence"),
            constraints=items("constraints"),
            stakeholders=items("stakeholders"),
            proposed_actions=items("proposed_actions"),
            success_metric=str(value.get("success_metric", "")).strip(),
            deadline=str(value.get("deadline", "")).strip(),
        )


class SolvabilityEngine:
    """Classify a problem and route it without pretending every problem is solvable."""

    def assess(self, problem: Problem) -> dict[str, Any]:
        blockers: list[str] = []
        questions: list[str] = []
        risk = "standard"
        if not problem.evidence:
            questions.append("What observable evidence establishes the current state?")
        if not problem.constraints:
            questions.append("What limits, dependencies, budget, and authority apply?")
        if not problem.stakeholders:
            questions.append("Who is affected and who owns the decision?")
        if not problem.success_metric:
            questions.append("What measurable result would count as success?")
        if problem.domain in HIGH_STAKES:
            risk = "high"
            blockers.append("Qualified human review is required for this high-stakes domain.")
        action_words = {word for action in problem.proposed_actions
                        for word in action.lower().replace("-", "_").split()}
        if action_words & IRREVERSIBLE:
            risk = "high"
            blockers.append("One or more proposed actions are irreversible or externally consequential.")
        status = "ready_for_analysis"
        if blockers:
            status = "restricted"
        elif len(questions) >= 3:
            status = "needs_definition"
        route = self._route(problem, risk, status)
        return {
            "problem_id": self._id(problem),
            "problem": asdict(problem),
            "status": status,
            "risk": risk,
            "known_unknowns": questions,
            "blockers": blockers,
            "recommended_route": route,
            "first_safe_step": self._first_step(status, route),
            "claim": "Assessment and routing only; not proof that the problem is solvable.",
        }

    @staticmethod
    def _route(problem: Problem, risk: str, status: str) -> str:
        if status == "needs_definition":
            return "clarification"
        if risk == "high":
            return "expert_review_then_problem_council"
        if problem.domain in {"software", "github", "linux", "security"}:
            return "diagnostics_then_sandbox"
        return "jarvis_problem_council"

    @staticmethod
    def _first_step(status: str, route: str) -> str:
        if status == "needs_definition":
            return "Answer the known-unknown questions before generating solutions."
        if route == "expert_review_then_problem_council":
            return "Identify an authorized qualified reviewer and collect minimum-necessary evidence."
        if route == "diagnostics_then_sandbox":
            return "Capture a reproducible baseline and run read-only diagnostics."
        return "Run a no-cost Problem Council plan before authorizing provider calls."

    @staticmethod
    def _id(problem: Problem) -> str:
        encoded = json.dumps(asdict(problem), sort_keys=True, separators=(",", ":")).encode()
        return "problem-" + hashlib.sha256(encoded).hexdigest()[:16]
