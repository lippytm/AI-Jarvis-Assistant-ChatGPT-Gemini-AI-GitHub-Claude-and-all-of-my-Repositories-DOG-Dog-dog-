# Jarvis cross-platform referral integration

Version: 0.1.0 | October 14, 2026
Status: review-branch implementation, locally tested; not a deployed autonomous service.
Project owner and final release authority: Charles Earl Lipshay.

## Preserved foundation

Continue the existing `jarvis/unified-ai-fabric-v0.1` branch and PR #6, stacked on
Control Tower PR #2. Do not replace the user's work or merge unrelated branches.
The inspected source revision before this addition was
`9d9860386bed8a177c0cc07fd4cf1e0060df44f0`.

GitHub contains the public-safe code and review evidence. Private project content,
customer records, provider credentials and detailed financial records stay outside
public repositories. No permission expansion, account login or public website
publication is implied by this document.

## Three separate referral channels

| Registry ID | Intended routing | Original owner-supplied URL |
|---|---|---|
| `7figures-customer` | Customer referral, not partner recruitment | `http://www.7figurescredit.com?a_aid=lippytm` |
| `7figures-partner` | Referral-partner recruitment | `http://join.7figurespartners.com/?a_aid=lippytm` |
| `lendtrack-partner` | Separate referral-partner program | `http://lendtrack.ai/join/lippytmai` |

The two query identifiers are `lippytm`; the LendTrack path is `lippytmai`.
Keep those different identifiers intact. Do not silently normalize them.
These programs are distinct from any Hostinger product-affiliate account.
Hostinger may be a website delivery platform, not evidence of account membership
in these referral programs.

Public HTTP and HTTPS retrieval attempts returned tool errors on October 14.
That means this session could not inspect the destinations; it is not evidence
that the sites are down or that tracking is broken. The registry preserves the
original HTTP URLs and separately records HTTPS candidates. None is a newly
verified or approved publication URL.

Each program has six outstanding checks: HTTPS destination, account membership,
referral attribution, program terms, public copy and owner release scope.
Commission rates, payout status and account ownership were not independently
verified. A successful page load would not, by itself, prove referral credit.

## Implemented now

`src/jarvis/referral_review.py` is a standard-library offline tool that validates
this exact three-program pilot and generates a review packet. It rejects changed
referral identifiers, substituted destinations, duplicate/missing channels,
unexpected fields, invented commissions, duplicate JSON keys and oversized input.
Network, automatic publication and spending must remain disabled.

A JSON gate marked `verified` is treated only as an assertion. Even if every gate
is marked verified, this tool never grants publication or spending authority.
There is no network request, provider API call, loan application, payment or
publishing function in the new module.

Optional MemPalace integration records a local run ID, action, result status,
tool version and input/output SHA-256 hashes. It does not copy raw referral URLs,
application data or private prompts into the evidence event. The review packet
itself does contain the public referral URLs.

MemPalace hash checks establish local consistency, not provider authenticity,
factual truth, signed external attestation or tamper-proof storage. Keep the
expected head hash independently: a local hash chain alone cannot reliably prove
that no valid tail was removed. This addition does not create shared remote memory.

## Proposed cross-platform workflow, not yet live

1. Intake: import the owner's actual Gemini/Claude project exports or source
   repository snapshots. Preserve originals, timestamps, source references,
   permissions and content hashes. Do not infer unseen content from tutorial titles.
2. Reconcile: compare decisions, code and workflows against a common base revision.
   Deduplicate identical artifacts; retain conflicts for independent review.
3. Hermes: route a bounded task to registered, authorized platform adapters.
   Each handoff carries a bundle ID, project, base revision, source, changes,
   evidence, tests, approval state and next action. Blocked access stops that path;
   it does not create authorization or justify retries after a denial.
4. MemPalace: retain evidence receipts and separately permissioned project memory.
   Public hashes do not make private source content public. Retrieve prior accepted
   decisions before proposing a conflicting change.
