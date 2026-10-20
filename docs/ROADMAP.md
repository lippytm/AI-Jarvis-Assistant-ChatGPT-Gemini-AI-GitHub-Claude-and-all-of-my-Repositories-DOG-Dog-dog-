# Jarvis build roadmap

## v0.1 — Control Tower foundation

- Provider-neutral task contract
- OpenAI, Claude, Gemini, and mock adapters
- SQLite provenance ledger, CLI, health checks, tests, connector permission contract

## v0.2 — GitHub and business workflow pilot

- GitHub read connector and approval-gated issue/PR drafting
- Repository registry for the lippytm portfolio
- Prompt #11 task templates and round-trip provenance export/import
- Idempotency keys and retry policy
- Automated JSON workflow runner and multi-AI review pipeline (foundation delivered)

## v0.3 — Hostinger and communications

- Hostinger deployment status connector, Slack notification drafts
- Webhook inbox with signature verification, human approval queue
- Redaction rules and configurable retention

## v1.0 — Operated service

- Authenticated dashboard, encrypted database, managed secrets and role-based access
- Cost budgets, observability, backups, incident runbooks and external security review

Every integration needs a health check, least-privilege credentials, tests, an audit event, timeout/retry behavior, failure recovery documentation, and a human-approval boundary.
