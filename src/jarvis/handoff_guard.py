"""Jarvis offline handoff toolkit. Inspect data; never execute imported instructions.

No network, archive extraction, dynamic tools, approval service or scheduler.
Reports contain filenames; keep them private unless separately cleared for release.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import sqlite3
import stat
from uuid import uuid4
import zlib
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile

from .hermes import MemPalace
from .referral_review import build_review, load_registry

VERSION = "0.2.0"
MAX_ARCHIVE = 8_000_000
MAX_FILE = 1_000_000
MAX_TOTAL = 4_000_000
MAX_MANIFEST = 64_000
MAX_ENTRIES = 128
MAX_RATIO = 100
MAX_TASKS = 16
HASH = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
RESERVED = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)},
            *{f"LPT{i}" for i in range(1, 10)}}
TOOLS = {
    "bundle-verify": "Check bounded jarvis.bundle.v1 bytes and manifests without extracting.",
    "merge-preview": "Compare two bundles without overwriting or deleting any artifact.",
    "referral-review": "Check the existing three-channel referral registry offline.",
    "owner-approval": "Unimplemented human decision boundary; never auto-approved.",
}


class HandoffError(ValueError):
    """Invalid, unsupported or oversized handoff input."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def fingerprint(value: object) -> str:
    return sha256(canonical(value)).hexdigest()


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise HandoffError("Duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise HandoffError("Nonfinite JSON value")


def parse_json(data: bytes) -> object:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_nonfinite)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise HandoffError("Invalid JSON input") from exc


