# Prompt #11 workflow operating profile

The repository now has one explicitly versioned operating profile shared by all
seven Python workflow definitions. It supplies actual system guidance to each
AI step that executes, and records the resolved profile in plans, run reports
and catalog validation. It does not activate providers or confer authority to
publish, merge, deploy, spend, or send messages.

## Identity and source provenance

| Field | Value |
|---|---|
| Profile file | `config/prompt-11-profile.json` |
| Identity | `P-011-E6C-001` |
| Repository revision | `repository-1` |
| Schema | `jarvis.prompt-profile.v1` |
| Kind | `repository_operating_profile` |
| Content identity | SHA-256 of the exact profile file bytes |

This is a **new repository operating profile**, not a recovered verbatim master
prompt or a claim to have implemented the complete Prompt #11 architecture.
Its source baseline is **P-011-E6C-001 Canonical Architecture, August 22, 2026**
(`P011-E6C-001-canonical-architecture.md`), supplemented by
**Bot Swarms Systems Master Upgrade, September 16, 2026, persistent version 3**
(`Bot_Swarms_Systems_Master_Upgrade_v1.0.md`). The operating specification's
filename says v1.0, its opening heading says v1.1, and later release text says
v1.2. That provenance discrepancy is retained; `repository-1` is this
repository's own revision and does not resolve those source labels.

The profile references the existing repository operating contract, approval
policy, provider contracts and knowledge schema. Those references document the
basis for review. The loader does not fetch them, the source documents, remote
instructions, or private conversation history and execute them as prompts.

## Catalog and execution behavior

Every `workflows/*.json` entry must declare the known ID and revision:

```json
"prompt_profile": {"id": "P-011-E6C-001", "revision": "repository-1"}
```

The current catalog contains `affiliate_site_review`, `jarvis_problem_council`,
`life_business_daily_briefing`, `multi_ai_business_review`,
`prompt_11_product_factory`, `repository_fleet_review` and
`unified_life_business_creation`. Validation discovers all JSON entries; adding
a workflow without the reference makes coverage incomplete and exits nonzero.
No shipping workflow is silently exempted. Invalid filenames, malformed
definitions, unknown IDs or revisions, and unavailable or invalid profile files
also prevent successful validation.

The fixed loader reads `config/prompt-11-profile.json` relative to the workflow
directory's project root. Workflow references cannot choose another path or
URL. It validates the schema, identity, revision, kind and all eight ordered
guidance sections, rejects duplicate profile JSON fields, and pins the exact
loaded bytes for the invocation. Introducing another revision requires an
explicit loader and workflow-reference update through normal code review.

For an AI step, the runner prepends the profile's shared guidance and a fixed
no-new-authority statement to the existing role-specific system instruction.
User input and preceding model output stay in the task prompt. Existing step
order, provider selection, approval positions and handoff destinations are
preserved. Non-AI steps receive profile metadata in the run report; their
handoff contents and execution behavior are unchanged.

Plans and results include `prompt_profile: {id, revision, sha256}` and
`profile_status: "resolved"`. **Resolved means the profile was validated and
attached to this invocation.** A plan executes nothing, and a blocked or
approval-pending run may not have called any AI provider. Consult the result's
status, steps and `not_run_steps` to establish what actually happened.

The Python cache identity includes the workflow hash, profile metadata, input,
external-call opt-in and sensitive-input opt-in. Changing profile bytes creates
a new identity even if its ID, revision and workflow JSON remain unchanged.
Changing an established operating contract should also receive a reviewed
revision update. Only completed or approval-pending runs are reusable; force
execution remains an explicit caller choice.

## Shared Node task planner

`runtime/src/prompt-profile.mjs` consumes the same fixed repository file and the
same ID, revision and exact-byte hash. It resolves the path from the module,
independently of the caller's working directory or request input. The Node task
planner includes the same profile metadata and `resolved` status in its plans
and results. Dry-run and approval-required plans still make no advisory calls.
When an authorized advisory step runs, the shared guidance and existing role
are supplied through the provider's system-instruction field. A missing or
invalid profile prevents task planning rather than falling back to an
unprofiled run.

The Python and Node system-text builders produce identical text for the same
profile and role. Node retains its existing authentication, repository/action
scope, external-call opt-in and approval boundaries. It does not execute the
Python JSON catalog, so its integration is verified separately from the seven
catalog entries. See [the runtime documentation](../runtime/README.md) for the
local task endpoint and its remaining deployment/provider limits.

## Guidance and enforced controls

The eight sections request objective and done criteria; scoped tools, data and
budgets; approvals; provenance and evidence; independent QA; idempotent
handoffs; stop and rollback planning; and scoped memory. Their delivery as
system guidance is tested. Model compliance is not mechanically certified.

