# Jarvis operating procedure

## Before every live workflow

1. Run `jarvis validate-workflows --json`.
2. Run `jarvis plan WORKFLOW "INPUT" --json`.
3. Confirm every required provider reports `configured: true`.
4. Confirm the external-call count is within budget.
5. Remove credentials, private keys, customer records, medical data, and unnecessary personal data.
6. Run without `--allow-external` first to verify handoff structure.
7. Only then run with `--allow-external`.

## Approval rule

An approval record documents the owner's decision; it never executes the action itself.
Publishing, sending messages, spending, merging, deploying, changing credentials, and deleting
remain separate operations requiring a clear target and fresh authorization.

## Recovery

- Reuse the idempotent report after an interrupted client session.
- Use `--force` only when a fresh paid run is intentional.
- If a provider fails, inspect its task event in the ledger before retrying.
- Revoke any credential that appears in a prompt, terminal output, issue, commit, or report.
- Preserve the run ID and content hashes when moving work between systems.

## Production readiness checklist

- Managed secret storage and key rotation
- Encrypted database and backups
- Role-based access and multi-factor authentication
- Provider spend limits and alerts
- Data-retention and deletion policy
- Incident response contacts and recovery drill
- Legal/privacy review for customer information
- Staging environment before production deployment
