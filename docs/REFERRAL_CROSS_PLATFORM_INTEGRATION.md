# Jarvis cross-platform referral integration

Version: 0.2.0 | October 20, 2026 | Registry schema: 1.1.0
Status: offline review implementation, locally tested; no deployed referral service.
Project owner and final release authority: Charles Earl Lipshay.

## Preserved foundation

This extends the existing referral review tool. The original addition was prepared
on `jarvis/unified-ai-fabric-v0.1` in PR #6, stacked on Control Tower PR #2, from
inspected source revision `9d9860386bed8a177c0cc07fd4cf1e0060df44f0`.
Those original promotions are recorded in [the operational pilot](OPERATIONAL_PILOT.md).
The historical test and hash record below remains evidence of the October 14
version; it is not the identity or test result of this updated module.

GitHub contains the public-safe code and review evidence. Private project content,
customer records, provider credentials and detailed financial records stay outside
public repositories. No permission expansion, account login or public website
publication is implied by this document.

## Four exact current funding routes

| Registry ID | Intended routing | Original owner-supplied URL |
|---|---|---|
| `7figures-customer` | Customer referral, not partner recruitment | `http://www.7figurescredit.com?a_aid=lippytm` |
| `7figures-partner` | Referral-partner recruitment; supplied parameter unverified | `http://7figurespartners.com?a_lippytm` |
| `lendtrack-partner` | Separate referral-partner program | `http://lendtrack.ai/join/lippytmai` |
| `getbizfunds-business` | Business funding site / proposed gateway destination | `lippytmai.getbizfunds.com` |

The registry preserves these strings byte for byte. In particular,
`?a_lippytm` must not become `?a_lippytm=` or `?a_aid=lippytm`.
The LendTrack path and GetBizFunds host use `lippytmai`; the customer referral
parameter uses `lippytm`. GetBizFunds was supplied without a scheme.
Its separately recorded HTTPS candidate is a proposed URL to check, not a
replacement for the original or an approved publication destination.

The earlier Partners route, `http://join.7figurespartners.com/?a_aid=lippytm`, is
retained exactly in `prior_original_urls` as prior evidence. It is not an
additional current route or a fallback to select silently. Schema 1.1.0 requires
all four current records and the exact prior-evidence list. Older three-record
files require an explicit update; the validator does not migrate them silently.

These programs are distinct from any Hostinger product-affiliate account.
Hostinger may be a website delivery platform, not evidence of account membership
in these referral programs.

Retrieval of the four exact supplied targets, using an HTTPS candidate for the
scheme-free GetBizFunds host, was inaccessible through the web tool on October 20.
Tool normalization, including adding `=` to the Partners query, is not an observed
server redirect and must not change the registry. These access limitations do not
show that a site is down or tracking is broken. Public homepage and search-index
content can describe a program, but cannot prove this owner's referral credit,
account membership or payout rights.

Each route has six outstanding checks: HTTPS destination, account membership,
referral attribution, program terms, public copy and owner release scope.
All 24 checks remain unverified in the repository's draft registry.
Commission rates, payout status and account ownership were not independently
verified. A successful page load would not, by itself, prove referral credit.

## Implemented now

`src/jarvis/referral_review.py` is a standard-library offline tool that validates
this exact four-route intake and generates a review packet. It rejects changed
referral identifiers, substituted destinations, duplicate/missing channels,
changed prior evidence, unexpected fields, invented commissions, duplicate JSON
keys and oversized input.
Network, automatic publication and spending must remain disabled.

A JSON gate marked `verified` is treated only as an assertion. Even if every gate
is marked verified, this tool never grants publication or spending authority.
There is no network request, provider API call, loan application, payment or
publishing function in the new module.

The public operator name is owner-reported as Intergalactic Corporate Services LLC,
formed September 8, 2026, with support address
`support@intergalacticcorporateservices.com`. These facts do not establish any
provider partnership or account ownership. Private entity and tax records are not
part of this registry. The earlier Hostinger design places a co-branded
`/funding-readiness` gateway on `aievolutionaryevolutions.com`; its proposed
destination and readiness checks are in
[the Hostinger mapping plan](PROPOSED_HOSTINGER_WORKFLOW_MAPPINGS.md).

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

## Current offline verification

The focused suite on October 20, 2026 passed **36 tests, 0 failures, 0 errors,
0 skipped**: 17 referral-review tests, 16 Hostinger adapter tests and 3 existing
Hermes tests. Hostinger responses and failures were injected; no account was
contacted. The referral tests preserve all four originals, reject the normalized
Partners query and substituted prior evidence, preserve the scheme-free
GetBizFunds original, and confirm that asserted review flags never grant release.
This is a focused suite, not a report of the full repository tests or a live
Hostinger/referral integration. An additional 3 existing brain-fleet tests passed
after the capability-documentation update, retaining 145 planning combinations
and zero authenticated live pairs. The new Hostinger regressions reject repeated
records and overlapping domain/Horizons identities without writing a success
receipt, including overlaps whose other record fields differ.

Reproduce from the repository root without provider credentials:

```sh
PYTHONPATH=src python3 -m unittest tests.test_hostinger tests.test_hermes tests.test_referral_review -v
PYTHONPATH=src python3 -m jarvis.referral_review config/referral-programs.public.json
```

To record the offline review, add `--ledger` with a private local SQLite file path.
Keep real ledgers and detailed source artifacts out of public version control.

## Historical verification: October 14 version 0.1.0

Syntax checks passed separately for the new module, its tests and the inspected
Hermes source. The targeted offline suite ran on Python 3.13.5 on October 14, 2026
at 20:03:32 UTC: **14 tests, 0 failures, 0 errors, 0 skipped**.
This was not a run of the full repository test suite and is not a live integration
or independent security review. Windows execution was not tested.

A local CLI run also generated a valid MemPalace review receipt and left all 18
program checks unresolved. Provider calls, applications submitted, payments and
production deployments in these tests: zero.

Historical module SHA-256:
`5cdc62c8a3f76b926d60b30b44cf8b44b7819109310b12c3db42219433080494`

Historical test file SHA-256:
`738e9715bf526a6bfa2faaf860dba7302750259883ad32bf01cb89ef0acb08f3`

Historically inspected `src/jarvis/hermes.py` SHA-256:
`b5a517e783c13cfe9ef6c3967e468289a3a1e0fc6942227e54a7f12963da73d9`

## Review state, recovery and next task

This update prepares offline review packets and a bounded inventory adapter.
No live Gemini/Claude handoff, Hostinger account inventory/edit, affiliate dashboard
login or persistent referral runner was verified by these changes. The public
GitHub audit evidence is separate and does not establish those connections.
Current release/promotion evidence belongs in
[the operational pilot](OPERATIONAL_PILOT.md), not in a local draft status assertion.

Recovery: revert only the relevant reviewed change, preserving unrelated Hermes
work and keeping local evidence for comparison. Reverting the registry to schema
1.0.0 also requires its matching old validator; the current validator intentionally
rejects the old shape. No live deployment rollback was exercised here.

Next bounded task: identify the owner's actual two workflow names/exports and
triggers, map them to the proposed Hostinger actions, then verify the intended
account/site and provider destinations. Preserve source receipts and conflicts
when importing actual Claude/Gemini handoffs. No unnamed workflow has been added
to the shipping catalog and no scheduler has been activated by this update.
