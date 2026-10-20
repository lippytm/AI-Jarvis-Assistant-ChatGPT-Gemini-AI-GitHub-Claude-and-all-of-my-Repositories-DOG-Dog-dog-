"""Create and verify bounded local studio templates; no media or account calls."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

from .business_context import BusinessContext, PROJECTION_SCHEMA, VERIFICATION_STATUS
from .models import utc_now
from .prompt_profiles import PROFILE_ID, PROFILE_REVISION
from .safety import find_sensitive


CONFIG_PATH = Path("config/creative-studio.public.json")
CONFIG_SCHEMA = "jarvis.creative-studio.v1"
STUDIO_ID = "evolutionary-evolutions-creative-creations-studios"
REVISION = "repository-1"
PACKET_SCHEMA = "jarvis.creative-studio-packet.v1"
MAX_CONFIG_BYTES = 16 * 1024
MAX_INPUT_BYTES = 16 * 1024
MAX_FILE_BYTES = 64 * 1024
MAX_PACKET_BYTES = 512 * 1024
HEX = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
WORKFLOW_NAME = re.compile(r"[A-Za-z0-9_-]{1,128}")
BRAND = "The Evolutionary Evolutions Creative Creations Studios of Intergalactic Corporate Services LLC"
FORMATS = ("Videos", "eBooks", "Audiobooks", "Video Books")
PURPOSES = ("Ad Copy", "Affiliate Program Marketing", "Educational", "Entertainment",
            "Business of Businesses Systems of Systems")
CHANNELS = ("Facebook", "LinkedIn", "Instagram", "Threads", "SubStack", "Hostinger.com")
WORKSPACES = ("ChatGPT Business", "Gemini AI", "Claude")
DECLARATION_KEYS = ("brand_name", "formats", "purposes",
                    "intended_distribution_channels", "intended_ai_workspaces",
                    "declaration_status", "connection_status")
EXECUTION = {"provider_calls": 0, "media_rendered": False, "published": False,
             "external_handoff_sent": False, "approval_granted": False,
             "shared_memory_sync": False}
MISSING_INPUTS = ("topic_or_campaign", "audience", "objective_and_done_criteria",
                  "source_assets_and_rights", "target_lengths_and_language",
                  "selected_purposes", "destination_accounts_and_permissions",
                  "independent_reviewer", "release_scope")
FORMAT_PATHS = ("formats/videos.md", "formats/ebooks.md", "formats/audiobooks.md",
                "formats/video-books.md")
CHANNEL_PATHS = ("distribution/facebook.md", "distribution/linkedin.md",
                 "distribution/instagram.md", "distribution/threads.md",
                 "distribution/substack.md", "distribution/hostinger.md")
WORKSPACE_PATHS = ("ai-workspaces/chatgpt-business.md", "ai-workspaces/gemini-ai.md",
                   "ai-workspaces/claude.md")
PAYLOAD_PATHS = frozenset(("README.md", "intake.json", "intake-and-rights.md",
                           "review-checklist.md", "studio-config.json",
                           "business-context.json", *FORMAT_PATHS, *CHANNEL_PATHS,
                           *WORKSPACE_PATHS))
REQUIRED_PATHS = PAYLOAD_PATHS | {"manifest.json"}
REQUIRED_DIRS = frozenset(("formats", "distribution", "ai-workspaces"))


class StudioError(ValueError):
    """A static, public-safe studio validation or local-file error."""


def _invalid(message: str = "Invalid creative studio packet") -> StudioError:
    return StudioError(message)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _invalid()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise _invalid()


def _json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise _invalid() from None
    if not isinstance(value, dict):
        raise _invalid()
    return value


def _no_symlink(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            if stat.S_ISLNK(part.lstat().st_mode):
                raise _invalid("Studio paths must not contain symlinks")
        except FileNotFoundError:
            continue


def _read_regular(path: Path, limit: int = MAX_FILE_BYTES) -> bytes:
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise _invalid()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise _invalid()
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise _invalid()
        return raw
    except OSError:
        raise _invalid("Cannot read studio evidence file") from None


def _config_value() -> dict[str, Any]:
    return {"schema": CONFIG_SCHEMA, "id": STUDIO_ID, "revision": REVISION,
            "brand_name": BRAND, "operator_legal_name": "Intergalactic Corporate Services LLC",
            "formats": list(FORMATS), "purposes": list(PURPOSES),
            "intended_distribution_channels": list(CHANNELS),
            "intended_ai_workspaces": list(WORKSPACES),
            "declaration_status": "owner_declared_intended_use",
            "connection_status": "not_asserted_by_this_context"}


@dataclass(frozen=True)
class StudioConfig:
    """Pin the exact reviewed bytes; returned objects are independent copies."""

    sha256: str
    _raw: bytes

    def as_dict(self) -> dict[str, Any]:
        return _json(self._raw)

    def metadata(self) -> dict[str, str]:
        return {"schema": CONFIG_SCHEMA, "id": STUDIO_ID,
                "revision": REVISION, "sha256": self.sha256}


def _checked_config(raw: bytes) -> StudioConfig:
    if len(raw) > MAX_CONFIG_BYTES or _json(raw) != _config_value():
        raise _invalid("Unsupported creative studio configuration")
    return StudioConfig(sha256(raw).hexdigest(), raw)


def load_studio_config(root: Path) -> StudioConfig:
    """Read only the fixed repository-relative configuration; no URL overrides."""
    try:
        path = Path(root).absolute() / CONFIG_PATH
        _no_symlink(path)
        return _checked_config(_read_regular(path, MAX_CONFIG_BYTES))
    except (OSError, TypeError):
        raise _invalid("Cannot load creative studio configuration") from None


def _identifier(value: Any) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise _invalid()


def _hash(value: Any) -> None:
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise _invalid()


def _profile(value: Any) -> None:
    if (not isinstance(value, dict) or set(value) != {"id", "revision", "sha256"}
            or value["id"] != PROFILE_ID or value["revision"] != PROFILE_REVISION):
        raise _invalid("Unsupported studio prompt profile")
    _hash(value["sha256"])


def _workflow(value: Any) -> None:
    if (not isinstance(value, dict) or set(value) != {"name", "sha256"}
            or not isinstance(value["name"], str) or not WORKFLOW_NAME.fullmatch(value["name"])):
        raise _invalid("Invalid studio workflow identity")
    _hash(value["sha256"])


def _business_metadata(value: Any) -> None:
    if (not isinstance(value, dict)
            or set(value) != {"schema", "projection_id", "record_id", "sha256", "verification_status"}
            or value["schema"] != PROJECTION_SCHEMA
            or value["verification_status"] != VERIFICATION_STATUS):
        raise _invalid("Invalid studio business context")
    _identifier(value["record_id"])
    if value["projection_id"] != "owner-business-context-v1:" + value["record_id"]:
        raise _invalid("Invalid studio business context")
    _hash(value["sha256"])
    if find_sensitive(json.dumps(value)):
        raise _invalid("Studio context contains recognized credentials")


def _context_record(config: StudioConfig, context: BusinessContext | None) -> dict[str, Any]:
    if context is None:
        return {"supplied": False, "metadata": None, "creative_studio": None}
    if not isinstance(context, BusinessContext):
        raise _invalid("Expected a sanitized business context")
    metadata = context.metadata()
    _business_metadata(metadata)
    projection = context.as_dict()
    declaration = projection.get("creative_studio")
    expected = {key: config.as_dict()[key] for key in DECLARATION_KEYS}
    if "creative_studio" in projection and declaration != expected:
        raise _invalid("Business studio declaration conflicts with fixed configuration")
    return {"supplied": True, "metadata": dict(metadata),
            "creative_studio": expected if declaration is not None else None}


def validate_business_context(config: StudioConfig, business_context: BusinessContext | None) -> None:
    """Check optional studio agreement without writing a packet or opening a source."""
    if not isinstance(config, StudioConfig) or _checked_config(config._raw).sha256 != config.sha256:
        raise _invalid("Invalid studio configuration snapshot")
    _context_record(config, business_context)


def _document(title: str, body: str) -> bytes:
    return (f"# {title}\n\n{BRAND}\n\n"
            "Template only. Intake and independent review are required. "
            "No media rendering, external handoff or publication was performed.\n\n"
            + body.strip() + "\n").encode("utf-8")


def _intake(input_sha256: str, input_bytes: int) -> dict[str, Any]:
    return {"schema": "jarvis.creative-studio-intake.v1", "status": "intake_required",
            "template_only": True, "request": {"sha256": input_sha256, "bytes": input_bytes},
            "missing_inputs": list(MISSING_INPUTS),
            "brief": {field: None for field in MISSING_INPUTS},
            "source_assets": [], "rights_review": "unreviewed",
            "note": "Raw request text is not copied. Complete a separate working brief; do not infer a topic from these templates."}


def _payloads(config: StudioConfig, input_sha256: str, input_bytes: int,
              context_record: dict[str, Any]) -> dict[str, bytes]:
    files = {
        "studio-config.json": config._raw,
        "business-context.json": _json_bytes(context_record),
        "intake.json": _json_bytes(_intake(input_sha256, input_bytes)),
        "README.md": _document("Studio production packet", """
