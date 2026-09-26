# Hermes Fabric, MemPalace and Hostinger pilot

Status: review branch; local pilot verified, Hostinger account unverified.

## Execution contract

`jarvis.hermes.run_swarm` accepts an ordered, bounded sequence of registered stations. It passes each output to the next injected handler, stops on failure, and creates a pending-owner-approval receipt before consequential actions. It never invokes a provider on its own. The current prototype supports up to eight stages and has no scheduler.

`MemPalace` stores only station, action, status and input/output hashes in SQLite. Each entry links to the preceding hash; `verify` detects changes to recorded evidence. Keep real prompts, customer data, credentials and model output out of public repositories and public logs. A hash chain detects mutation of this local file; it is not a signed external attestation or a backup.

## Hostinger connection

The read-only adapter calls the official `GET /api/hosting/v1/websites` endpoint only when `allow_external=True` and `HOSTINGER_API_TOKEN` is available in the environment. It has no methods to edit the AI Website Builder, deploy, publish, delete or buy services. No token or account details are in this repository.

```python
from jarvis.hostinger import list_websites
sites = list_websites(allow_external=True)
```

Store the token in a secret manager or local environment, never a committed `.env` file. Review the returned website inventory privately and confirm that `aievolutionaryevolutions.com` is associated with the intended account. The public integration status changes to verified only after an actual authenticated, read-only response and a redacted receipt are checked. The official API endpoint may not expose editing for the Hostinger AI Website Builder; that workflow requires separate validation.

## Rollout to other repositories

1. Use the public-only inventory in `config/public-repository-fleet-rollout.json`; review repository identity and default branch at rollout time. Never expose private repository names in the public manifest.
2. Add a per-repository integration contract on a review branch, with station ID, permitted read/draft actions, schema version, owner approval boundaries, and rollback instructions.
3. Test a local handoff and MemPalace verification; require CI and independent review for code changes.
4. Activate only the repos and workflows that actually have installed integrations and a verified harmless round trip. Do not describe a documentation-only link as a live connection.

Official API reference: https://docs.hostinger.com/api-reference/overview
