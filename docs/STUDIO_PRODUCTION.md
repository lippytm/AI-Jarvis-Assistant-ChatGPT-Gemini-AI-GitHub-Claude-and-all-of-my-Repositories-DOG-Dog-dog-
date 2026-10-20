# Local studio production plans

The production planner packages a filled brief and supplied local text drafts into an immutable review packet. It checks source bytes, declared dependencies and recorded review findings, then reports which draft formats are prepared for review and which remain blocked. Every packet retains `release_status: release_blocked`.

Start with the substantive [AI Jarvis workforce pilot](../examples/studio-workforce-pilot/README.md). It supplies a chapter, narration, short-video script and Video Book storyboard. This teaching companion does not establish completion of the earlier full-book target or incorporate unseen manuscript editions.

The implementation is [studio_production.py](../src/jarvis/studio_production.py). Its local-file, lineage and tamper regressions are in [test_studio_production.py](../tests/test_studio_production.py).

## Commands and exit status

Run from the repository root with Python 3.11 or newer. The build command resolves the two fixed repository configuration files relative to the current working directory.

```sh
studio_run="$(mktemp -d /tmp/jarvis-production.XXXXXX)"

PYTHONPATH=src python3 -m jarvis studio-plan \
  examples/studio-workforce-pilot/production-brief.json \
  --output "$studio_run/packet" --json

PYTHONPATH=src python3 -m jarvis verify-studio-plan \
  "$studio_run/packet" --json
```

With the project installed, the equivalent commands are:

```sh
jarvis studio-plan BRIEF --output FRESH_DIR --json
jarvis verify-studio-plan DIR --json
```

`FRESH_DIR` must not already exist. An existing parent directory is allowed. Keep each completed packet immutable; build a separate packet for every revised source snapshot.

| Command | Exit code | Meaning |
|---|---:|---|
| `studio-plan` | 0 | A valid packet was written and all declared draft evidence needed by the plan is `prepared_for_review` |
| `studio-plan` | 1 | A valid packet was written with missing, stale or blocked draft evidence; inspect the JSON `blockers` |
| `studio-plan` | 2 | The input, configuration, paths or output operation were invalid |
| `verify-studio-plan` | 0 | The archived packet is internally consistent, including a packet whose production status is blocked |
| `verify-studio-plan` | 2 | Packet inventory, bytes, identities, derived states or scope assertions are invalid |

Verification exit code 0 is an integrity result. It is not a release decision. Check `status` and `release_status` separately.

Both command branches run before `ControlTower` construction. They do not initialize a task ledger, load a provider session, require a provider key or create a local MemPalace receipt. They do not activate an account connection.

## Python API

```python
from pathlib import Path
from jarvis.studio_production import (
    StudioProductionError,
    build_production_plan,
    verify_production_plan,
)

result = build_production_plan(
    root=Path.cwd(),
    brief_path=Path("examples/studio-workforce-pilot/production-brief.json"),
    output_dir=Path("/tmp/a-new-production-packet"),
)
verified = verify_production_plan(Path(result["package_path"]))
```

Choose a fresh output path before using that example. Validation and file failures raise `StudioProductionError`, a `ValueError` subclass. A valid blocked plan is returned as a result; it is not a validation exception.

The result includes `package_path`, `manifest_sha256`, `file_count`, project identity, exact brief hash, profile/configuration metadata, `dependency_order`, asset and format states, blockers, release blockers, execution declarations and evidence scope. The same complete derived plan is saved as `production-plan.json`.

## Strict brief contract

The input must be a UTF-8 JSON object with schema `jarvis.studio-production-brief.v1`. Every root field below is required. Unknown fields, duplicate JSON keys, nonfinite numbers, invalid types and unsupported identities are rejected. The parser also checks decoded strings for recognized credential patterns, including escaped strings.

| Root field | Accepted value |
|---|---|
| `schema` | Exactly `jarvis.studio-production-brief.v1` |
| `project_id` | 1–80 characters; first character ASCII letter or digit; remaining characters letters, digits, `.`, `_` or `-` |
| `revision` | The same identifier shape; use a distinct revision for a revised working brief |
| `title` | Nonblank UTF-8 text, up to 512 bytes |
| `objective` | Nonblank UTF-8 text, up to 4,096 bytes; state the assignment and its observable done criteria |
| `audience` | Nonblank UTF-8 text, up to 2,048 bytes |
| `language` | A 2–3 letter primary tag, optionally followed by 2–8 character alphanumeric subtags; at most 40 characters |
| `purposes` | One or more distinct exact labels from the purpose list below |
| `formats` | One or more distinct exact labels from the format table below |
| `source_declaration` | Exactly `provided_local_drafts` |
| `assets` | Zero to four asset records, at most one per supported kind |
| `reviews` | Zero to 32 recorded review assertions |