## How to use this packet

1. Preserve this original packet and its manifest hash as intake evidence.
2. Copy the relevant templates into a separate working directory.
3. Supply a topic/campaign, audience, objective, sources, rights and target lengths.
4. Produce and check each requested edition before comparing or combining editions.
5. Record corrections, evidence and unresolved questions with a separate reviewer.
6. Prepare a specific destination/account handoff and seek its release decision.

This packet defines four formats and six intended distribution destinations.
The three AI-workspace briefs are local files, not installed connections.
Editing an original template invalidates this packet's evidence. This version
always remains intake_required, even when the input request contains a topic.
It does not interpret the raw request or generate finished creative content.

## Files

- intake.json and intake-and-rights.md: the working questions and missing assets.
- formats/: Videos, eBooks, Audiobooks and Video Books structures.
- distribution/: separate review briefs for the six named destinations.
- ai-workspaces/: proposed, manually reviewable production/review roles.
- review-checklist.md: source, quality and release acceptance questions.
- studio-config.json: the exact fixed studio declaration used by this run.
- business-context.json: optional projection metadata and matching studio labels.
- manifest.json: required inventory, byte counts, hashes and scope declarations.
"""),
        "intake-and-rights.md": _document("Intake and source rights", """
## Complete the working brief

Topic or campaign:
Audience and intended benefit:
Selected purpose(s):
Objective and observable done criteria:
Language and accessibility needs:
Length for each selected format:
Tone, narrator/presenter approach and visual direction:
Source artifacts and their revisions:
Target destination accounts and permitted actions:
Independent reviewer:
Release scope, expiry and rollback/contact owner:

