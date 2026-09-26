# Jarvis Problem Council

The Problem Council is a multi-model deliberation workflow for difficult business, technical,
creative, and operational problems. It is designed to outperform a single answer through
independence and structured disagreement, not by claiming omniscience.

The council uses evidence research, scenario modeling, adversarial review, solution synthesis,
a blind-spot challenge, and a verification gate. It ends at an owner-approval record and a
draft handoff. No proposal is executed automatically.

## Quality rules

- Preserve disagreements instead of averaging them away.
- Separate facts, assumptions, forecasts, and preferences.
- Include best, expected, worst, adversarial, and unknown-unknown probes.
- Prefer portfolios of reversible experiments to one irreversible bet.
- Define success metrics, time limits, stop conditions, and rollback before execution.
- Escalate when evidence is missing, consequences are high, or the system lacks authority.
- Never interpret confidence or model agreement as proof.

Run `jarvis plan jarvis_problem_council "PROBLEM" --json` first. Live execution requires
configured providers, explicit `--allow-external`, and a six-call budget. Provider outputs
may be wrong and remain advisory until evidence and real-world tests support them.