Use `"language": "en"` or a supported shape such as `"en-US"`. The word `"English"` is not accepted. This is tag-shape validation, not certification that the source text is written in the declared language.

The exact purpose labels are `Ad Copy`, `Affiliate Program Marketing`, `Educational`, `Entertainment` and `Business of Businesses Systems of Systems`.

| Exact format label | Required asset kind | What the input establishes |
|---|---|---|
| `Videos` | `video_script` | A local text script |
| `eBooks` | `ebook_manuscript` | A local text manuscript |
| `Audiobooks` | `narration_script` | A local narration script |
| `Video Books` | `video_book_storyboard` | A local storyboard or chapter adaptation |

The contract checks that the brief is populated and structurally valid. It cannot determine whether the objective is useful, a manuscript is accurate, or a script meets its audience's needs. Those remain content-review work.

### Assets and parent references

Each asset has exactly these fields:

```json
{
  "id": "narration",
  "kind": "narration_script",
  "path": "assets/narration.md",
  "sha256": "<64 lowercase hexadecimal characters>",
  "parents": [
    {
      "asset_id": "chapter",
      "sha256": "<64 lowercase hexadecimal characters>"
    }
  ]
}
```

The angle-bracket hash values above describe the schema and are not valid input. The [filled pilot brief](../examples/studio-workforce-pilot/production-brief.json) contains real hashes.

Asset IDs use the identifier shape above. IDs, paths and kinds must each be unique. A path is relative to the brief's directory, uses forward slashes, ends in `.md` or `.txt`, and has at most 240 characters. Each component uses the identifier character rules. Absolute paths, URLs, backslashes, empty components, `.`, `..` and symlink paths are refused.

Sources must be nonblank UTF-8 regular files. Binary/control characters other than line breaks and tabs are refused, as are recognized credentials. Missing files are represented as missing evidence; the planner does not invent replacement text or an empty placeholder file.

A parent entry contains exactly `asset_id` and `sha256`. It must name another declared asset. Duplicate parents, self-references, unknown parents and cycles are rejected. Each asset can name up to three parents. An empty list means no dependency was declared; the planner does not infer one.

The planner reads each supplied file's actual bytes and computes its observed SHA-256. It compares those bytes with the asset's expected `sha256`. Every child parent pin must also match both the parent's declared hash and its observed hash. An available parent that is itself blocked cannot make its descendants prepared for review.

The source snapshot is a sequence of individual bounded file reads. It is not an atomic snapshot of an entire working directory. If another process is changing sources concurrently, use a stable source copy or versioned checkout before building.

### Recorded reviews

A review contains exactly these fields:

```json
{
  "asset_id": "chapter",
  "asset_sha256": "<64 lowercase hexadecimal characters>",
  "reviewer": "Recorded reviewer name",
  "result": "changes_requested",
  "note": "Recorded findings and the unresolved correction."
}
```

`asset_id` must name a declared asset. `result` is exactly `pass`, `changes_requested` or `not_reviewed`. Reviewer and note must be nonblank text, limited to 128 and 2,048 UTF-8 bytes respectively. Duplicate or contradictory records for the same asset/hash/reviewer combination are rejected.

Every record is marked `recorded_untrusted`. The tool does not authenticate the reviewer, establish independence or check whether the described review occurred.

- A `changes_requested` assertion matching the observed source hash blocks the asset and its descendants.
- A stale assertion is flagged with `hash_matches_observed: false` and a warning. It cannot clear a source, dependency or current review blocker.
- A recorded `pass` never grants approval, proves source rights or removes the unconditional release blockers.

Adding another reviewer's `pass` does not cancel a current change request. Resolve the underlying issue, retain the old packet, and supply a revised source/brief and accurate review record. Do not invent reviewer identities or a completed review to make a result pass.

## Derived states

| Field and value | Meaning |
|---|---|
| Asset `source_status: present` | Actual source bytes match the declared source hash |
| Asset `source_status: missing` | The declared local file was absent |
| Asset `source_status: stale` | A local text file was read, but its actual hash differs from the declaration |
| Asset/format `status: missing_source` | The required source is absent, or that requested format has no declared asset |
| Asset/format `status: stale_source` | The asset's own bytes differ from its declared hash |
| Asset/format `status: blocked` | Present source bytes have an unresolved parent or applicable recorded-review blocker |
| Asset/format `status: prepared_for_review` | Source bytes and declared dependencies are current and no applicable change request blocks them |
| Plan `status: blocked` | At least one declared asset or requested format is blocked, stale or missing |
| Plan `status: prepared_for_review` | Every declared asset and requested format meets the local evidence checks |
| `release_status: release_blocked` | Always; this engine has no release-approval or publishing capability |