5. Quality review: run deterministic checks and obtain a separate reviewer.
   For referral content, verify attribution, program terms and plain-language
   compensation disclosure. AI agreement alone is not proof.
6. Delivery: create a GitHub review diff and a Hostinger staging preview. A live
   integration requires authenticated tests on the correct accounts and site.
   Preserve owner approval for publishing, merges, spending and financial actions.
7. Later bounded autonomy: deploy a runner with per-action scopes, idempotency,
   retry limits, a dead-letter queue, spending caps and a kill switch. Enable only
   successfully verified adapters. None of that scheduling was activated here.

Read/draft/validate routines can be candidates for preauthorized automation.
Sending messages, submitting credit applications, changing payout instructions,
publishing or spending are not authorized by a generic workflow request.

## Sabrina Ramonov and Claude material

The owner identified Sabrina Ramonov and Claude work as an additional input.
An exact owner project export from that work has not been imported in this change.
Sabrina's public course covers project instructions, permissions, tools and
workflow practices. It is an educational reference, not proof that she is an
operator, collaborator, endorsing party or installed agent in this system.
Preserve attribution and check reuse rights before importing third-party code or
templates. Existing `CLAUDE.md` or other project rules must be compared, not replaced.

Public learning reference, retrieved October 14, 2026:
https://www.sabrina.dev/p/every-claude-code-concept-explained-beginners

## Referral-content review

The FTC advises clear, conspicuous disclosure of material connections, close to
the recommendation. A hidden footer or unexplained 'affiliate link' label is not
a substitute for understandable compensation disclosure.

Draft wording for review, not published:
'I may receive compensation from the provider when you use these referral links.
Review the provider's current terms and eligibility requirements directly.'

Do not add unverified claims about guaranteed approvals, credit-score changes,
income, commission rates, no additional cost or payout timing. Use provider-hosted
application flows; do not put applicants' sensitive information in public GitHub,
general-purpose swarm memory or unauthenticated forms. This is an engineering
review plan, not a legal compliance certification or financial recommendation.

Official reference, retrieved October 14, 2026:
https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking

## Verification and reproducibility

Syntax checks passed separately for the new module, its tests and the inspected
Hermes source. The targeted offline suite ran on Python 3.13.5 on October 14, 2026
at 20:03:32 UTC: **14 tests, 0 failures, 0 errors, 0 skipped**.
This was not a run of the full repository test suite and is not a live integration
or independent security review. Windows execution was not tested.

A local CLI run also generated a valid MemPalace review receipt and left all 18
program checks unresolved. Provider calls, applications submitted, payments and
production deployments in these tests: zero.

New module SHA-256:
`5cdc62c8a3f76b926d60b30b44cf8b44b7819109310b12c3db42219433080494`

New test file SHA-256:
`738e9715bf526a6bfa2faaf860dba7302750259883ad32bf01cb89ef0acb08f3`

Inspected `src/jarvis/hermes.py` SHA-256:
`b5a517e783c13cfe9ef6c3967e468289a3a1e0fc6942227e54a7f12963da73d9`

From the repository root, without installing dependencies (POSIX shell):

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_referral_review.py -v
PYTHONPATH=src python3 -m jarvis.referral_review config/referral-programs.public.json
```

To record evidence, add `--ledger` with a private local SQLite file path. Keep real
ledgers and detailed source artifacts out of public version control.

## Review state, recovery and next task

Review state: draft, not merged, no independent reviewer. No live Gemini/Claude
handoff, Hostinger edit, affiliate dashboard login or persistent runner was verified.
The available session connector set did not expose a direct Gemini, Claude or
Hostinger account action; GitHub read/write access was verified. Connector listing
is not a test of services available in the owner's other workspaces.

Recovery: revert the referral-addition commits on the review branch, preserving
unrelated Hermes work; retain local evidence for comparison. No live deployment
rollback is needed for this change because none occurred.

Next bounded task: import one actual Sabrina/Claude or Gemini project handoff,
compare it to this branch and produce a conflict-aware review diff with source
receipts. Do not activate scheduling or silently merge different projects.
