"""Bounded local production plans from supplied text drafts; no execution adapters.

The archived packet proves internal byte consistency, not authorship, rights,
independent review, later source freshness, rendered media, or release approval.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

from .creative_studio import (
    CONFIG_PATH, FORMATS, PURPOSES, WORKSPACES, StudioConfig, StudioError,
    _checked_config, load_studio_config,
)
from .models import utc_now
from .prompt_profiles import (
    GUIDANCE_SECTIONS, PROFILE_ID, PROFILE_PATH, PROFILE_REVISION, PromptProfile,
    PromptProfileError, validate_reference,
)
from .safety import find_sensitive


BRIEF_SCHEMA = "jarvis.studio-production-brief.v1"
PLAN_SCHEMA = "jarvis.studio-production-plan.v1"
MANIFEST_SCHEMA = "jarvis.studio-production-packet.v1"
MAX_BRIEF_BYTES = 64 * 1024
MAX_ASSET_BYTES = 256 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_PROFILE_BYTES = 64 * 1024
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_REVIEWS = 32
HEX = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
LANGUAGE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
FORMAT_KINDS = dict(zip(FORMATS, (
    "video_script", "ebook_manuscript", "narration_script", "video_book_storyboard",
)))
KINDS = frozenset(FORMAT_KINDS.values())
WORKSPACE_PATHS = (
    "ai-workspaces/chatgpt-business.md", "ai-workspaces/gemini-ai.md",
    "ai-workspaces/claude.md",
)
BASE_PATHS = frozenset((
    "brief.json", "production-plan.json", "README.md", CONFIG_PATH.as_posix(),
    PROFILE_PATH.as_posix(), *WORKSPACE_PATHS,
))
DIRECTORIES = frozenset(("config", "sources", "ai-workspaces"))
EXECUTION = {
    "provider_calls": 0, "media_rendered": False, "published": False,
    "external_handoff_sent": False, "approval_granted": False,
    "shared_memory_sync": False,
}
EVIDENCE_SCOPE = {
    "source_declaration": "provided_local_drafts",
    "authorship": "unverified", "rights": "unverified",
    "review_assertions": "recorded_untrusted",
    "independent_content_qa": "not_established",
    "lineage_scope": "packaged_local_asset_graph",
    "external_source_freshness": "not_rechecked_by_packet_verification",
    "snapshot_atomicity": "individual_file_reads_not_atomic_project_snapshot",
    "manifest_trust": "local_hash_consistency_not_signature",
    "connection_status": "not_asserted",
}
RELEASE_BLOCKERS = (
    "source_authorship_and_rights_unverified",
    "independent_content_qa_not_established",
    "finished_format_exports_or_rendered_media_not_produced",
    "destination_identity_and_permissions_unverified",
    "exact_artifact_release_approval_not_granted",
)


class StudioProductionError(ValueError):
    """Public-safe production validation or local-file error."""


def _invalid(message: str = "Invalid studio production evidence") -> StudioProductionError:
    return StudioProductionError(message)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _invalid("Duplicate JSON fields are not allowed")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise _invalid("Non-finite JSON numbers are not allowed")


def _json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise _invalid("Malformed production JSON") from None
    if not isinstance(value, dict):
        raise _invalid("Production JSON must be an object")
    pending = [(value, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if depth > 12 or count > 4096:
            raise _invalid("Production JSON exceeds its structural bounds")
        if isinstance(node, dict):
            pending.extend((item, depth + 1) for item in (*node.keys(), *node.values()))
        elif isinstance(node, list):
            pending.extend((item, depth + 1) for item in node)
        elif isinstance(node, float) and not math.isfinite(node):
            raise _invalid("Non-finite JSON numbers are not allowed")
        elif isinstance(node, str) and find_sensitive(node):
            raise _invalid("Production JSON contains recognized credentials")
    return value


def _no_symlink(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            if stat.S_ISLNK(part.lstat().st_mode):
                raise _invalid("Production paths must not contain symlinks")
        except FileNotFoundError:
            continue


def _read_regular(path: Path, limit: int, *, missing_allowed: bool = False) -> bytes | None:
    _no_symlink(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing_allowed:
            return None
        raise _invalid("Required production evidence file is missing") from None
    try:
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise _invalid("Production input must be a bounded regular file")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
                raise _invalid("Production input must be a bounded regular file")
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise _invalid("Production input exceeds its byte limit")
        return raw
    except OSError:
        raise _invalid("Cannot read local production evidence") from None


def _text(value: Any, limit: int, *, field: str = "text") -> None:
    if not isinstance(value, str) or not value.strip():
        raise _invalid(f"Production {field} must be nonempty text")
    try:
        raw = value.encode("utf-8")
    except UnicodeError:
        raise _invalid("Invalid production text encoding") from None
    if (len(raw) > limit or any(ord(char) < 32 and char not in "\r\n\t" for char in value)
            or "\x7f" in value or find_sensitive(value)):
        raise _invalid("Production text is oversized, non-text, or contains recognized credentials")


def _hash(value: Any) -> None:
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise _invalid("Production SHA-256 values must be lowercase hexadecimal")


def _id(value: Any) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise _invalid("Invalid production identifier")


def _asset_path(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 240 or "\\" in value:
        raise _invalid("Unsafe production asset path")
    parts = value.split("/")
    if (not parts or any(not IDENTIFIER.fullmatch(part) or part in {".", ".."} for part in parts)
            or PurePosixPath(value).suffix not in {".md", ".txt"}):
        raise _invalid("Assets must use local relative Markdown or text paths")
    return value


def _selected(value: Any, allowed: tuple[str, ...], field: str) -> None:
    if (not isinstance(value, list) or not 1 <= len(value) <= len(allowed)
            or any(not isinstance(item, str) or item not in allowed for item in value)
            or len(set(value)) != len(value)):
        raise _invalid(f"Invalid or duplicate production {field}")


def _topological_order(assets: list[dict[str, Any]]) -> list[str]:
    by_id = {asset["id"]: asset for asset in assets}
    ordered: list[str] = []
    active: set[str] = set()
    done: set[str] = set()

    def visit(asset_id: str) -> None:
        if asset_id in active:
            raise _invalid("Production asset dependencies must not contain cycles")
        if asset_id in done:
            return
        active.add(asset_id)
        for parent in by_id[asset_id]["parents"]:
            if parent["asset_id"] not in by_id:
                raise _invalid("Production parent names an unknown asset")
            visit(parent["asset_id"])
        active.remove(asset_id)
        done.add(asset_id)
        ordered.append(asset_id)

    for asset in assets:
        visit(asset["id"])
    return ordered


def _brief(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BRIEF_BYTES:
        raise _invalid("Production brief exceeds its byte limit")
    value = _json(raw)
    if (set(value) != {"schema", "project_id", "revision", "title", "objective", "audience",
                       "language", "purposes", "formats", "source_declaration", "assets", "reviews"}
            or value["schema"] != BRIEF_SCHEMA
            or value["source_declaration"] != "provided_local_drafts"):
        raise _invalid("Unsupported production brief schema or source declaration")
    _id(value["project_id"])
    _id(value["revision"])
    for field, limit in (("title", 512), ("objective", 4096), ("audience", 2048)):
        _text(value[field], limit, field=field)
    if (not isinstance(value["language"], str) or len(value["language"]) > 40
            or not LANGUAGE.fullmatch(value["language"])):
        raise _invalid("Invalid production language label")
    _selected(value["purposes"], PURPOSES, "purposes")
    _selected(value["formats"], FORMATS, "formats")
    assets = value["assets"]
    if not isinstance(assets, list) or len(assets) > len(KINDS):
        raise _invalid("Production brief allows at most four draft assets")
    ids: set[str] = set()
    paths: set[str] = set()
    kinds: set[str] = set()
    for asset in assets:
        if (not isinstance(asset, dict) or set(asset) != {"id", "kind", "path", "sha256", "parents"}
                or not isinstance(asset["kind"], str) or asset["kind"] not in KINDS):
            raise _invalid("Invalid production asset declaration")
        _id(asset["id"])
        _hash(asset["sha256"])
        path = _asset_path(asset["path"])
        if asset["id"] in ids or path in paths or asset["kind"] in kinds:
            raise _invalid("Production asset IDs, paths and kinds must be unique")
        ids.add(asset["id"])
        paths.add(path)
        kinds.add(asset["kind"])
        parents = asset["parents"]
        if not isinstance(parents, list) or len(parents) > len(KINDS) - 1:
            raise _invalid("Invalid production parent list")
        seen: set[str] = set()
        for parent in parents:
            if not isinstance(parent, dict) or set(parent) != {"asset_id", "sha256"}:
                raise _invalid("Invalid production parent pin")
            _id(parent["asset_id"])
            _hash(parent["sha256"])
            if parent["asset_id"] == asset["id"] or parent["asset_id"] in seen:
                raise _invalid("Production parent references must be unique and non-self")
            seen.add(parent["asset_id"])
    _topological_order(assets)
    reviews = value["reviews"]
    if not isinstance(reviews, list) or len(reviews) > MAX_REVIEWS:
        raise _invalid("Production review assertions exceed their limit")
    seen_reviews: set[tuple[str, str, str]] = set()
    for review in reviews:
        if (not isinstance(review, dict)
                or set(review) != {"asset_id", "asset_sha256", "reviewer", "result", "note"}
                or not isinstance(review["asset_id"], str) or review["asset_id"] not in ids
                or review["result"] not in ("pass", "changes_requested", "not_reviewed")):
            raise _invalid("Invalid recorded production review")
        _hash(review["asset_sha256"])
        _text(review["reviewer"], 128, field="reviewer")
        _text(review["note"], 2048, field="review note")
        key = (review["asset_id"], review["asset_sha256"], review["reviewer"])
        if key in seen_reviews:
            raise _invalid("Duplicate or contradictory reviewer assertions")
        seen_reviews.add(key)
    _text(raw.decode("utf-8"), MAX_BRIEF_BYTES, field="brief")
    return value


def _profile(raw: bytes) -> PromptProfile:
    if len(raw) > MAX_PROFILE_BYTES:
        raise _invalid("Production prompt profile exceeds its byte limit")
    value = _json(raw)
    validate_reference({"id": value.get("id"), "revision": value.get("revision")})
    if (value.get("schema") != "jarvis.prompt-profile.v1"
            or value.get("kind") != "repository_operating_profile"):
        raise _invalid("Unsupported production prompt profile")
    sections = value.get("guidance")
    if not isinstance(sections, list) or len(sections) != len(GUIDANCE_SECTIONS):
        raise _invalid("Production prompt profile requires all guidance sections")
    guidance: list[str] = []
    for section, expected_id in zip(sections, GUIDANCE_SECTIONS):
        if (not isinstance(section, dict) or set(section) != {"id", "text"}
                or section["id"] != expected_id):
            raise _invalid("Invalid production prompt guidance")
        _text(section["text"], 8192, field="profile guidance")
        guidance.append(section["text"])
    return PromptProfile(sha256(raw).hexdigest(), tuple(guidance))


def _source_text(raw: bytes) -> None:
    if len(raw) > MAX_ASSET_BYTES:
        raise _invalid("Production source exceeds its byte limit")
    try:
        _text(raw.decode("utf-8"), MAX_ASSET_BYTES, field="source asset")
    except UnicodeError:
        raise _invalid("Production sources must be UTF-8 text") from None


def _copy_path(asset: dict[str, Any]) -> str:
    return "sources/" + asset["id"] + PurePosixPath(asset["path"]).suffix


def _derive_plan(brief: dict[str, Any], brief_raw: bytes, config: StudioConfig,
                 profile: PromptProfile, sources: dict[str, bytes | None]) -> dict[str, Any]:
    ordered = _topological_order(brief["assets"])
    by_id = {asset["id"]: asset for asset in brief["assets"]}
    derived: dict[str, dict[str, Any]] = {}
    for asset_id in ordered:
        asset = by_id[asset_id]
        raw = sources[asset_id]
        observed = sha256(raw).hexdigest() if raw is not None else None
        source_status = ("missing" if raw is None else "present"
                         if observed == asset["sha256"] else "stale")
        blockers: list[str] = []
        warnings: list[str] = []
        if source_status != "present":
            blockers.append("source_" + source_status)
        parents: list[dict[str, Any]] = []
        for pin in asset["parents"]:
            parent = derived[pin["asset_id"]]
            declared_match = pin["sha256"] == parent["expected_sha256"]
            observed_match = pin["sha256"] == parent["observed_sha256"]
            if not declared_match:
                blockers.append("parent_declared_hash_mismatch:" + pin["asset_id"])
            if not observed_match:
                blockers.append("parent_observed_hash_mismatch:" + pin["asset_id"])
            if parent["status"] != "prepared_for_review":
                blockers.append("parent_blocked:" + pin["asset_id"])
            parents.append({"asset_id": pin["asset_id"], "pinned_sha256": pin["sha256"],
                            "declared_sha256": parent["expected_sha256"],
                            "observed_sha256": parent["observed_sha256"],
                            "pin_matches_declared": declared_match,
                            "pin_matches_observed": observed_match,
                            "parent_status": parent["status"]})
        reviews: list[dict[str, Any]] = []
        for review in brief["reviews"]:
            if review["asset_id"] != asset_id:
                continue
            matches = observed is not None and review["asset_sha256"] == observed
            reviews.append({**review, "hash_matches_observed": matches,
                            "trust": "recorded_untrusted"})
            if not matches:
                warnings.append("stale_review_assertion:" + review["reviewer"])
            elif review["result"] == "changes_requested":
                blockers.append("recorded_changes_requested:" + review["reviewer"])
        status = ("missing_source" if source_status == "missing" else
                  "stale_source" if source_status == "stale" else
                  "blocked" if blockers else "prepared_for_review")
        derived[asset_id] = {
            "id": asset_id, "kind": asset["kind"], "source_path": asset["path"],
            "packet_path": _copy_path(asset) if raw is not None else None,
            "expected_sha256": asset["sha256"], "observed_sha256": observed,
            "bytes": len(raw) if raw is not None else None,
            "source_status": source_status, "status": status,
            "parents": parents, "review_assertions": reviews,
            "review_status": "recorded_untrusted" if reviews else "not_reviewed",
            "blockers": blockers, "warnings": warnings,
        }
    formats: list[dict[str, Any]] = []
    for label in brief["formats"]:
        asset = next((item for item in derived.values() if item["kind"] == FORMAT_KINDS[label]), None)
        formats.append({"format": label, "required_asset_kind": FORMAT_KINDS[label],
                        "asset_id": asset["id"] if asset else None,
                        "status": asset["status"] if asset else "missing_source",
                        "blockers": list(asset["blockers"]) if asset else ["required_draft_not_declared"],
                        "deliverable_state": "local_text_draft_only" if asset and asset["packet_path"] else "missing",
                        "finished_edition_produced": False, "release_status": "release_blocked"})
    blockers = [{"asset_id": item["id"], "code": code}
                for item in derived.values() for code in item["blockers"]]
    blockers.extend({"format": item["format"], "code": "required_draft_not_declared"}
                    for item in formats if item["asset_id"] is None)
    project = {key: brief[key] for key in ("project_id", "revision", "title", "objective", "audience",
                                         "language", "purposes", "formats", "source_declaration")}
    return {
        "schema": PLAN_SCHEMA, "project": project,
        "brief": {"sha256": sha256(brief_raw).hexdigest(), "bytes": len(brief_raw)},
        "studio_config": config.metadata(), "prompt_profile": profile.metadata(),
        "status": "blocked" if blockers else "prepared_for_review",
        "release_status": "release_blocked", "draft_assets_only": True,
        "contains_source_drafts": any(raw is not None for raw in sources.values()),
        "execution": dict(EXECUTION), "evidence_scope": dict(EVIDENCE_SCOPE),
        "dependency_order": ordered, "assets": list(derived.values()), "formats": formats,
        "blockers": blockers, "release_blockers": list(RELEASE_BLOCKERS),
        "workspace_handoffs": [{"workspace": label, "path": path, "status": "draft_not_sent"}
                               for label, path in zip(WORKSPACES, WORKSPACE_PATHS)],
    }


def _fenced_json(value: Any) -> str:
    text = _json_bytes(value).decode("utf-8").rstrip()
    longest = max((len(match.group()) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return fence + "json\n" + text + "\n" + fence + "\n"


def _documents(plan: dict[str, Any], profile: PromptProfile) -> dict[str, bytes]:
    readme = """# Local studio production review packet