## Record source evidence

| Source/asset | Owner or license | Permitted use | Evidence reference | Unresolved issue |
|---|---|---|---|---|
| To be supplied | Unverified | Unverified | Missing | Review required |

Identify permission for music, images, footage, quotations, voice and likeness.
Separate sourced factual claims from hypotheses and fictional material. Do not
invent testimonials, partner approval, funding eligibility or commission rates.
For affiliate material, preserve exact approved routing and review the applicable
terms, attribution and plain-language compensation disclosure before release.
Do not include tax identifiers, account secrets, applications or customer records.
"""),
        "review-checklist.md": _document("Independent review and approved handoff", """
## Evidence and quality

- Does the completed brief state its audience, purpose and done criteria?
- Are facts sourced, quotations checked and unresolved claims labeled?
- Are asset, music, voice and likeness permissions documented?
- Are independently produced provider editions retained before comparison?
- Has a separate reviewer recorded findings and dispositions?
- Do video, narration, chapter references and captions agree where relevant?
- Have accessibility, readability, pronunciation and playback checks actually run?

## Destination review

- Is the intended account/page/site identified and its access verified?
- Are the current destination specifications checked for the actual asset?
- Are tracking links and affiliate claims verified without silent URL changes?
- Does the owner decision name the exact assets, hashes and release action?
- Is a reversible staging/rollback plan available where needed?

Record each item as unreviewed, passed with evidence, or blocked with a reason.
This checklist grants no approval and does not mark any check as passed.
The workflow approval request stops downstream execution; it does not send these
files, resume a provider job or publish an approved artifact automatically.
"""),
    }
    format_bodies = (
        """## Videos working structure

Working title:
Audience, purpose and desired action:
Target duration and destination:

