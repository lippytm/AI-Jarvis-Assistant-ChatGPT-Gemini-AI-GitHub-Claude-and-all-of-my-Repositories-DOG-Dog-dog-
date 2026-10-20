# AI Jarvis Handoff Toolkit v0.2

Owner: Charles Earl Lipshay / lippytm.AI. Component release, October 14, 2026.
Status: review-branch implementation; locally tested; not merged or deployed.
This extends the existing Hermes/MemPalace work. It does not replace the separate
Linux Development Studio v0.8, read private Claude/Gemini conversations, or activate
a continuously running swarm.

## Delivered capabilities

- `verify`: inspect a `jarvis.bundle.v1` archive without extracting or executing it.
  Check declared/actual files, byte counts and SHA-256 values; reject duplicate JSON
  keys, duplicate archive paths, path traversal, case collisions, file/directory
  collisions, symlinks, unsupported compression and encrypted entries.
- `preview`: compare two verified bundles. Classify additions, unchanged files,
  changed-file conflicts and base-only files that must be preserved. Never infer
  deletion from omission. Flag agent-instruction, environment and policy filenames
  for extra review. This is a two-way file-hash comparison, not a semantic merge.
- `plan`: validate up to 16 allowlisted tasks and their dependencies, reject cycles
  and missing dependencies, and return deterministic dependency layers. It executes
  no tasks and starts no scheduler. `owner-approval` is explicitly unimplemented.
- `referrals`: reuse the existing three-channel offline referral validator without
  changing URLs or partner attribution. Link destinations, commissions, accounts
  and payout status are not verified by these local checks.
- Optional MemPalace receipts persist local result hashes. Reports can be verified
  against a separately retained head hash; raw prompts and file contents are not
  copied into the new receipt metadata.

The tool has no network client, shell command runner, dynamic tool loader, approval
endpoint, publishing path, payment path or provider invocation. Imported text is
handled as data, never installed as an agent's instructions.

## Actual validation

Final local check: 2026-10-14T20:25:18.445070+00:00, Python 3.13.5, Linux.
48 tests passed: 34 new handoff/planning tests plus 14 retained referral/Hermes tests.
Failures: 0. Errors: 0. Skips: 0. Syntax was checked separately before behavior tests.
This is not the full repository suite, a live integration test or an independent
security audit. Windows execution was not tested.

The local Hermes integration test executes the actual verifier and comparison
functions, records their hash-linked results, then stops before a Hostinger-labeled
publication stage. Its station names are routing labels for local test handlers,
not evidence that ChatGPT, GitHub, Claude, Gemini or Hostinger was contacted.
A failed intake test verifies that downstream work does not run.

The example comparison reports one conflict, one proposed addition and one
base-only file preserved. It writes and deletes zero source files. The plan example
executes zero tasks. The referral example retains all 18 unresolved review gates.
All examples are synthetic, not imported customer or private account records.

Source SHA-256:
- `src/jarvis/handoff_guard.py`: `ec59211496e60880f657daf7088bb1b9158001dca1ccaae43358c9ec2983b6a6`
- `tests/test_handoff_guard.py`: `94908d2697909e10a3b7a6bd403ab7fa97723ec44982552702bc7024be2885a6`

## Invocation from the repository

With Python 3.11 or later, from the repository root:

```sh
PYTHONPATH=src python3 -m jarvis.handoff_guard catalog
PYTHONPATH=src python3 -m jarvis.handoff_guard verify /path/to/export.jarvis.zip
PYTHONPATH=src python3 -m jarvis.handoff_guard preview /path/to/base.jarvis.zip /path/to/incoming.jarvis.zip
PYTHONPATH=src python3 -m jarvis.handoff_guard plan /path/to/workflow.json
PYTHONPATH=src python3 -m jarvis.handoff_guard referrals config/referral-programs.public.json
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_handoff_guard.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_referral_review.py' -v
```

Use `--expected-sha256`, `--base-sha256` and `--incoming-sha256` for independent
archive anchors. Put the optional `--ledger /private/path/review.sqlite` before
the command. The downloadable component includes a `run_toolkit.py` launcher,
synthetic examples, raw results and an exclusive-output `check_toolkit.py` helper.
No pip dependency installation is required for this component.

A plain chat export or arbitrary ZIP is not automatically a compatible bundle.
The existing `jarvis.bundle.v1` format requires `manifest.json` with `schema`,
`run_id`, and `files`; each file entry contains `path`, `bytes` and `sha256`.
Optional manifest fields are `workflow` and `created_at`. Only declared files
are accepted; directory-only entries are rejected. Keep the original export intact
and prepare a reviewed copy rather than silently renaming or altering it.

## Resource bounds and limitations

Limits are 8,000,000 archive bytes, 1,000,000 bytes per ordinary file, 4,000,000
bytes total including the manifest, 64,000 manifest bytes, 128 entries including
the manifest, compression ratio 100:1, and 16 tasks. These stricter limits can
reject otherwise valid legacy bundles. Names use a conservative portable ASCII
subset; rejection is intentional rather than an implicit conversion.

Hashes establish byte consistency, not authorship, safe behavior, human approval,
provider identity, truth or ownership. An attacker who replaces both content and
its untrusted manifest can recompute the hashes. A local chain is not an externally
signed attestation. Store the expected anchor outside the agent-writable ledger.
Reports contain filenames and may reveal private project metadata: keep them
private unless cleared for sharing. SHA-256 is not encryption.

These checks are not a hostile-host sandbox, antivirus or complete prompt-injection
filter. Final-input symlinks are rejected, but hostile concurrent filesystem changes,
parent-directory substitution, process isolation and OS resource enforcement require
a separately hardened runner. Other legacy CLI paths are unchanged and do not
magically inherit the new guard. Do not expose this CLI as an untrusted public API.

## Evidence and next bounded integration

Before promotion, inspect the exact review-branch diff and current CI. Keep old
artifacts and approvals intact. Test one owner-authorized, non-sensitive Claude or
Gemini export against its separately supplied hash, preview differences against the
intended base, and obtain independent review of conflicts. Add provider adapters,
credential storage, budget limits, deduplication, retries and authenticated approval
only as separately scoped, tested changes. No account enrollment, financial
application, spending, publication, merge or production rollout is authorized here.

Charles remains the final authority. An AI vote or a JSON flag never substitutes
for his decision. Recovery for this release is to stop invoking the new component;
no original input artifacts are changed by verification or preview. Review-branch
source changes can be reverted without altering public websites.

## Primary engineering references

Reviewed October 14, 2026; these guide the design, not certify this implementation.

1. OpenAI, Safety in building agents: structured fields, untrusted-input separation,
   approvals and evaluation. https://developers.openai.com/api/docs/guides/agent-builder-safety
2. Anthropic, Building effective agents: simple composable workflows, documented
   tools and measured complexity. https://www.anthropic.com/engineering/building-effective-agents
3. Python, zipfile documentation: unsafe names, resource limits and decompression
   pitfalls. https://docs.python.org/3.13/library/zipfile.html
