# Creative Studio template workflow

The new local workflow prepares a usable, verifiable template packet for
**The Evolutionary Evolutions Creative Creations Studios of Intergalactic
Corporate Services LLC**. This is the owner's declared studio identity. It does
not rename an existing website or independently establish a new legal entity.

The packet always has `status: intake_required` and `template_only: true`.
It makes no provider calls, renders no media, sends no handoff and publishes
nothing. Even a detailed input request does not change those assertions in this
version. The generator supplies reusable working structures; it does not
interpret a topic or invent source assets.

## Exact intended scope

| Category | Owner-declared labels |
|---|---|
| Formats | Videos; eBooks; Audiobooks; Video Books |
| Purposes | Ad Copy; Affiliate Program Marketing; Educational; Entertainment; Business of Businesses Systems of Systems |
| Intended distribution destinations | Facebook; LinkedIn; Instagram; Threads; SubStack; Hostinger.com |
| Intended AI workspaces | ChatGPT Business; Gemini AI; Claude |

Distribution destinations and AI workspaces are separate lists. A workspace
label is not an API adapter, connected account, imported conversation or installed
publishing tool. The public operator name is Intergalactic Corporate Services
LLC; the studio declaration is owner-reported. Private entity/tax records,
account details and customer applications are not part of the studio config.

## Workflow and review boundary

`workflows/creative_studio_package.json` uses the existing Prompt #11 identity,
`P-011-E6C-001`, revision `repository-1`, and has three ordered steps:

1. `studio_templates`: the fixed local `studio_package` operation creates a new
   packet. The workflow step contains only its ID and type; it cannot select
   another config path, output path, URL, provider or account.
2. `github_review_draft`: the existing handoff operation writes a local review
   file containing the packet location and manifest hash. It does not send a
   message or create a GitHub commit, issue or pull request.
3. `owner_studio_review`: the existing approval operation requests review of that
   concrete packet and stops execution.

The runner records the local package step as `drafted` while retaining
`package_status: intake_required`. The overall workflow stops as
`pending_approval`; those execution statuses do not mean creative content is
complete. An approval record does not resume the workflow or confer permission
for any unrelated production, media generation, platform account or release.

The fixed studio config is included in plan, result and cache identity. A plan
checks the config and any supplied studio declaration without creating a packet
or calling a provider. Omitting optional business context remains supported.
When a cached studio run is reused, the runner verifies its packet and compares
the recorded manifest/provenance anchors; missing or changed evidence stops reuse.
It also reconciles the workflow identity, executed step order, remaining steps and
overall status with the definition. Each executed studio result must agree with
the verifier, including its template status, execution limits and serialized
output. A studio step prevented by an earlier approval needs no packet and remains
unexecuted on reuse. These checks establish local report consistency, not signed
authorship or an automatic approval/resume mechanism.

## Create and inspect a packet

From the repository root:

```sh
PYTHONPATH=src python3 -m jarvis plan creative_studio_package "Prepare studio intake templates" --json
PYTHONPATH=src python3 -m jarvis run creative_studio_package "Prepare studio intake templates" --json
```

The run creates a fresh packet under the local outbox and a separate review
handoff. Its JSON report gives the exact `package_path` and `manifest_sha256`.
The run's approval-pending exit status is expected; it is not an external
execution failure or a successful publication.

The existing optional `--business-context` flag can supply a sanitized owner
projection. See [the business-context contract](BUSINESS_CONTEXT.md). The packet
generator receives an already-loaded `BusinessContext`; it never opens a private
owner source file itself. If that projection contains a studio declaration, its
five label fields and fixed qualifications must agree exactly with the repository
config before any packet file is written. A conflicting brand, format, purpose,
destination or workspace fails instead of being silently reconciled.

Verify the returned packet path with:

```sh
PYTHONPATH=src python3 -m jarvis.creative_studio verify /path/to/returned/studio-packet
```

Successful verification reports `valid: true`, `integrity: verified`,
`status: intake_required` and `template_only: true`. It checks this revision's
immutable template inventory and evidence, not the quality of a finished work.
Invalid packets exit nonzero with a static error.

## What the 20 files contain

| Packet files | Useful working structure |
|---|---|
| `README.md` | How to preserve the original and create a separate working copy |
| `intake.json`, `intake-and-rights.md` | Missing brief fields, audience/objective questions, source/rights ledger and review scope |
| `formats/videos.md` | Script and scene/shot structure, sources, narration and caption/accessibility plan |
| `formats/ebooks.md` | Chapter/manuscript structure, reader outcomes, sources and export review questions |
| `formats/audiobooks.md` | Narration script, pronunciation/voice-permission questions, chapter map and audio review |
| `formats/video-books.md` | Proposed chapter-to-scene adaptation, narration, visuals, captions and adaptation rights |
| Six files in `distribution/` | Separate account, artifact, copy, attribution, permission, preview and release questions for each intended destination |
| Three files in `ai-workspaces/` | Proposed coordination, production and review handoff briefs; none is sent |
| `review-checklist.md` | Independent source, rights, factual, accessibility, asset and release review questions |
| `studio-config.json` | The exact public config bytes resolved for the run |
| `business-context.json` | Optional projection metadata and exact matching studio labels; no full business projection or private source |
| `manifest.json` | Required file inventory, hashes, byte counts, provenance and explicit execution limits |

