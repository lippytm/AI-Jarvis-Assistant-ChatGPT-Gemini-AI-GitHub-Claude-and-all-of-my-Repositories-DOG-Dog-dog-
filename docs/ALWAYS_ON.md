# Always-On Jarvis Operations

Jarvis can run continuously as a bounded patrol after this branch is reviewed and merged into
the default branch. GitHub Actions supplies the initial hosted scheduler; a later Hostinger,
Zo Computer, or Linux service may run the same command.

## Continuous loop

1. Inventory repositories using read-only GitHub access.
2. Apply deterministic health rules.
3. Write a machine-readable report with provenance.
4. Preserve the report as a workflow artifact.
5. Present proposed actions for owner review.
6. Use one dedicated branch and draft pull request for any approved repair.
7. Test, review, and merge only after explicit approval.

The patrol does not call paid AI providers. It does not edit repositories, open issues,
merge pull requests, deploy, publish, message people, spend money, or handle secrets.

## Run locally

```bash
jarvis patrol --owner lippytm --json
```

Reports are written atomically to `data/patrol/latest.json`. Set
`JARVIS_PATROL_MAX_REPOSITORIES` and `JARVIS_PATROL_STALE_DAYS` to tune the bounded scan.

## Growth and self-healing model

"Self-improvement" means: observe results, record a measurable proposal, test it in isolation,
compare it with the current baseline, and request approval through a draft pull request.
"Self-healing" means: retry safe reads, detect drift, restore generated reports, and propose
a tested repair. It never means silently modifying production systems.

Promotion stages are observe → recommend → draft repair → sandbox test → owner approval →
merge/deploy. A failure, unexpected repository count, missing permission, detected secret,
budget limit, or policy violation stops the loop.

## Activation

Scheduled GitHub workflows run from the repository's default branch. Therefore the daily
patrol becomes active only after PR #2 is conflict-free, its checks pass, and Charles chooses
to merge it. No API keys are required for public inventory. Private repository inventory
requires a minimum-scope GitHub token supplied through GitHub Actions secrets.
