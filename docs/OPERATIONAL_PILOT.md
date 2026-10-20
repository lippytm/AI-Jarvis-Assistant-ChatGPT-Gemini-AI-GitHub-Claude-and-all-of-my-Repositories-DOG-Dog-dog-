# Jarvis operational pilot: October 20, 2026

This maintenance increment turns public GitHub inventory reporting into a bounded
live workflow and hardens the existing local runtimes. The owner approved
promotion on October 20, 2026, and PRs #14, #2 and #6 were merged into `main` in
that order. The verified audit demonstrates public metadata reporting; it does
not demonstrate deployment of the complete multi-provider swarm.

## Components and actual scope

| Component | Implemented behavior | Remaining activation boundary |
| --- | --- | --- |
| Synchronization check | Scans both control and workflow files, with redacted findings and regression checks; promoted to main in PR #14. | Future changes continue through reviewed pull requests. |
| Python workflow runner | Stops at approvals, missing external opt-in and failures; reports downstream steps not run. | No authenticated approval-to-resume endpoint is implemented. |
| Public GitHub audit | Reads public repository metadata and creates deterministic findings and proposals. | Does not inspect every repository's CI, code, deployments or revenue. |
| Audit MemPalace receipts | Hashes reports and preserves a local ledger, manifest and anchor in each run's artifact. | No shared memory service or restored cross-run history. |
| Node HTTP pilot | Authenticated repository-scoped planning, effective dry-run, bounded advisory calls. | Local-only; no hosted service, production identity, durable worker or aggregate spending budget. |
| Shared Prompt #11 profile | All eight Python workflows and the Node planner resolve the same versioned guidance and record its hash. | Coverage proves the instruction source, not provider compliance or remote synchronization. |
| Optional business context | Projects allowed owner facts once per local invocation; every executed Python AI step receives the same task data. | Private tax and administration fields are excluded; no automatic cloud-agent memory sync. |
| Provider adapters | Require explicit models, bound responses and reject failed, refused, truncated or empty output before downstream work. | Live account access and end-to-end provider exchanges are not established by offline tests. |
| Hostinger adapter | GET-only bounded inventory verifies pagination and duplicate records before a metadata-only receipt. | No account connection verified; completion is not a transactional snapshot or deployment. |
| Funding-route review | Preserves four exact latest routes, earlier conflicting evidence and unresolved review checks. | Destination, attribution, terms and publication remain unverified. |
| Creative studio packet | Four-format local template packet, six distribution briefs, three AI-workspace briefs, hashed files and an approval stop. | Intake is required; no finished media, account connection or publication. |

## Verified audit and triggers

The audit workflow runs on relevant pull-request changes, relevant main pushes,
and the existing daily schedule at 15:17 UTC. Pull-request runs record both the
tested merge-checkout SHA and the source head SHA. The merge-checkout may differ
from the source head.

The first verified review-branch run was `39467647402`, at source head
`abd73db645492803f5f3fcffb9d2a1313b78736c`. Its downloaded evidence verified with
`integrity_valid: true` and `operational_success: true`. After promotion, main run
`39470533073` completed successfully at commit
`940e1f4b08061c7caeb8900e8590f69376360771`. Its checkout has the same source tree
as the reviewed revision. Later runs must be checked against their own commits.

The subsequent shared-profile, business-context and Hostinger repair in PR #19
was merged as `e30e7b769a0c5eec6e31f44d956419880e02cd13`. All five main workflows
passed at that commit. Audit run `39476724554` recorded 210 passing tests, seven
covered workflows, 40 public repository records, and successful internal hash and
receipt verification. Artifact `12288229398` could not be downloaded for an
independent local check: an initial timeout and one transport-connectivity failure
returned no usable ZIP. Its contents and ZIP digest were not independently
verified outside Actions. The PR records the exact source tree and evidence links.

The creative-studio extension adds the eighth catalog workflow after that
seven-workflow audit. Its own reviewed revision and checks are recorded in the
studio follow-up pull request; the earlier audit is not evidence for later code.

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

## Promotion record and recovery

1. PR #14: scanner repair, merged as `87ab0df8d20a6c2d3449902dfb870f6357868899`.
2. PR #2: Control Tower and operational gates, merged as
   `5c2eede966d4663bf9f1433516cc7d4bfe608ff3`.
3. PR #6: retargeted from the Control Tower branch to main, then merged as
   `940e1f4b08061c7caeb8900e8590f69376360771`.
4. PR #19: shared Prompt #11, business context, Hostinger/referral integration and
   the Python 3.13 SQLite cleanup repair, merged as
   `e30e7b769a0c5eec6e31f44d956419880e02cd13`.

The review branches preserve the dependency ancestry. The earlier automatic
review block was resolved by the owner's subsequent approval; the three merges
used the exact reviewed source heads. No direct default-branch write substituted
for a merge.

The first main runs also exposed a separate repository-scope check that looked
for `approval_required` in the provider contract instead of the repository
policy. The follow-up correction validates the existing declaration in
`.jarvis/repositories.yaml`, requires the approval policy file, and runs the
scope check on relevant pull requests. A successful audit alone is not a claim
that every other CI job succeeded.

The subsequent shared Prompt #11 integration and its catalog coverage are
documented in `PROMPT11_WORKFLOW_PROFILE.md`. Its repository operating-profile
version is distinct from the underlying source documents' inconsistent labels.
The optional owner-context projection and proposed Hostinger mappings are
documented in `BUSINESS_CONTEXT.md` and `PROPOSED_HOSTINGER_WORKFLOW_MAPPINGS.md`.
The follow-up pull request records its exact source revision, CI outcomes and
independent audit verification once those checks finish.

Recovery is to stop the relevant workflow/local command and revert the approved
change if needed. Keep prior code, product artifacts and approval records intact.
No automatic deployment, account enrollment or paid provider activation is added.
