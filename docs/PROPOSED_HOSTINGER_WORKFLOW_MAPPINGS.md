# Proposed Hostinger workflow mappings

Prepared October 20, 2026. These are two concrete proposed mappings for review.
The owner's two existing workflow names, exports and triggers have not yet been
identified. No new shipping catalog workflow, account connection, website edit or
scheduler is established by this document.

## Preserved business and site decisions

The prior design identifies `aievolutionaryevolutions.com` as the canonical domain
and Intergalactic Corporate Services LLC as the operator. The operator name,
September 8, 2026 formation date and public support address
`support@intergalacticcorporateservices.com` are owner-reported. Private entity
and tax records do not belong in the public repository or general swarm memory.
Neither domain ownership, current DNS nor the actual Hostinger product has been
verified in this work.

An approved GitHub release remains the source of truth for reviewed site changes.
The planned `/funding-readiness` page is a co-branded gateway to
`lippytmai.getbizfunds.com`, using an ordinary link by default. A form or API
handoff requires confirmed provider support and the relevant consent. An iframe
requires permission and is not the default. These decisions carry forward from:

| Prior source | Persistent source evidence | Design used here |
|---|---|---|
| `HOSTINGER_ECOSYSTEM_INTEGRATION_BLUEPRINT_v0.1.md` | Version 1; modified `2026-09-17T19:12:03.490504Z`; source ID `file_000000004e6c81fb9e53d4ed40308d6f` | Canonical domain, approved GitHub source, site inventory, funding gateway and conditional handoffs |
| `hostinger-deployment-blueprint-v1.md` | Modified `2026-09-16T21:58:21.454523Z`; source ID `file_00000000e1c481fdb09a8f3b008455ea` | Static-first deployment, account-dependent hosting paths, backups and staged rollout |

These source identifiers describe the inspected private source versions; the
source files themselves are not embedded in the public repository. They contain
no evidence that the two requested automations are currently installed.

## Two proposed mappings

| Mapping | Inputs and trigger | Existing implementation and output | Remaining concrete checks |
|---|---|---|---|
| **A. Site inventory to Jarvis review** | An explicitly authorized manual read of the intended Hostinger account; private token; target domain | `jarvis.hostinger.list_websites` performs bounded GET-only inventory and can append a metadata-only local MemPalace receipt. A private reviewer checks the returned site records against the target. | Identify the real workflow/trigger; authenticate to the intended account; confirm the target site, product and permissions. Inventory does not check DNS, page content or site health. |
| **B. Funding gateway review to staging handoff** | A named source workflow/export; sanitized business context; the exact four-route registry; approved source revision | `jarvis.referral_review` produces an offline review packet with unresolved checks. Existing Hermes stages can pass that draft through registered, injected handlers and stop before publish. | Verify destination/attribution and copy; inspect the actual site; prepare a reviewed `/funding-readiness` draft and backup/staging plan. No Hostinger draft-upload or publish adapter is implemented here. |

For mapping A, the adapter reads only the fixed website-list endpoint. It requests
up to 100 records per page and stops at 250 websites, 10 pages or 1 MiB per response.
It rejects partial or changed pagination and refuses redirects. The 15-second
per-request transport timeout is not an end-to-end wall-clock deadline. A receipt
labels the scope `hostinger_account_website_inventory`, records the report hash
and completeness, and distinguishes injected test transport from default HTTPS.
Raw account records stay private. A read receipt does not authorize a later write.
Duplicate exact records and repeated documented domain/Horizons identities stop
the run before a success receipt. Records with neither optional identity are
counted separately. The completeness claim concerns observed pagination and
available record identities; it is explicitly not a transactional snapshot or
ownership proof. The endpoint can include sites shared by other clients.

For mapping B, the default funding gateway links to the GetBizFunds destination
only after its scheme and destination are verified. Preserve the supplied original
`lippytmai.getbizfunds.com` in the source registry; its HTTPS candidate is separate.
The other three routes remain distinct choices for customer funding or partner
recruitment. Do not silently combine their purposes, substitute an earlier route,
append new tracking parameters or assume any commission entitlement.

## Exact routing inputs

