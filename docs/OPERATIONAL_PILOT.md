# Jarvis operational pilot: October 20, 2026

This maintenance increment turns public GitHub inventory reporting into a bounded
live workflow and hardens the existing local runtimes. Its release decision is
recorded in PRs #14, #2 and #6. A successful review-branch audit is evidence for
that audit, not a deployment of the complete multi-provider swarm.

## Components and actual scope

| Component | Implemented behavior | Remaining activation boundary |
| --- | --- | --- |
| Synchronization check | Scans both control and workflow files, with redacted findings and regression checks. | Main promotion requires the exact PR merge approval. |
| Python workflow runner | Stops at approvals, missing external opt-in and failures; reports downstream steps not run. | No authenticated approval-to-resume endpoint is implemented. |
| Public GitHub audit | Reads public repository metadata and creates deterministic findings and proposals. | Does not inspect every repository's CI, code, deployments or revenue. |
| Audit MemPalace receipts | Hashes reports and preserves a local ledger, manifest and anchor in each run's artifact. | No shared memory service or restored cross-run history. |
| Node HTTP pilot | Authenticated repository-scoped planning, effective dry-run, bounded advisory calls. | Local-only; no hosted service, production identity, durable worker or aggregate spending budget. |
| Provider and Hostinger adapters | Existing code and explicit configuration points remain available. | Live account access and end-to-end provider exchanges are not established by these tests. |

## First live audit

The audit workflow runs on relevant pull-request changes. This allows a real
public metadata read to be tested before any main-branch merge. It also retains
the existing daily schedule at 15:17 UTC and adds relevant main-push events for
use after promotion. Pull-request runs record both the tested merge-checkout SHA
and the source head SHA. The merge-checkout may differ from the source head.

The workflow has `contents: read`, a 15-minute timeout and a cap of 250 repository
records. Explicit owner scope selects public API requests without a token; a
private or different-owner record fails the inventory. All AI provider invocation
is outside this audit.

Required outcomes are checkout, Python setup, installation, unit tests, workflow
validation, local doctor, patrol and improvement proposals. Explicit Bash makes
pipeline failures propagate through `tee`. Missing, failed or skipped steps and
inconsistent reports prevent `operational_success`.

The `jarvis-audit-<run-id>-<attempt>` artifact contains the test log, validation,
readiness, patrol and proposal reports, plus:

- `data/audit/manifest.json`: GitHub context, report hashes, step outcomes and scope.
- `data/audit/anchor.json`: retained manifest and ledger hashes.
- `data/audit/mempalace.sqlite3`: the local metadata receipt.

Artifacts are retained by this workflow for 30 days. Preserve a reviewed copy and
its anchor separately when long-term evidence is needed. Each fresh GitHub runner
starts without a restored prior journal; no cross-run learning or persistent
multi-provider memory is claimed.

After downloading and extracting a run's artifact, use the corresponding source
revision to verify it:

```sh
PYTHONPATH=/path/to/audited-checkout/src python3 -m jarvis.audit_evidence verify \
  --root /path/to/extracted-artifact --require-success
```

Also verify the GitHub run conclusion and exact commit context. Hashes detect
changes relative to the retained anchor. They do not certify authorship or remain
independent if an attacker can replace both artifacts and anchor.

## Local runtime and product review

See `runtime/README.md` for the local Node pilot. It defaults to loopback and
dry-run. Provider keys alone cannot enable calls. No service is started by merging
these files or importing the server module.

The Prompt #11 release is a separate product decision. Its independent human
accessibility scorecard is still required. Automated structural checks and an AI
code review cannot replace that human review. No checkout or product publication
is part of this repository maintenance.

## Integration order and recovery

1. PR #14: tested scanner repair.
2. PR #2: reconciled Control Tower and operational gates.
3. PR #6: Unified Fabric, bounded audit and hardened local pilot.

The review branches preserve the dependency ancestry. Default-branch merges
remain pending the owner's explicit approval of these exact pull requests. No
default-branch write should be substituted for the blocked merge operation.

Recovery is to stop the relevant workflow/local command and revert the approved
change if needed. Keep prior code, product artifacts and approval records intact.
No automatic deployment, account enrollment or paid provider activation is added.
