# Quick Actions pilot

## Scope

Pilot mode is enabled only when `JARVIS_PILOT_REPOSITORY` is set. Requests for any other repository are rejected.

## Autonomous actions

Repository analysis, debugging, self-healing repair plans, self-improvement plans, change summaries, tests, versioned knowledge sync, issue drafts, and pull-request drafts may be planned autonomously. They remain auditable and do not bypass repository permissions.

## Approval-required actions

Slack messages, deployments, pull-request merges, deletions, secret changes, and other external or destructive operations require an approval record containing the repository, branch, action, affected resources, test result, rollback plan, and exact approval text.

## Expansion gate

Do not expand beyond the pilot until the runtime tests pass, provider outputs are reconciled, audit records are present, and rollback has been tested successfully.