This packet contains supplied local text drafts and a derived production plan.
It does not contain newly rendered video, audio, a finished eBook export or a
synchronized Video Book. No provider was called and no handoff was sent.

Read production-plan.json for each source's expected and observed SHA-256,
dependency pins, recorded review assertions, and missing/stale/blocked states.
prepared_for_review means the declared draft bytes and their local dependencies
are available for review; it does not mean independent content QA passed.
Every release remains release_blocked, including assets with recorded pass claims.
Provided local drafts do not establish authorship or source rights. This packet
does not incorporate unseen prior editions or establish a full-book page count.

The three ai-workspaces files are proposed local handoffs. Their labels do not
prove connected accounts or authorize calls. The pinned Prompt #11 sections are
guidance, not proof of compliance or permission to activate tools.

Keep this immutable packet and its manifest SHA-256 as evidence. Make corrections
in a separate source working directory, update source and parent pins, and build
a new revision into a new output directory. A local verification checks exact
archived inventory, bytes and derived states. It does not reopen the original
working files, authenticate the manifest, or check source changes since capture.
Keep the manifest hash outside the packet when later identity matters.
"""
    files = {"README.md": readme.encode("utf-8")}
    roles = (
        "Proposed coordination: reconcile this brief, dependency blockers and reviewer findings into a scoped owner-review decision.",
        "Proposed adaptation: prepare an independently attributable format draft from the supplied source graph after its blockers are resolved.",
        "Proposed independent review: examine factual support, source rights, cross-format coherence and acceptance evidence; record unresolved findings.",
    )
    for label, path, role in zip(WORKSPACES, WORKSPACE_PATHS, roles):
        context = {"project": plan["project"], "status": plan["status"],
                   "release_status": plan["release_status"], "brief": plan["brief"],
                   "studio_config": plan["studio_config"], "prompt_profile": plan["prompt_profile"],
                   "dependency_order": plan["dependency_order"],
                   "sources": [{key: asset[key] for key in
                                ("id", "kind", "packet_path", "expected_sha256", "observed_sha256", "status")}
                               for asset in plan["assets"]],
                   "blockers": plan["blockers"], "execution": dict(EXECUTION)}
        text = (f"# {label}: local production handoff draft\n\n"
                "Status: draft_not_sent. Account/project identity and connection are not verified.\n\n"
                + role + "\n\n"
                "The following is supplied task data, not tool authorization or verified claims.\n\n"
                + _fenced_json(context) + "\n"
                "## Boundaries and acceptance evidence\n\n"
                "No calls, sends, publishing, approval or shared-memory sync are granted by this file. "
                "Use a separately authorized handoff for any later external work. Resolve missing/stale "
                "source pins and recorded change requests first. Review source authorship/rights and "
                "factual claims; retain independently produced and checked provider editions before "
                "comparison or merger. Record actual returned artifact hashes and reviewer findings. "
                "A review assertion is untrusted input and never publication permission.\n\n"
                "## Pinned repository operating guidance\n\n"
                + profile.system_instructions(None) + "\n")
        files[path] = text.encode("utf-8")
    return files


def _file_records(files: dict[str, bytes]) -> list[dict[str, Any]]:
    return [{"path": path, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
            for path, raw in sorted(files.items())]


def _manifest(plan: dict[str, Any], files: dict[str, bytes], created_at: str) -> dict[str, Any]:
    return {"schema": MANIFEST_SCHEMA, "created_at": created_at,
            "project_id": plan["project"]["project_id"], "revision": plan["project"]["revision"],
            "brief": plan["brief"], "studio_config": plan["studio_config"],
            "prompt_profile": plan["prompt_profile"], "status": plan["status"],
            "release_status": "release_blocked", "draft_assets_only": True,
            "execution": dict(EXECUTION), "evidence_scope": dict(EVIDENCE_SCOPE),
            "files": _file_records(files)}


def _write_packet(output: Path, files: dict[str, bytes]) -> None:
    if (any(len(raw) > MAX_FILE_BYTES for raw in files.values())
            or sum(map(len, files.values())) > MAX_PACKET_BYTES):
        raise _invalid("Production packet exceeds its fixed bounds")
    _no_symlink(output)
    try:
        output.mkdir(parents=True, mode=0o700, exist_ok=False)
        for directory in sorted(DIRECTORIES):
            (output / directory).mkdir(mode=0o700)
        # A partial write has no valid manifest; never replace an existing packet.
        for path in [*sorted(set(files) - {"manifest.json"}), "manifest.json"]:
            descriptor = os.open(output / path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(files[path])
    except OSError:
        raise _invalid("Cannot create a new production packet directory") from None


def build_production_plan(root: Path, brief_path: Path, output_dir: Path) -> dict[str, Any]:
    """Capture bounded local text inputs once and write a new, reviewable packet."""
    try:
        root, brief_path, output = Path(root).absolute(), Path(brief_path).absolute(), Path(output_dir).absolute()
        config = load_studio_config(root)
        profile_raw = _read_regular(root / PROFILE_PATH, MAX_PROFILE_BYTES)
        profile = _profile(profile_raw)
        brief_raw = _read_regular(brief_path, MAX_BRIEF_BYTES)
        brief = _brief(brief_raw)
        sources: dict[str, bytes | None] = {}
        files = {"brief.json": brief_raw, CONFIG_PATH.as_posix(): config._raw,
                 PROFILE_PATH.as_posix(): profile_raw}
        for asset in brief["assets"]:
            path = brief_path.parent.joinpath(*asset["path"].split("/"))
            raw = _read_regular(path, MAX_ASSET_BYTES, missing_allowed=True)
            if raw is not None:
                _source_text(raw)
                files[_copy_path(asset)] = raw
            sources[asset["id"]] = raw
        plan = _derive_plan(brief, brief_raw, config, profile, sources)
        files["production-plan.json"] = _json_bytes(plan)
        files.update(_documents(plan, profile))
        files["manifest.json"] = _json_bytes(_manifest(plan, files, utc_now()))
        _write_packet(output, files)
        return verify_production_plan(output)
    except StudioProductionError:
        raise
    except (OSError, TypeError, ValueError, RecursionError, StudioError, PromptProfileError):
        raise _invalid("Cannot build local studio production evidence") from None


def _inventory(root: Path, allowed_sources: set[str]) -> set[str]:
    _no_symlink(root)
    allowed = BASE_PATHS | {"manifest.json"} | allowed_sources
    if not root.is_dir():
        raise _invalid("Production packet directory is missing")
    found: set[str] = set()
    root_entries = {path for path in allowed if "/" not in path} | DIRECTORIES
    for folder, expected in [("", root_entries), *(
            (directory, {path.split("/", 1)[1] for path in allowed if path.startswith(directory + "/")})
            for directory in sorted(DIRECTORIES))]:
        observed: set[str] = set()
        with os.scandir(root / folder) as entries:
            for entry in entries:
                if entry.name not in expected or entry.is_symlink():
                    raise _invalid("Unexpected or unsafe production packet entry")
                is_directory = not folder and entry.name in DIRECTORIES
                if (is_directory and not entry.is_dir(follow_symlinks=False)
                        or not is_directory and not entry.is_file(follow_symlinks=False)):
                    raise _invalid("Unexpected production packet file type")
                observed.add(entry.name)
                if not is_directory:
                    found.add(folder + "/" + entry.name if folder else entry.name)
        if folder != "sources" and observed != expected:
            raise _invalid("Required production packet inventory is incomplete")
    return found


def verify_production_plan(path: Path) -> dict[str, Any]:
    """Re-derive archived source readiness; never certify approval or fresh worktrees."""
    try:
        root = Path(path).absolute()
        brief_raw = _read_regular(root / "brief.json", MAX_BRIEF_BYTES)
        brief = _brief(brief_raw)
        source_paths = {_copy_path(asset) for asset in brief["assets"]}
        inventory = _inventory(root, source_paths)
        files = {name: _read_regular(root / name, MAX_FILE_BYTES)
                 for name in sorted(inventory - {"manifest.json"})}
        raw_manifest = _read_regular(root / "manifest.json", MAX_BRIEF_BYTES)
        if sum(map(len, files.values())) + len(raw_manifest) > MAX_PACKET_BYTES:
            raise _invalid("Production packet exceeds its fixed bounds")
        value = _json(raw_manifest)
        created_at = value.get("created_at")
        if not isinstance(created_at, str) or len(created_at) > 40:
            raise _invalid("Invalid production evidence observation time")
        timestamp = datetime.fromisoformat(created_at)
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise _invalid("Production evidence timestamp must be UTC")
        config = _checked_config(files[CONFIG_PATH.as_posix()])
        profile = _profile(files[PROFILE_PATH.as_posix()])
        sources: dict[str, bytes | None] = {}
        for asset in brief["assets"]:
            raw = files.get(_copy_path(asset))
            if raw is not None:
                _source_text(raw)
            sources[asset["id"]] = raw
        plan = _derive_plan(brief, brief_raw, config, profile, sources)
        if files["production-plan.json"] != _json_bytes(plan):
            raise _invalid("Production states or source lineage do not match the archived inputs")
        if any(files[name] != raw for name, raw in _documents(plan, profile).items()):
            raise _invalid("Production handoff or scope assertions changed")
        expected = _manifest(plan, files, created_at)
        # Canonical comparison also rejects bool/int aliases and unknown claims.
        if _json_bytes(value) != _json_bytes(expected):
            raise _invalid("Production manifest inventory, identity or hashes do not match")
        return {"valid": True, "integrity": "verified", "package_path": str(root),
                "manifest_sha256": sha256(raw_manifest).hexdigest(), "file_count": len(inventory),
                "project_id": brief["project_id"], "revision": brief["revision"],
                "brief_sha256": plan["brief"]["sha256"],
                "studio_config": config.metadata(), "prompt_profile": profile.metadata(),
                "status": plan["status"], "release_status": "release_blocked",
                "draft_assets_only": True, "contains_source_drafts": plan["contains_source_drafts"],
                "dependency_order": plan["dependency_order"], "formats": plan["formats"],
                "assets": plan["assets"], "blockers": plan["blockers"],
                "release_blockers": list(RELEASE_BLOCKERS), "execution": dict(EXECUTION),
                "evidence_scope": dict(EVIDENCE_SCOPE)}
    except StudioProductionError:
        raise
    except (OSError, TypeError, ValueError, KeyError, RecursionError, StudioError, PromptProfileError):
        raise _invalid("Cannot verify local studio production evidence") from None