| Registry ID | Latest supplied string | Attribution and publication state |
|---|---|---|
| `7figures-customer` | `http://www.7figurescredit.com?a_aid=lippytm` | Destination and referral credit unverified |
| `7figures-partner` | `http://7figurespartners.com?a_lippytm` | Keep the query exactly as supplied; recognition is unverified |
| `lendtrack-partner` | `http://lendtrack.ai/join/lippytmai` | Join route, membership and referral credit unverified |
| `getbizfunds-business` | `lippytmai.getbizfunds.com` | No original scheme supplied; proposed gateway destination unverified |

The earlier Partners string `http://join.7figurespartners.com/?a_aid=lippytm`
remains separate prior evidence. It is not a fallback destination. Exact-route web
retrieval was inaccessible in this session; internal tool normalization is not a
verified HTTP redirect. These limitations do not prove that a site is down. No
forms, credit applications, messages or account settings were submitted or changed.
All 24 review checks remain unresolved in the draft registry.

## Shared instructions, context and evidence

The repository Prompt #11 operating profile, `P-011-E6C-001` revision
`repository-1`, supplies shared guidance to the eight shipping Python workflows
and the local Node task planner. Plans/results identify its revision and exact
file hash. This gives the covered local runtimes an explicit common instruction
source; it does not connect every external assistant or synchronize remote work.
See [the profile contract](PROMPT11_WORKFLOW_PROFILE.md) for enforced controls
versus guidance, including independent quality review and scoped handoffs.

The optional [business-context projection](BUSINESS_CONTEXT.md) can attach approved
public business facts to a local task. It is not an automatic Hostinger upload or
a shared remote memory service. Actual Gemini/Claude project exports require
explicit source identity and permission before comparison or handoff. Keep
conflicts visible instead of treating different project editions as synchronized.

Hermes uses injected registered handlers and a bounded sequence; it does not
install adapters or run providers by itself. MemPalace receipts are local to the
chosen journal/run. They record hashes and scope, not signed provider attestations.
There is no restored cross-run Hostinger journal or deployed shared MemPalace
service in this implementation. Independently retain the expected receipt head
when checking for evidence changes or truncation.

## Before any live site change

1. Identify the two actual workflow names, source revisions, trigger events and
   permitted output actions. Match them to A or B only when their behavior fits.
2. Verify the Hostinger account and domain association; determine whether the
   site is Website Builder, WordPress, custom/static, Node or Horizons. Verify DNS
   separately and privately inventory pages, forms, scripts and redirects.
3. Confirm destination and attribution behavior through an authorized review of
   the actual provider routes and account terms. Check the relationship between
   current Lippytm/Lippytm.AI branding and the owner-reported LLC before public copy.
4. Prepare a restorable site backup, a staging plan, a bounded diff from the
   approved GitHub release, rollback instructions and independent review evidence.
5. Obtain the action-specific release authorization before the chosen site write.
   Stop on a scope mismatch, missing permission, failed check or unsupported
   product. Do not retry through a different account or product to bypass a stop.

These are implementation prerequisites, not proof that they have already passed.
The current adapter enforces read-only scope and opt-in; the draft-review module
has no publication or spending function. The broader staging and rollout process
remains proposed until the real workflow and hosting environment are identified.

## Current official API capabilities

The [website-list endpoint](https://docs.hostinger.com/api-reference/endpoints/hosting/websites/list-websites)
and [pagination contract](https://docs.hostinger.com/api-reference/pagination)
support mapping A. The [Horizons index](https://docs.hostinger.com/api-reference/endpoints/horizons/websites)
now lists edit and publish operations, and hosting has a separate
[static archive deployment endpoint](https://docs.hostinger.com/api-reference/endpoints/hosting/websites/deploy-static-site-archive).
This corrects the earlier assumption that Horizons editing was available only
through its editor. Exact mutation contracts and account entitlement still need
review for the selected product; no such calls are implemented or activated here.
The [API overview](https://docs.hostinger.com/api-reference/overview) states that
tokens inherit user permissions, so a GET-only adapter is a code boundary rather
than a token-level restriction over all Hostinger APIs.

Official documentation reviewed October 20, 2026. Focused verification is recorded
in [the referral integration record](REFERRAL_CROSS_PLATFORM_INTEGRATION.md);
the separate live GitHub audit evidence is in [the operational pilot](OPERATIONAL_PILOT.md).