| Scene | Purpose | Visual/shot | Narration/dialogue | Source/rights | Caption/accessibility notes |
|---|---|---|---|---|---|
| Opening | To be decided | Asset required | Draft required | Unverified | Draft required |
| Development | To be decided | Asset required | Draft required | Unverified | Draft required |
| Ending | To be decided | Asset required | Draft required | Unverified | Draft required |

Prepare the full script, shot list, asset list, transcript and caption working
file only after the brief is complete. Confirm recording/render settings for the
chosen destination rather than treating this template as a rendered video.
""",
        """## eBooks working structure

Working title and reader promise:
Audience and selected purpose:
Target length, language and desired edition/export:

| Section/chapter | Reader outcome | Outline/manuscript | Sources | Review state |
|---|---|---|---|---|
| Introduction | To be decided | Draft required | Missing | Unreviewed |
| Core chapters | To be decided | Draft required | Missing | Unreviewed |
| Closing/resources | To be decided | Draft required | Missing | Unreviewed |

Plan front matter, a navigable contents list, chapter hierarchy, glossary,
references and image descriptions as appropriate. Review facts, links, layout
and accessibility on the actual exported edition. No PDF, EPUB or finished
manuscript is generated by this packet.
""",
        """## Audiobooks working structure

Source manuscript and edition:
Narrator/voice choice and permission:
Target language, chapter length and delivery format:

| Chapter | Narration text | Pronunciation/cues | Source permission | Audio QA |
|---|---|---|---|---|
| Opening | Script required | To be supplied | Unverified | Not recorded |
| Chapters | Script required | To be supplied | Unverified | Not recorded |
| Closing | Script required | To be supplied | Unverified | Not recorded |

Prepare a narration-ready script, pronunciation list, chapter map and corrections
log. Verify permission before voice synthesis or recording. Listen to actual
audio for missing text, pronunciation, noise, clipping and chapter alignment.
No recording, voice clone, synthesized speech or mastered audio is produced here.
""",
        """## Video Books working structure

Source book/chapters and edition:
Proposed treatment: chapter-based narrated video adaptation, for owner review.
Audience, target chapter lengths and visual approach:

| Book chapter | Video sequence | Narration | Visual assets | Captions/transcript | Adaptation rights |
|---|---|---|---|---|---|
| To be supplied | Storyboard required | Script required | Missing | Draft required | Unverified |

Keep this format distinct from a short promotional video. Map every selected
chapter to its scenes and narration, preserve references and record adaptations.
Check continuity between source text, narration, visual timing and accessibility
materials on the actual media. No synchronized or rendered Video Book exists yet.
""",
    )
    for label, path, body in zip(FORMATS, FORMAT_PATHS, format_bodies):
        files[path] = _document(label, body)
    for label, path in zip(CHANNELS, CHANNEL_PATHS):
        site_note = (
            "\nFor the existing Hostinger plan, verify the actual product, domain/DNS, "
            "pages/forms/scripts/redirects, backup and staging before a site write. "
            "The /funding-readiness gateway remains a separate reviewed funding route.\n"
            if label == "Hostinger.com" else "")
        files[path] = _document(f"{label} distribution review", f"""
Intended destination: {label}. Account/page/site identity: not supplied.
Connection and publishing permission: unverified.

Working copy or description:
Selected artifact(s), version and hash:
Audience, purpose and proposed call to action:
Exact reviewed link and attribution evidence:
Asset/caption/accessibility requirements for this destination:
Source and rights evidence:
Affiliate disclosure or other copy-review questions:
Proposed timing and approval owner:
Staging/preview and rollback approach:

Review the destination's current specifications for the chosen content. This
file contains no assumed account ID, uploaded asset, scheduled post or approved
marketing claim. A named destination is not evidence of an installed publisher.
{site_note}""")
    roles = (
        "Proposed coordination role: reconcile the brief, source evidence and reviewer findings into an owner-review packet.",
        "Proposed production role: develop an independently attributable outline or format adaptation from approved sources.",
        "Proposed review role: challenge factual support, rights, coherence, feasibility and missing acceptance evidence.",
    )
    for label, path, role in zip(WORKSPACES, WORKSPACE_PATHS, roles):
        files[path] = _document(f"{label} workspace handoff draft", f"""
Intended workspace: {label}. Workspace/project/account identity: not supplied.
Connection status: not asserted by this template.

{role}