A draft with current bytes may still have `review_status: not_reviewed`. That is consistent with being prepared *for* review. The tool does not claim editorial correctness, a rendered deliverable, a complete full-length book, an audience result or an authorized release.

## Packet contents and exact identities

A complete four-asset packet has **13 files**:

| Files | Count | Role |
|---|---:|---|
| `brief.json` | 1 | Exact input brief bytes |
| `sources/<asset-id>.md` or `.txt` | 4 | Exact observed bytes of each available source; the extension is preserved |
| `config/creative-studio.public.json` | 1 | Exact fixed studio configuration snapshot |
| `config/prompt-11-profile.json` | 1 | Exact fixed Prompt #11 profile snapshot |
| `production-plan.json` | 1 | Reproducible derived source, dependency, review and format states |
| `ai-workspaces/chatgpt-business.md` | 1 | Proposed coordination handoff, stored locally |
| `ai-workspaces/gemini-ai.md` | 1 | Proposed adaptation handoff, stored locally |
| `ai-workspaces/claude.md` | 1 | Proposed review handoff, stored locally |
| `README.md` | 1 | Packet scope and use instructions |
| `manifest.json` | 1 | Observation time, identities, exact inventory, byte counts and SHA-256 values |

There are nine fixed files plus one file per actually available source. A missing source has no copied file, so a blocked packet may contain fewer than 13 files. Additional files in the brief's working directory are not swept into the packet. For example, the pilot's distribution drafts and economics assumptions are separate artifacts.

The studio identity is `evolutionary-evolutions-creative-creations-studios`, revision `repository-1`. Its fixed declaration names The Evolutionary Evolutions Creative Creations Studios of Intergalactic Corporate Services LLC. Prompt #11 uses ID `P-011-E6C-001`, revision `repository-1`. Both identities and exact byte hashes are included in plans and results; unknown identities or revisions fail closed.

There is no brief field for changing either configuration path or loading a remote profile. The three handoff files include the pinned profile's actual shared guidance. This is a local proposed use of guidance, not evidence that any AI workspace received it or complied with it. See [the Prompt #11 workflow profile](PROMPT11_WORKFLOW_PROFILE.md) for that distinction.

## Verification and the external manifest anchor

`verify-studio-plan` stays within the packet. It validates the brief again, checks the full allowed inventory and regular-file paths, verifies fixed identities, reconstructs source/dependency/review states from the copied source bytes, and reconstructs the expected plan and handoff contents. It then checks the manifest against those results.

Changing a source or approval claim and updating only its adjacent manifest hash cannot preserve a valid prepared-for-review packet. Derived states and fixed scope declarations must agree with the actual archived inputs. Unknown files, omitted required files, duplicated inventory entries, unsafe paths, changed guidance identities and unsupported execution claims are rejected.

The returned `manifest_sha256` is an **external comparison anchor only when retained separately**. Save it with the source revision, build record or review record used to identify the packet. Later, compare the verifier's returned hash to that independently retained value.

A colocated hash file is not a signature. A person who rewrites the complete brief, sources, plan and manifest into a different internally consistent packet can obtain a different valid packet. Internal verification alone cannot prove it is the earlier packet you intended. It also does not reopen the original source directory to detect later edits, authenticate source authorship, establish rights, or validate a human approval.

## Source drift exercise

This exercise uses a temporary copy of the public pilot and three fresh packet directories. It does not modify checked-in example files. Run it from the repository root:

```sh
PYTHONPATH=src python3 - <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile

from jarvis.studio_production import build_production_plan

repo = Path.cwd()
exercise = Path(tempfile.mkdtemp(prefix="jarvis-source-drift-"))
working = exercise / "working"
shutil.copytree(repo / "examples/studio-workforce-pilot", working)
brief_path = working / "production-brief.json"

baseline = build_production_plan(repo, brief_path, exercise / "01-baseline")
assert baseline["status"] == "prepared_for_review"

brief = json.loads(brief_path.read_text(encoding="utf-8"))
chapter = next(asset for asset in brief["assets"] if asset["kind"] == "ebook_manuscript")
chapter_path = working / chapter["path"]
chapter_path.write_bytes(
    chapter_path.read_bytes()
    + b"\nExercise edit: this source now includes an additional review note.\n"
)

changed = build_production_plan(repo, brief_path, exercise / "02-source-changed")
assert changed["status"] == "blocked"
assert next(asset for asset in changed["assets"] if asset["id"] == chapter["id"])["status"] == "stale_source"

# Pin only the changed source's own bytes. Leave every child pin unchanged
# so the remaining adaptation review work stays visible.
chapter["sha256"] = sha256(chapter_path.read_bytes()).hexdigest()
brief["revision"] = "drift-source-pin-only"
brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

parent_drift = build_production_plan(repo, brief_path, exercise / "03-parent-pins-stale")
assert parent_drift["status"] == "blocked"
assert any("parent_" in blocker["code"] for blocker in parent_drift["blockers"])

print(json.dumps({
    "exercise_directory": str(exercise),
    "working_brief": str(brief_path),
    "baseline_status": baseline["status"],
    "changed_source_status": changed["status"],
    "parent_drift_status": parent_drift["status"],
    "parent_drift_blockers": parent_drift["blockers"],
    "release_status": parent_drift["release_status"],
}, indent=2))
PY
```

The first changed packet identifies the source mismatch. The next packet shows that updating the manuscript's own hash is insufficient: its adaptations still name the previous parent bytes.

To repair a real project:

1. Preserve the earlier packet and its separately recorded manifest hash.
2. Compare the changed manuscript with the exact prior source. Review every direct and indirect adaptation in dependency order.
3. Edit the narration, video script and storyboard where needed. Decide whether each remaining adaptation still accurately uses its changed parents; a hash calculator cannot make that editorial decision.
4. Compute each changed file's SHA-256 from its exact saved bytes, for example `sha256(Path("assets/narration.md").read_bytes()).hexdigest()` in Python from the working directory. Update that asset's own `sha256`.
5. Update each reviewed child's parent pins to the exact current hashes it actually uses. If narration changes, check the storyboard's narration pin as well as its manuscript pin. Keep unrelated parent lists unchanged.
6. Record a new brief revision and accurate review assertions. Preserve historical review evidence in the old packet; stale assertions in a new brief remain warnings and never become fresh approvals.
7. Build into a new output directory, inspect all blockers, then verify the resulting packet and retain its manifest hash separately.

Do not repair a packet by editing its archived files. Do not update every parent hash mechanically before reviewing the adaptations. Current pins establish byte consistency; they cannot establish semantic agreement or rights.

## Bounds and execution scope

| Limit | Value |
|---|---:|
| Brief | 64 KiB |
| Declared source assets | Four, at most one per kind |
| Each source asset | 256 KiB |
| Recorded reviews | 32 |
| Prompt profile snapshot | 64 KiB |
| Fixed studio configuration | 16 KiB |
| Any generated/copied packet file | 256 KiB |
| Entire packet including manifest | 2 MiB |
| Parsed JSON nesting depth / visited nodes | 12 / 4,096 |

The engine scans for the repository's recognized credential patterns. That is not a general guarantee that arbitrary supplied text contains no personal or confidential information. Select intended public or appropriately scoped source drafts before packaging them; this API has no private-record projection or account-data import.

Every result and manifest uses these execution declarations:

```json
{
  "provider_calls": 0,
  "media_rendered": false,
  "published": false,
  "external_handoff_sent": false,
  "approval_granted": false,
  "shared_memory_sync": false
}
```

Source authorship and rights remain unverified, independent content QA is not established, and destination identity/permissions and exact release approval remain unresolved. No review record can switch these declarations on. A finished eBook export, recording, rendered video or synchronized Video Book requires separate production and review work.

## Relationship to the existing template workflow

The existing [creative studio workflow](CREATIVE_STUDIO_WORKFLOW.md) always produces fixed `intake_required`, `template_only` structures. Its shipping `studio_package` step does not interpret a substantive brief or render media.

This production CLI accepts a filled brief and actual local draft assets, copies their bytes, and derives evidence-based review states. It is a separate local command surface; it does not add a catalog workflow, enable the old approval step to resume itself, or connect ChatGPT Business, Gemini AI, Claude, Hostinger or social accounts. The three named AI workspaces remain proposed handoff destinations.

Use the [pilot README](../examples/studio-workforce-pilot/README.md) for the supplied teaching project and the [studio economics contract](STUDIO_ECONOMICS.md) for its separate hypothetical cost scenarios.