“Video Books” remains a distinct format. The chapter-based narrated adaptation
structure is a proposed treatment for the owner to refine. This packet contains
Markdown and JSON templates; it contains no recorded video, PDF/EPUB book, audio
recording, voice clone or synchronized chapter video.

Copy templates into a separate working directory before filling them in. Editing
an original packet invalidates its evidence. Finished scripts, exports and media
belong in separately reviewed production artifacts with their own source and
rights records; editing template status flags cannot promote this packet.

## Manifest and fixed configuration

`config/creative-studio.public.json` has:

| Field | Value |
|---|---|
| Schema | `jarvis.creative-studio.v1` |
| ID | `evolutionary-evolutions-creative-creations-studios` |
| Revision | `repository-1` |
| Declaration | `owner_declared_intended_use` |
| Connection qualification | `not_asserted_by_this_context` |
| Hash | SHA-256 of the exact config bytes |

The loader reads only that repository-relative file. Unknown identities,
revisions, declaration changes, extra fields, duplicate JSON keys, malformed
input and symlinked config paths fail. The loaded byte snapshot is immutable.
Changing the approved public declaration requires an explicit configuration and
validator update; no runtime input can override it.

The manifest uses `jarvis.creative-studio-packet.v1` and records:

- Run ID and observation time.
- Workflow name/hash and Prompt #11 ID/revision/hash.
- Studio config identity/hash and optional business-projection metadata.
- Raw request SHA-256 and byte count, without copying its text.
- All 19 payload paths, media types, byte counts, hashes and template status.
- Missing intake fields and explicit zero-call/no-render/no-publish/no-send/
  no-approval/no-shared-sync assertions.

The verifier checks the exact expected inventory, file contents, byte counts,
hashes, config snapshot identity and the supported profile ID/revision/hash
shape. It reconstructs the fixed templates as well as checking their hashes, so
rewriting a template to claim “published” and updating its adjacent hash does not
make that template acceptable. Unexpected files, missing files, duplicate or
escaping manifest paths, symlinks and unsupported readiness assertions fail.

Profile metadata identifies the instruction source recorded by the runner; this
local operation does not execute an AI step or independently retrieve that
profile's historical contents. Source checkout and GitHub audit evidence provide
the corresponding code/profile context. The optional business hash identifies
the sanitized projection; its full contents are not embedded in this packet.

Keep the returned manifest hash independently. Colocated hashes are local
consistency evidence, not a signature of authorship or a trusted timestamp.
A fully replaced self-consistent record of different run/input/profile metadata
requires comparison with that external anchor. The runner performs the relevant
cache-provenance comparison before reuse.

## Enforced bounds and remaining work

The generator accepts at most 16 KiB of UTF-8 request text and independently
rejects credentials recognized by the existing sensitive-data scanner. It does
so even when invoked directly, outside the workflow runner. This recognition is
not a universal detector for all private information. The packet stores only the
request hash/count and the small allowed context record.

Configuration is limited to 16 KiB. The packet has exactly 20 files, at most
64 KiB per file and 512 KiB in total. Existing destinations are never overwritten.
The manifest is written last: a failed partial write does not produce a
verifiable success packet. The verifier refuses symlinked directories/files and
does not follow network locations.

Before substantive production, supply the topic/campaign, audience, objective,
source assets and permissions, lengths/language, selected purposes, actual
destination accounts, independent reviewer and release scope. Existing
[product-factory and unified workflows](PROMPT11_WORKFLOW_PROFILE.md) can later
produce attributable candidate work through their existing configured-provider
and external-call gates. This template workflow adds no call budget or provider
activation authority.

For affiliate campaigns, use the separate
[exact-route review registry](REFERRAL_CROSS_PLATFORM_INTEGRATION.md); these
templates do not validate program membership, referral credit or compensation.
For Hostinger, follow the
[proposed account/site mapping](PROPOSED_HOSTINGER_WORKFLOW_MAPPINGS.md). The
current product, domain/DNS, permissions, backup and staging still need actual
verification before a site change.

## Local verification

The module tests use synthetic local records and intercepted network entry
points. They cover exact declarations, optional-context agreement, private-source
and raw-request exclusion, file/budget limits, overwrite/symlink/path refusal,
missing/tampered evidence, unsupported assertions, partial writes and the verifier
CLI:

```sh
PYTHONPATH=src python3 -m unittest tests.test_creative_studio -v
```

Runner integration and catalog coverage are verified separately. Passing these
tests proves the local template/evidence behavior, not completed media, live
platform connections or independent creative approval.