Task and selected format:
Approved source bundle and source hashes:
Current workflow/profile identity and optional business projection hash:
Permitted tools, data, calls and budget:
Expected output and done criteria:
Independent reviewer and unresolved disagreements:
Evidence returned and next authorized action:

Supply this draft only through a separately authorized handoff. API-provider
configuration does not prove access to conversations or projects in this named
workspace. Preserve independently produced and checked editions when comparing
providers; do not add calls or claim completed review from these role labels.
""")
    return files


def _file_records(files: dict[str, bytes]) -> list[dict[str, Any]]:
    return [{"path": path, "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
             "media_type": "application/json" if path.endswith(".json") else "text/markdown",
             "status": "template_only"} for path, raw in sorted(files.items())]


def build_packet(config: StudioConfig, output_dir: Path, *, run_id: str, input_text: str,
                 prompt_profile: dict, workflow: dict,
                 business_context: BusinessContext | None = None) -> dict[str, Any]:
    """Write a new local template packet; refuse input/context conflicts first."""
    validate_business_context(config, business_context)
    _identifier(run_id)
    _profile(prompt_profile)
    _workflow(workflow)
    if not isinstance(input_text, str):
        raise _invalid("Studio input must be text")
    try:
        raw_input = input_text.encode("utf-8")
    except UnicodeError:
        raise _invalid("Invalid studio input") from None
    if len(raw_input) > MAX_INPUT_BYTES or find_sensitive(input_text):
        raise _invalid("Studio input exceeds its limit or contains recognized credentials")
    input_hash = sha256(raw_input).hexdigest()
    context_record = _context_record(config, business_context)
    files = _payloads(config, input_hash, len(raw_input), context_record)
    manifest = {
        "schema": PACKET_SCHEMA, "template_revision": REVISION, "run_id": run_id,
        "created_at": utc_now(), "status": "intake_required", "template_only": True,
        "studio_config": config.metadata(), "prompt_profile": dict(prompt_profile),
        "workflow": dict(workflow), "business_context": context_record["metadata"],
        "input_sha256": input_hash, "input_bytes": len(raw_input),
        "execution": dict(EXECUTION), "missing_inputs": list(MISSING_INPUTS),
        "files": _file_records(files),
    }
    files["manifest.json"] = _json_bytes(manifest)
    if (set(files) != REQUIRED_PATHS or any(len(raw) > MAX_FILE_BYTES for raw in files.values())
            or sum(map(len, files.values())) > MAX_PACKET_BYTES):
        raise _invalid("Studio packet exceeds its fixed bounds")
    try:
        output = Path(output_dir).absolute()
        _no_symlink(output)
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
        for directory in sorted(REQUIRED_DIRS):
            (output / directory).mkdir(mode=0o700)
        # Manifest is written last; any partial write remains unverifiable.
        for path in [*sorted(PAYLOAD_PATHS), "manifest.json"]:
            descriptor = os.open(output / path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(files[path])
    except (OSError, TypeError):
        raise _invalid("Cannot create a new studio packet directory") from None
    return verify_packet(output)


def _inventory(root: Path) -> None:
    _no_symlink(root)
    if not root.is_dir():
        raise _invalid("Studio packet directory is missing")
    expected_root = {path for path in REQUIRED_PATHS if "/" not in path} | set(REQUIRED_DIRS)
    for directory, expected in [(root, expected_root), *(
            (root / name, {path.split("/", 1)[1] for path in REQUIRED_PATHS if path.startswith(name + "/")})
            for name in sorted(REQUIRED_DIRS))]:
        found: set[str] = set()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name not in expected or entry.is_symlink():
                    raise _invalid("Unexpected or unsafe studio packet entry")
                is_directory = directory == root and entry.name in REQUIRED_DIRS
                if (is_directory and not entry.is_dir(follow_symlinks=False)
                        or not is_directory and not entry.is_file(follow_symlinks=False)):
                    raise _invalid("Unexpected studio packet file type")
                found.add(entry.name)
        if found != expected:
            raise _invalid("Studio packet inventory is incomplete")


def verify_packet(root: Path) -> dict[str, Any]:
    """Verify this revision's immutable template packet, not publication readiness."""
    try:
        root = Path(root).absolute()
        _inventory(root)
        raw_manifest = _read_regular(root / "manifest.json")
        value = _json(raw_manifest)
        keys = {"schema", "template_revision", "run_id", "created_at", "status",
                "template_only", "studio_config", "prompt_profile", "workflow",
                "business_context", "input_sha256", "input_bytes", "execution",
                "missing_inputs", "files"}
        if (set(value) != keys or value["schema"] != PACKET_SCHEMA
                or value["template_revision"] != REVISION or value["status"] != "intake_required"
                or value["template_only"] is not True or value["execution"] != EXECUTION
                or value["missing_inputs"] != list(MISSING_INPUTS)):
            raise _invalid("Unsupported studio readiness or manifest assertion")
        # Reject bool/int aliases in execution assertions.
        if any(type(value["execution"][key]) is not type(expected) for key, expected in EXECUTION.items()):
            raise _invalid()
        _identifier(value["run_id"])
        _profile(value["prompt_profile"])
        _workflow(value["workflow"])
        _hash(value["input_sha256"])
        if type(value["input_bytes"]) is not int or not 0 <= value["input_bytes"] <= MAX_INPUT_BYTES:
            raise _invalid()
        if not isinstance(value["created_at"], str) or len(value["created_at"]) > 40:
            raise _invalid()
        timestamp = datetime.fromisoformat(value["created_at"])
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise _invalid()
        records = value["files"]
        if not isinstance(records, list) or len(records) != len(PAYLOAD_PATHS):
            raise _invalid()
        seen = set()
        for record in records:
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes", "media_type", "status"}:
                raise _invalid()
            if (type(record["bytes"]) is not int or not 0 <= record["bytes"] <= MAX_FILE_BYTES
                    or record["media_type"] not in {"application/json", "text/markdown"}
                    or record["status"] != "template_only"):
                raise _invalid()
            _hash(record["sha256"])
            path = record["path"]
            if (not isinstance(path, str) or path not in PAYLOAD_PATHS or path in seen
                    or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts):
                raise _invalid("Unsafe or duplicate studio manifest path")
            seen.add(path)
        files = {path: _read_regular(root / path) for path in sorted(PAYLOAD_PATHS)}
        if sum(map(len, files.values())) + len(raw_manifest) > MAX_PACKET_BYTES:
            raise _invalid("Studio packet exceeds its fixed bounds")
        if records != _file_records(files):
            raise _invalid("Studio file bytes or hash do not match the manifest")
        config = _checked_config(files["studio-config.json"])
        if value["studio_config"] != config.metadata():
            raise _invalid("Studio configuration identity does not match")
        context_record = _json(files["business-context.json"])
        if set(context_record) != {"supplied", "metadata", "creative_studio"}:
            raise _invalid()
        if context_record["supplied"] is True:
            _business_metadata(context_record["metadata"])
            expected = {key: config.as_dict()[key] for key in DECLARATION_KEYS}
            if context_record["creative_studio"] is not None and context_record["creative_studio"] != expected:
                raise _invalid("Studio context declaration does not match")
        elif (context_record["supplied"] is not False
              or context_record != {"supplied": False, "metadata": None, "creative_studio": None}):
            raise _invalid()
        if context_record["metadata"] != value["business_context"]:
            raise _invalid("Studio context metadata does not match")
        # Reconstruct fixed templates as well as checking hashes: modified ready/
        # published assertions cannot be legitimized by rewriting colocated hashes.
        expected_files = _payloads(config, value["input_sha256"], value["input_bytes"], context_record)
        if files != expected_files:
            raise _invalid("Studio template contents or intake assertions changed")
        return {"valid": True, "integrity": "verified", "status": "intake_required",
                "template_only": True, "package_path": str(root),
                "manifest_sha256": sha256(raw_manifest).hexdigest(),
                "file_count": len(REQUIRED_PATHS), "run_id": value["run_id"],
                "studio_config": config.metadata(), "prompt_profile": value["prompt_profile"],
                "workflow": value["workflow"], "input_sha256": value["input_sha256"],
                "business_context": value["business_context"], "execution": dict(EXECUTION)}
    except StudioError:
        raise
    except (OSError, TypeError, ValueError, KeyError, RecursionError):
        raise _invalid("Cannot verify studio packet") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="Verify an existing local template packet")
    verify.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_packet(args.path)
    except StudioError as exc:
        parser.exit(2, f"Studio verification failed: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
