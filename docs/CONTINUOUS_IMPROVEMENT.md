# Continuous Learning, Diagnostics, and Self-Healing

Jarvis uses a transparent improvement loop across repositories, publishing systems, business
operations, education, CRM, websites, and future life-support workflows.

## Loop contract

1. **Observe** — collect bounded, minimum-necessary health evidence.
2. **Diagnose** — classify symptoms without claiming an unverified root cause.
3. **Pattern** — count repeated evidence and preserve source hashes.
4. **Hypothesize** — state one falsifiable improvement proposal.
5. **Sandbox** — test a reversible change on an isolated branch or test environment.
6. **Compare** — measure against the recorded baseline and run regression tests.
7. **Document** — save results, failures, uncertainty, and rollback instructions.
8. **Approve** — require Charles or an authorized reviewer for production changes.
9. **Monitor** — check whether the approved change actually improved outcomes.
10. **Learn** — retain evidence in the journal; do not rewrite history.

## What continuous learning means

The current engine learns operational patterns from evidence and creates proposals. It does
not change model weights, secretly copy private conversations, or treat AI output as fact.
A recurring observation must meet the configured repeat threshold before it becomes a
proposal. One-off events remain visible but do not trigger an experiment automatically.

## Self-healing levels

| Level | Allowed automatically | Approval required |
|---|---|---|
| 0 Observe | Health checks, hashes, logs, reports | No |
| 1 Recover | Retry safe reads; recreate disposable reports | No |
| 2 Recommend | Diagnosis, repair plan, rollback plan | No |
| 3 Sandbox | Tests on an isolated branch with no production secrets | Policy-dependent |
| 4 Change | Repository edits, issues, pull requests | Yes |
| 5 Production | Merge, deploy, publish, message, spend, delete | Always |

## Transparency record

Every cycle records its input checksum, observation count, detected patterns, proposals,
policy, timestamp, and whether production or model weights changed. The append-only journal
records both useful and failed cycles. Failed experiments are evidence, not material to hide.

## Ecosystem application

Each system adapter should publish the same observation fields: system, component, code,
severity, evidence reference, timestamp, confidence, sensitivity class, and safe action.
Domain-specific diagnostics may then cover GitHub, Hostinger websites, Prompt #11 factories,
CRM, publishing, education, finance, security, and Linux environments without granting one
agent unlimited access to all of them.

Health or medical, legal, financial, security, identity, and physical-safety workflows must
remain advisory and require qualified human review. Life/business improvement never justifies
credential collection, surveillance, impersonation, or irreversible autonomous action.