def read_bounded(path: Path, limit: int) -> bytes:
    # A caller explicitly selects this local input; imported content selects no paths.
    # Do not follow a final symlink or read a device/FIFO. Not a hostile-host sandbox.
    if path.is_symlink() or not path.is_file():
        raise HandoffError("Input must be a regular non-symlink file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise HandoffError("Input exceeds byte limit")
    return data


def portable_path(name: object) -> str:
    if not isinstance(name, str) or not name or len(name) > 240:
        raise HandoffError("Invalid archive path")
    parts = name.split("/")
    for part in parts:
        if (not part or part in {".", ".."} or part[-1:] in {" ", "."}
                or not re.fullmatch(r"[A-Za-z0-9_. -]+", part)
                or part.split(".")[0].upper() in RESERVED):
            raise HandoffError("Nonportable or unsafe archive path")
    return name


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise HandoffError("Invalid identifier")
    return value


def _sha(value: object) -> str:
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise HandoffError("Invalid SHA-256")
    return value


def _member_read(archive: ZipFile, info, limit: int) -> bytes:
    with archive.open(info) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit or len(data) != info.file_size:
        raise HandoffError("Archive member size mismatch")
    return data


def verify_bundle(path: Path, *, expected_sha256: str | None = None) -> dict:
    """Verify byte integrity, NOT provenance, consent, safety or provider identity.

    Accepts the existing jarvis.bundle.v1 manifest format. Directory records and
    nonportable names are rejected rather than rewritten. No contents are extracted.
    """
    raw = read_bounded(path, MAX_ARCHIVE)
    archive_hash = sha256(raw).hexdigest()
    if expected_sha256 is not None and _sha(expected_sha256) != archive_hash:
        raise HandoffError("Archive does not match the separately supplied anchor")
    try:
        with ZipFile(BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not 2 <= len(infos) <= MAX_ENTRIES:
                raise HandoffError("Invalid archive entry count")
            members, normalized = {}, set()
            total = 0
            for info in infos:
                name = portable_path(info.filename)
                if info.orig_filename != info.filename or name.casefold() in normalized:
                    raise HandoffError("Duplicate, case-colliding or truncated archive path")
                normalized.add(name.casefold())
                if info.flag_bits & 1 or info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
                    raise HandoffError("Encrypted or unsupported archive entry")
                if stat.S_IFMT(info.external_attr >> 16) not in {0, stat.S_IFREG}:
                    raise HandoffError("Only ordinary file entries are allowed")
                limit = MAX_MANIFEST if name == "manifest.json" else MAX_FILE
                if info.file_size > limit or info.file_size < 0:
                    raise HandoffError("Declared archive member exceeds byte limit")
                if info.file_size > MAX_RATIO * max(1, info.compress_size):
                    raise HandoffError("Archive compression ratio exceeds limit")
                total += info.file_size
                members[name] = info
            if total > MAX_TOTAL or "manifest.json" not in members:
                raise HandoffError("Missing manifest or archive exceeds total limit")
            for name in normalized:
                parts = name.split("/")
                if any("/".join(parts[:i]) in normalized for i in range(1, len(parts))):
                    raise HandoffError("Archive contains a file/directory collision")
            manifest = parse_json(_member_read(archive, members["manifest.json"], MAX_MANIFEST))
            required = {"schema", "run_id", "files"}
            allowed = required | {"workflow", "created_at"}
            if not isinstance(manifest, dict) or not required <= set(manifest) <= allowed:
                raise HandoffError("Invalid manifest fields")
            if manifest["schema"] != "jarvis.bundle.v1":
                raise HandoffError("Unsupported manifest schema")
            _identifier(manifest["run_id"])
            for field in ("workflow", "created_at"):
                value = manifest.get(field)
                if value is not None and (not isinstance(value, str) or len(value) > 200):
                    raise HandoffError("Invalid manifest metadata")
            declared = manifest["files"]
            if not isinstance(declared, list) or not 1 <= len(declared) < MAX_ENTRIES:
                raise HandoffError("Invalid manifest file list")
            expected = {}
            for item in declared:
                if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
                    raise HandoffError("Invalid manifest entry")
                name = portable_path(item["path"])
                if name == "manifest.json" or name in expected:
                    raise HandoffError("Duplicate or recursive manifest entry")
                if type(item["bytes"]) is not int or not 0 <= item["bytes"] <= MAX_FILE:
                    raise HandoffError("Invalid manifest byte count")
                _sha(item["sha256"])
                expected[name] = item
            if set(expected) != set(members) - {"manifest.json"}:
                raise HandoffError("Declared and actual files differ")
            for name, item in expected.items():
                if members[name].file_size != item["bytes"]:
                    raise HandoffError("Declared byte count mismatch")
                data = _member_read(archive, members[name], MAX_FILE)
                if sha256(data).hexdigest() != item["sha256"]:
                    raise HandoffError("Member digest mismatch")
    except (BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as exc:
        raise HandoffError("Unreadable archive") from exc
    return {"tool": "bundle-verify", "tool_version": VERSION, "status": "integrity_checked",
            "archive_sha256": archive_hash, "independent_anchor_supplied": expected_sha256 is not None,
            "source_run_id": manifest["run_id"], "content_trust": "untrusted",
            "provider_identity": "not_authenticated", "files": [expected[k] for k in sorted(expected)],
            "files_extracted": 0, "provider_calls": 0, "release_authorized": False}


def preview_merge(base_path: Path, incoming_path: Path, *, base_sha256: str | None = None,
                  incoming_sha256: str | None = None) -> dict:
    """Two-way preview only; no semantic merge, extraction or deletion inference."""
    base = verify_bundle(base_path, expected_sha256=base_sha256)
    incoming = verify_bundle(incoming_path, expected_sha256=incoming_sha256)
    left = {f["path"]: f for f in base["files"]}
    right = {f["path"]: f for f in incoming["files"]}
    # Different portable spellings may still collide on Windows/macOS.
    folded = {}
    for name in set(left) | set(right):
        prior = folded.setdefault(name.casefold(), name)
        if prior != name:
            raise HandoffError("Cross-bundle case collision")
    for name in folded:
        parts = name.split("/")
        if any("/".join(parts[:i]) in folded for i in range(1, len(parts))):
            raise HandoffError("Cross-bundle file/directory collision")
    changes = []
    for name in sorted(set(left) | set(right)):
        a, b = left.get(name), right.get(name)
        status = ("added_candidate" if a is None else "absent_in_incoming_preserved" if b is None
                  else "unchanged" if a["sha256"] == b["sha256"] else "conflict_requires_review")
        parts = name.lower().split("/")
        sensitive = (any(p.startswith(".env") or p in {".github", ".git"} for p in parts)
                     or parts[-1] in {"agents.md", "claude.md", "skill.md"}
                     or "policy" in parts[-1] or "credential" in parts[-1])
        changes.append({"path": name, "status": status, "security_review_required": sensitive,
                        "base_sha256": a["sha256"] if a else None,
                        "incoming_sha256": b["sha256"] if b else None})
    report = {"tool": "merge-preview", "tool_version": VERSION, "status": "review_required",
              "base_archive_sha256": base["archive_sha256"],
              "incoming_archive_sha256": incoming["archive_sha256"], "changes": changes,
              "conflicts": sum(c["status"] == "conflict_requires_review" for c in changes),
              "files_written": 0, "files_deleted": 0, "provider_calls": 0,
              "release_authorized": False, "content_trust": "untrusted"}
    report["plan_sha256"] = fingerprint(report)
    return report


def plan_workflow(spec: object) -> dict:
    """Validate a bounded dependency graph. Does not run any listed task."""
    if not isinstance(spec, dict) or set(spec) != {"schema", "mission_id", "tasks"}:
        raise HandoffError("Invalid workflow fields")
    if spec["schema"] != "jarvis.offline-plan.v1":
        raise HandoffError("Unsupported workflow schema")
    _identifier(spec["mission_id"])
    tasks = spec["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        raise HandoffError("Invalid task count")
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"id", "tool", "depends_on"}:
            raise HandoffError("Invalid task fields")
        identity = _identifier(task["id"])
        if identity in by_id or not isinstance(task["tool"], str) or task["tool"] not in TOOLS:
            raise HandoffError("Duplicate task or unregistered tool")
        deps = task["depends_on"]
        if not isinstance(deps, list) or len(deps) > MAX_TASKS:
            raise HandoffError("Invalid task dependencies")
        for dep in deps:
            _identifier(dep)
        if len(set(deps)) != len(deps) or identity in deps:
            raise HandoffError("Duplicate dependency or self-cycle")
        by_id[identity] = task
    if any(d not in by_id for task in tasks for d in task["depends_on"]):
        raise HandoffError("Missing dependency")
    done, batches = set(), []
    while len(done) < len(tasks):
        batch = sorted(i for i, t in by_id.items() if i not in done and set(t["depends_on"]) <= done)
        if not batch:
            raise HandoffError("Workflow dependency cycle")
        batches.append(batch)
        done.update(batch)
    return {"tool": "workflow-plan", "tool_version": VERSION, "status": "planned_not_executed",
            "mission_id": spec["mission_id"], "input_sha256": fingerprint(spec), "batches": batches,
            "approval_boundaries": sorted(t["id"] for t in tasks if t["tool"] == "owner-approval"),
            "planned_tasks": len(tasks), "executed_tasks": 0, "provider_calls": 0,
            "release_authorized": False, "scheduler_started": False}


def catalog() -> dict:
    return {"tool_version": VERSION, "network_enabled": False, "dynamic_tool_loading": False,
            "tools": [{"id": k, "description": v, "implemented": k != "owner-approval"}
                      for k, v in TOOLS.items()], "planner_is_executor": False}


def record_receipt(report: dict, path: Path) -> dict:
    """Optional local metadata receipt. A local hash chain is not a signature."""
    result_hash = fingerprint(report)
    run_id = str(uuid4())
    ledger = MemPalace(path)
    head = ledger.append(run_id, "handoff_guard", {"tool_version": VERSION,
                         "action": "offline_review", "status": "recorded",
                         "output_sha256": result_hash, "provider_calls": 0})
    ledger.history(run_id, expected_head=head)
    return {**report, "receipt": {"run_id": run_id, "head_sha256": head,
                                  "result_sha256": result_hash, "scope": "local_metadata_only"}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, help="Optional private local SQLite receipt file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    verify = sub.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--expected-sha256")
    preview = sub.add_parser("preview")
    preview.add_argument("base", type=Path)
    preview.add_argument("incoming", type=Path)
    preview.add_argument("--base-sha256")
    preview.add_argument("--incoming-sha256")
    plan = sub.add_parser("plan")
    plan.add_argument("spec", type=Path)
    referral = sub.add_parser("referrals")
    referral.add_argument("registry", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            report = catalog()
        elif args.command == "verify":
            report = verify_bundle(args.bundle, expected_sha256=args.expected_sha256)
        elif args.command == "preview":
            report = preview_merge(args.base, args.incoming, base_sha256=args.base_sha256,
                                   incoming_sha256=args.incoming_sha256)
        elif args.command == "plan":
            report = plan_workflow(parse_json(read_bounded(args.spec, MAX_MANIFEST)))
        else:
            report = build_review(load_registry(args.registry))
        if args.ledger is not None:
            report = record_receipt(report, args.ledger)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f"Offline check failed ({type(exc).__name__}); no release authorized.\n")
    print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
