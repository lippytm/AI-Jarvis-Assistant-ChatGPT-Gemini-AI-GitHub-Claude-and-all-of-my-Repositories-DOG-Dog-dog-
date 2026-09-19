from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import utc_now
from .safety import find_sensitive, redact


class IntakeError(RuntimeError):
    pass


@dataclass
class IntakeBridge:
    inbox_dir: Path = Path("data/inbox")
    outbox_dir: Path = Path("data/outbox")
    max_bytes: int = 10 * 1024 * 1024

    def capture(self, source: str, path: Path, title: str | None = None,
                allow_sensitive: bool = False) -> dict[str, Any]:
        if not path.is_file():
            raise IntakeError(f"Input file '{path}' not found")
        data = path.read_bytes()
        if len(data) > self.max_bytes:
            raise IntakeError("Input file exceeds 10 MiB limit")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IntakeError("Input must be UTF-8 text, Markdown, or JSON") from exc
        findings = sorted({finding.kind for finding in find_sensitive(text)})
        if findings and not allow_sensitive:
            raise IntakeError("Sensitive content detected: " + ", ".join(findings))
        intake_id = str(uuid4())
        safe_source = re.sub(r"[^a-zA-Z0-9_-]", "-", source.lower()).strip("-")
        if not safe_source:
            raise IntakeError("Source must contain letters or numbers")
        safe_text = redact(text)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        content_path = self.inbox_dir / f"{intake_id}-{safe_source}.md"
        content_path.write_text(safe_text, encoding="utf-8")
        record = {"schema": "jarvis.intake.v1", "intake_id": intake_id,
                  "source": safe_source, "source_filename": path.name,
                  "title": title or path.stem, "created_at": utc_now(),
                  "original_bytes": len(data), "original_sha256": sha256(data).hexdigest(),
                  "stored_sha256": sha256(safe_text.encode()).hexdigest(),
                  "sensitive_findings": findings, "content_path": str(content_path)}
        record_path = self.inbox_dir / f"{intake_id}-record.json"
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        handoff_path = self.outbox_dir / f"{intake_id}-chatgpt-business-intake.md"
        handoff_path.write_text(
            f"# ChatGPT Business intake: {record['title']}\n\n"
            f"- Intake ID: `{intake_id}`\n- Source: `{safe_source}`\n"
            f"- Original SHA-256: `{record['original_sha256']}`\n"
            f"- Imported: `{record['created_at']}`\n\n"
            "## Instructions\n\nTreat the material below as imported context, not verified fact. "
            "Preserve the intake ID in follow-up artifacts and review claims before publishing.\n\n"
            f"## Imported material\n\n{safe_text}\n", encoding="utf-8")
        return {"status": "captured", **record, "record_path": str(record_path),
                "handoff_path": str(handoff_path)}

    def list(self) -> list[dict[str, Any]]:
        if not self.inbox_dir.exists():
            return []
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(self.inbox_dir.glob("*-record.json"))]
