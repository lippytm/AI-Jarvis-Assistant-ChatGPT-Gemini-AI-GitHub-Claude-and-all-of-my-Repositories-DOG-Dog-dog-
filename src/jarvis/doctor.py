from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .control_tower import ControlTower
from .workflows import WorkflowRunner


@dataclass
class Doctor:
    tower: ControlTower
    project_root: Path = Path(".")

    def run(self) -> dict[str, Any]:
        runner = WorkflowRunner(self.tower, self.project_root / "workflows")
        validation = runner.validate_all()
        checks = [
            self._check("python", sys.version_info >= (3, 11),
                        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
            self._check("workflows", bool(validation) and not any(validation.values()), validation),
            self._check("database_parent", self._writable_parent(self.tower.settings.db_path),
                        str(self.tower.settings.db_path.parent)),
            self._check("outbox_parent", self._writable_parent(Path("data/outbox")), "data/outbox"),
            self._check("gitignore", self._gitignore_protects_secrets(),
                        "expects .env, data/, and local databases to be ignored"),
        ]
        providers = {name: provider.configured() for name, provider in self.tower.providers.items()}
        passed = sum(int(check["passed"]) for check in checks)
        score = round(100 * passed / len(checks)) if checks else 0
        return {"status": "ready_local" if passed == len(checks) else "attention_required",
                "readiness_score": score, "platform": platform.platform(),
                "checks": checks, "providers": providers,
                "live_workflows_ready": any(value for key, value in providers.items()
                                            if key != "mock"),
                "note": "Provider configuration is informational; doctor never makes API calls."}

    @staticmethod
    def _check(name: str, passed: bool, detail: Any) -> dict[str, Any]:
        return {"name": name, "passed": passed, "detail": detail}

    @staticmethod
    def _writable_parent(path: Path) -> bool:
        parent = path.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        return parent.exists() and os.access(parent, os.W_OK)

    def _gitignore_protects_secrets(self) -> bool:
        path = self.project_root / ".gitignore"
        if not path.is_file():
            return False
        values = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
        return {".env", "data/", "*.sqlite3"}.issubset(values)
