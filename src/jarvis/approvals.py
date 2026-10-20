from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import utc_now


@dataclass
class ApprovalQueue:
    root: Path = Path("data/approvals")

    def create(self, approval_id: str, run_id: str, action: str,
               summary: str) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        record = {"id": approval_id, "run_id": run_id, "action": action,
                  "summary": summary, "status": "pending", "created_at": utc_now()}
        self._write(record)
        return record

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        records = [json.loads(path.read_text(encoding="utf-8"))
                   for path in sorted(self.root.glob("*.json"))]
        return [record for record in records if status is None or record["status"] == status]

    def approve(self, approval_id: str) -> dict[str, Any]:
        path = self.root / f"{approval_id}.json"
        if not path.is_file():
            raise ValueError(f"Approval '{approval_id}' not found")
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update({"status": "approved", "approved_at": utc_now()})
        self._write(record)
        return record

    def _write(self, record: dict[str, Any]) -> None:
        (self.root / f"{record['id']}.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8")
