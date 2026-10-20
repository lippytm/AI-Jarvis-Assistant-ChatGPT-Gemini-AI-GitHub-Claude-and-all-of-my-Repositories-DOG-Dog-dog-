# Hermes Fabric, MemPalace and Hostinger pilot

Status: local pilot and mocked inventory tests passed; Hostinger account unverified.
Documentation reviewed October 20, 2026. See [the operational pilot](OPERATIONAL_PILOT.md)
for the separate GitHub execution and promotion evidence.

## Execution contract

`jarvis.hermes.run_swarm` accepts an ordered, bounded sequence of registered stations. It passes each output to the next injected handler, stops on failure, and creates a pending-owner-approval receipt before consequential actions. It never invokes a provider on its own. The current prototype supports up to eight stages and has no scheduler.

`MemPalace` stores local SQLite evidence. The Hermes path records station, action,
status and input/output hashes; the optional Hostinger receipt records the limited
inventory metadata described below. Each entry links to the preceding hash.
Keep real prompts, customer data, credentials, inventory records and model output
out of public repositories and public logs. Verify against an independently kept
expected head hash to detect a removed tail as well as changed entries. This is
local consistency evidence, not a signed external attestation, backup or shared
remote memory service. A fresh runner has no earlier journal unless one is
explicitly restored through an approved storage design.

## Hostinger connection

The adapter in `src/jarvis/hostinger.py` calls only the official
`GET /api/hosting/v1/websites` endpoint. It requires literal `allow_external=True`
and a valid nonempty `HOSTINGER_API_TOKEN` from the environment or an explicitly
supplied token. It has no edit, deploy, publish, delete or purchase methods.

The [official inventory contract](https://docs.hostinger.com/api-reference/endpoints/hosting/websites/list-websites)
covers the authenticated client's CloudLinux, Builder and Horizons websites.
[Documented pagination](https://docs.hostinger.com/api-reference/pagination) uses
`page`, `per_page` and a response shaped as
`{"data": [...], "meta": {"current_page": 1, "per_page": 100, "total": 0}}`.
The adapter constructs every page URL itself, requests up to 100 items per page,
refuses redirects, and caps the operation at 250 websites, 10 pages and 1 MiB per
response. Each request uses a 15-second transport timeout; this is not a global
wall-clock deadline. Transport errors expose a fixed message rather than an
upstream body or credentials.

A successful result requires consistent page metadata and exactly the advertised
number of records. Unexpected, changed, repeated, incomplete or over-limit
pagination fails instead of returning a truncated inventory as complete. Exact
record duplicates are rejected within and across pages. The
[official website model](https://github.com/hostinger/api-python-sdk/blob/main/docs/HostingV1WebsitesWebsiteResource.md)
documents optional `domain` and `horizons_uuid` fields; the adapter also rejects
repeated available identities even if other record fields change. Sites without
either field are counted in `identity_unavailable_records`. Completeness covers
the observed pagination and available identities, not a transactional snapshot;
both the report and receipt explicitly record `transactional_snapshot=false`.
The adapter does not follow response-supplied URLs or require invented site fields.

```python
from jarvis.hermes import MemPalace
from jarvis.hostinger import list_websites

# This opt-in performs real account reads. Use an approved private runtime path.
ledger = MemPalace("/private/runtime/hostinger-inventory.sqlite")
report = list_websites(allow_external=True, ledger=ledger)
# Inspect report["data"] privately; do not print it to public CI logs.
```

Store the token in a secret manager or local environment, never a committed
`.env` file. Hostinger's [authentication overview](https://docs.hostinger.com/api-reference/overview)
says API tokens inherit the user's permissions; this adapter's GET-only behavior
does not convert a token into an account-wide read-only credential.

The result includes raw private website records, observation timestamps,
`complete`, record/page counts and the transport type. An optional local MemPalace
receipt contains counts, scope, a report hash, observation time and
`shared_sync_established=false`; it contains no raw domains, account fields or
token. Its `inventory_response_validated` status means the response passed this
adapter's checks. An injected test transport is labeled `injected`, so its receipt
does not prove live account access. Failed inventory does not append a successful
inventory receipt. Retain the returned receipt head independently for verification.

The [official method documentation](https://github.com/hostinger/api-python-sdk/blob/main/docs/HostingWebsitesApi.md)
states that inventory can include other clients' shared-access websites, so
appearance in a response is not proof of ownership. Review an actual authenticated
response privately to establish whether
`aievolutionaryevolutions.com` belongs to the intended account. Inventory alone
does not prove current DNS, site content, application health, editing rights or a
successful release. None of those account checks has been performed here.

The current [Horizons website API index](https://docs.hostinger.com/api-reference/endpoints/horizons/websites)
documents creation, editing and publication operations. The hosting API also
documents [static archive deployment](https://docs.hostinger.com/api-reference/endpoints/hosting/websites/deploy-static-site-archive).
These product capabilities do not mean this adapter implements them, nor establish
which product hosts the target domain. Verify the actual Website Builder,
WordPress, custom/static, Node or Horizons site before choosing an integration.
Exact write contracts, site backup, staging and release approval remain separate
work. The two bounded proposed mappings are in
[the Hostinger mapping plan](PROPOSED_HOSTINGER_WORKFLOW_MAPPINGS.md).

## Rollout to other repositories

1. Use the public-only inventory in `config/public-repository-fleet-rollout.json`; review repository identity and default branch at rollout time. Never expose private repository names in the public manifest.
2. Add a per-repository integration contract on a review branch, with station ID, permitted read/draft actions, schema version, owner approval boundaries, and rollback instructions.
3. Test a local handoff and MemPalace verification; require CI and independent review for code changes.
4. Activate only the repos and workflows that actually have installed integrations and a verified harmless round trip. Do not describe a documentation-only link as a live connection.

Official API reference: [Hostinger API overview](https://docs.hostinger.com/api-reference/overview).
