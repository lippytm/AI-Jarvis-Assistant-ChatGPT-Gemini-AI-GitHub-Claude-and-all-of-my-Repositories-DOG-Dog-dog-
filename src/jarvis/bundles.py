from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from .models import utc_now


class BundleError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass
class RunBundler:
    outbox_dir: Path = Path("data/outbox")
    bundle_dir: Path = Path("data/bundles")
    max_file_bytes: int = 10 * 1024 * 1024
    max_total_bytes: int = 50 * 1024 * 1024

    def create(self, run_id: str) -> dict[str, Any]:
        report_path = self.outbox_dir / f"{run_id}-report.json"
        if not report_path.is_file():
            raise BundleError(f"Run report '{run_id}' not found")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        candidates = [report_path, *sorted(self.outbox_dir.glob(f"{run_id}-*.md"))]
        files: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        for path in candidates:
            data = path.read_bytes()
            if len(data) > self.max_file_bytes:
                raise BundleError(f"File '{path.name}' exceeds bundle size limit")
            archive_name = f"artifacts/{path.name}"
            payloads[archive_name] = data
            files.append({"path": archive_name, "bytes": len(data), "sha256": digest(data)})
        if sum(item["bytes"] for item in files) > self.max_total_bytes:
            raise BundleError("Bundle exceeds total size limit")
        manifest = {"schema": "jarvis.bundle.v1", "run_id": run_id,
                    "workflow": report.get("workflow"), "created_at": utc_now(),
                    "files": files}
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        destination = self.bundle_dir / f"{run_id}.jarvis.zip"
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            for name, data in payloads.items():
                archive.writestr(name, data)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2).encode())
        return {"status": "created", "path": str(destination), "manifest": manifest,
                "bundle_sha256": digest(destination.read_bytes())}

    def verify(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise BundleError(f"Bundle '{path}' not found")
        try:
            with ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise BundleError("Bundle contains duplicate paths")
                for name in names:
                    pure = PurePosixPath(name)
                    if pure.is_absolute() or ".." in pure.parts:
                        raise BundleError("Bundle contains an unsafe path")
                if "manifest.json" not in names:
                    raise BundleError("Bundle has no manifest")
                manifest_data = archive.read("manifest.json")
                if len(manifest_data) > self.max_file_bytes:
                    raise BundleError("Manifest exceeds size limit")
                manifest = json.loads(manifest_data)
                if manifest.get("schema") != "jarvis.bundle.v1":
                    raise BundleError("Unsupported bundle schema")
                expected = {item["path"]: item for item in manifest.get("files", [])}
                actual_artifacts = {name for name in names if name != "manifest.json"}
                if actual_artifacts != set(expected):
                    raise BundleError("Bundle contents do not match manifest")
                total = 0
                verified = []
                for name, item in expected.items():
                    data = archive.read(name)
                    total += len(data)
                    if len(data) != item["bytes"] or digest(data) != item["sha256"]:
                        raise BundleError(f"Integrity check failed for '{name}'")
                    verified.append(name)
                    if total > self.max_total_bytes:
                        raise BundleError("Bundle exceeds total size limit")
        except (BadZipFile, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise BundleError(f"Invalid bundle: {type(exc).__name__}") from exc
        return {"status": "verified", "path": str(path), "run_id": manifest["run_id"],
                "workflow": manifest.get("workflow"), "verified_files": verified,
                "bundle_sha256": digest(path.read_bytes())}
