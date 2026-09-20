# Multi-agent orchestration

Hermes Fabric is the coordinator. It creates a task envelope, selects provider adapters, collects independent results, reconciles conflicts, runs GitHub validation, and records the outcome.

## Standard flow

`event -> intake -> context_load -> parallel_provider_analysis -> reconcile -> test -> approval_gate -> execute -> audit`

## Provider roles

- Gemini: broad context, research, and knowledge synthesis.
- ChatGPT Business/OpenAI: planning, structured drafts, and coding proposals.
- Claude: independent code review, risk analysis, and second opinion.
- GitHub: canonical state, code, issues, pull requests, tests, and audit record.
- Slack: notifications and approval requests only.
- Notion: optional readable mirror, never the canonical source.

## “Solve all problems” policy

Jarvis should classify each task before execution: code, operations, documentation, business process, affiliate marketing, financing workflow, security, or unknown. Unknown and high-impact tasks are routed to review instead of guessed at. No provider can bypass approval gates.
