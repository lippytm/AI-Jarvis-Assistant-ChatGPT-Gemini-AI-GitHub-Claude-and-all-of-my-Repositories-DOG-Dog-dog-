# Optional owner business context

The Python workflow runner can project a private owner record into a small pack
of business facts and supply that same pack as task data to each executed AI
step. This is an optional local input. It does not change Prompt #11, the seven
registered workflow definitions, their role instructions, or any approval and
execution gate.

## Export a reusable pack

From an installed checkout, use:

```sh
jarvis business-context /private/owner-business-context.json --json
```

For a source checkout without the installed command, use
`PYTHONPATH=src python -m jarvis` in place of `jarvis` from the repository root.
The export command reads one local file and writes the sanitized pack to standard
output. It does not initialize the task ledger, call an AI provider, fetch a
funding link, inspect a hosting account or write the private source into the
repository. Keep the private source outside public repositories and outputs.

The source must use `schema: jarvis.owner-business-context.v1`,
`source.kind: owner_supplied_in_conversation`, and
`source.verification_status: owner_reported_not_independently_verified`.
Only these facts are copied:

| Source fields | Projected data |
|---|---|
| `record_id` | Original record identity and a derived projection ID |
| `business.legal_name`, `business.support_email`, `business.formation_date` | Owner-reported business facts |
| `funding_channels[].id`, `owner_supplied_value`, `owner_described_role` | Funding channel identifiers, exact supplied values and described roles |
| `prior_project_baseline.canonical_website_domain`, `funding_gateway_path` | Prior canonical domain and gateway facts |
| `prior_project_baseline.domain_basis` | `source_qualifier`, preserving the prior evidence qualification |

The pack also carries the fixed owner-reported verification status. Funding
values retain their exact spelling, casing, referral parameters and surrounding
spaces. The projector does not substitute an earlier repository value, resolve a
URL, verify attribution, or infer a partnership or commission arrangement.

Tax identifiers, tax documents, private administration fields, account and
application data, requested account connections, approval-like booleans and all
other unlisted fields are excluded. The implementation constructs new allowed
objects; it does not export a redacted copy of the full private record. A
credential recognized by the existing sensitive-data scanner in an allowed
field blocks the export instead of changing the owner's value.

Inputs must be regular local UTF-8 JSON files no larger than 64 KiB. Remote URLs,
final symlinks, malformed or duplicate JSON fields, unsupported source metadata,
invalid required fields and duplicate funding IDs fail with static errors.
There may be at most 16 funding channels. Strings are bounded, and formation dates
must be valid `YYYY-MM-DD` dates. Validation establishes the accepted data format;
it does not independently verify company formation or domain ownership.

## Use the facts in a plan or run

Both flags are optional:

```sh
jarvis plan unified_life_business_creation "Prepare a review brief" \
  --business-context /private/owner-business-context.json --json

jarvis run unified_life_business_creation "Prepare a review brief" \
  --business-context /private/owner-business-context.json --json
```

`plan` projects the source and reports its identity without executing workflow
steps or contacting a provider. `run` reads and sanitizes the source once for that
invocation. Each AI step that actually executes receives the same safe pack in
its user/task prompt, with a label explaining that it grants no authority,
account access or independent verification. The step's system role and shared
Prompt #11 system text remain unchanged.

An external provider still requires the existing `--allow-external` opt-in,
configured credentials and model, and call budget. The flag shown above does not
enable external calls. Approval steps stop downstream work as before; supplied
business facts cannot approve a release, publication or financing application.
The existing sensitive-input gate still applies to the task's input. A detected
credential in the business projection is always refused, including when a caller
explicitly permits sensitive task input.

Omitting `--business-context` preserves the existing prompt, plan/report shape
and cache identity. The current `plan` and `run` flags accept the **private source
schema**, not an arbitrary replacement pack or remote file. The separate export
is the reusable artifact for another authorized workspace.

## Provenance and reuse

The exported pack uses `jarvis.business-context-projection.v1` and a
`projection_id` of `owner-business-context-v1:<record_id>`. Its `sha256` is computed
from the projected JSON **without** the `sha256` field, using sorted keys, compact
separators, unescaped Unicode and UTF-8 encoding:

```python
sha256(json.dumps(projection, sort_keys=True, separators=(",", ":"),
                  ensure_ascii=False).encode("utf-8")).hexdigest()
```

The private file's bytes and excluded values are never hashed for projection or
workflow identity. Changing a projected fact changes the projection hash and
prevents reuse of a prior workflow result. Changing only an excluded private
field leaves the safe pack and its cache identity unchanged. Each invocation uses
one immutable projection snapshot even if the source file changes afterward.

Plans and reports include `business_context` metadata with the projection schema,
ID, record ID, hash and verification status. They do not include the source file
path or raw private record. The safe facts are deliberately sent to executed AI
steps and can appear in their outputs and local task ledger; the metadata is not
proof that any external account was connected or any provider followed the facts.

## Hostinger and Node boundaries

The safe export can be supplied to the local Node pilot as ordinary task text,
within its existing authentication, repository scope and request-size limits.
Node has no business-context file option and does not synchronize this file,
Hostinger accounts, domains, funding applications, or other assistant memories.
The Python feature also performs no automatic file watching or account
synchronization. It establishes a repeatable local projection and per-run task
context, with no claim of live hosting deployment or shared persistent memory.

## Offline verification

`tests/test_business_context.py` uses synthetic names, domains, private fields
and an invalid dummy tax identifier. It checks positive field projection,
unchanged exact funding values, absence of private data in exports/prompts/saved
reports, canonical hashing and cache behavior, CLI export/flags, no provider or
network calls during projection and planning, and retained system, approval,
external opt-in, sensitive-input and call-budget gates.

```sh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_business_context.py' -v
```