| Requirement | Current runtime behavior and limit |
|---|---|
| Objective, owner and done criteria | Guidance asks for them and marks missing information. The runner does not require a structured task envelope with all of these fields. |
| Tools, data and budgets | Python preserves explicit external-call opt-in, configured call-count and provider-timeout limits, and its existing sensitive-input checks. The public fleet inventory remains scoped to lippytm's public metadata. The profile grants no additional tools or data. It is not a general authorization or resource-accounting engine. |
| Approvals | A workflow approval step records the request and stops downstream steps. An approval record does not automatically resume execution. The profile neither inserts approval stages into draft-only workflows nor grants approvals. |
| Provenance and evidence | Plans/results identify workflow and profile hashes; successful AI steps retain task/provider/model/content references. Catalog validation is included in the audit's hashed evidence artifact. Evidence supports its recorded scope, not an untested deployment claim. |
| Independent QA | Existing reviewer roles are preserved. Guidance requires unresolved QA and human review to remain visible, and independently produced and checked provider-specific editions before comparing or merging such editions. It does not initiate additional calls or certify that existing sequential workflows meet that production requirement. A successful workflow or mock test does not certify independent human QA, accessibility acceptance, or release readiness. |
| Handoffs and retries | Python handoffs remain local draft files. Its local run cache avoids repeating identical completed or approval-pending runs unless forced. This is not a distributed delivery, retry or cancellation protocol. |
| Stop and rollback | The runner stops on approvals, skipped external steps and failures, and records downstream steps not run. Rollback and escalation are requested as guidance; no automatic rollback service is introduced. |
| Scoped memory | Guidance calls for explicit scope, provenance and reviewed learning. Existing local ledgers and per-audit-run MemPalace receipts remain local evidence. No shared persistent MemPalace service, restored cross-run history, retention engine, or cross-provider learning is activated. |

## Verifying coverage and evidence

From the corresponding repository checkout, these commands make no provider
requests:

```bash
PYTHONPATH=src python3 -m jarvis validate-workflows --json
PYTHONPATH=src python3 -m jarvis plan prompt_11_product_factory "Profile verification only" --json
sha256sum config/prompt-11-profile.json
```

`validate-workflows` retains its existing `valid` and `workflows` fields and adds
`prompt_profile_coverage`. Complete coverage requires a nonempty valid catalog.
The coverage object records discovered and covered counts, uncovered filenames,
each covered workflow's normalized JSON hash and profile metadata, and a
`catalog_sha256` over that per-workflow mapping. Workflow and catalog hashes use
UTF-8 encoding of Python `json.dumps(value, sort_keys=True,
separators=(",", ":"))`, including its default ASCII escaping. The profile hash
uses the original file bytes, with no JSON reserialization.

The GitHub audit already archives and hashes the complete
`workflow-validation.json`. Its validation step must succeed, so a missing or
invalid profile prevents an operationally successful audit. The new coverage
object travels inside that existing artifact; no separate receipt system or
artifact path is introduced. Follow [the operational pilot verification
procedure](OPERATIONAL_PILOT.md) to check its manifest and per-run receipt.

To compare retained coverage with source, use the checkout identified by the
verified audit, rerun the command above, and compare its
`prompt_profile_coverage` object with the retained validation report. The profile
and workflow hashes must match the checkout's content. A colocated hash anchor
detects content changes; it is not an independent signature of authorship.

The coverage result attests the central Python JSON catalog. It does not attest
every GitHub repository, arbitrary CLI calls such as `ask`, external automation,
or activity inside ChatGPT, Gemini, Claude or Hostinger workspaces. External
operation still requires separate successful, scoped live evidence.

## Ad hoc compatibility and local tests

Standalone structural `validate_definition` calls remain useful for isolated
fixtures. They allow an absent profile but reject a present unknown reference.
For programmatic ad hoc `load`, `plan` or `run` calls, callers may explicitly
construct `WorkflowRunner(..., allow_unprofiled=True)`. Only an absent reference
is allowed by that option. Such plans/results contain `prompt_profile: null`
and `profile_status: "unprofiled_ad_hoc"`; they make no Prompt #11 coverage claim.

`validate_catalog` and `validate_all` always require profiles, even on that
runner. CLI `plan`, `run`, `validate-workflows` and Doctor enforce the profile
requirement; there is no CLI or environment opt-out. Existing isolated workflow tests opt out
explicitly, while CLI and Doctor fixtures carry the reviewed profile.

Run the focused profile and gate tests with:

```bash
PYTHONPATH=src python3 -m unittest tests.test_prompt_profiles tests.test_workflows tests.test_operational_gates tests.test_doctor -v
```

The profile tests use local mock providers. They check guidance delivery to
every executed AI step, role preservation, hashes, cache invalidation, complete
catalog coverage, strict unknown-reference handling, explicit ad hoc status,
and unchanged approval, external-call, input and budget gates. Passing them
does not verify a paid provider connection or authorize one.
