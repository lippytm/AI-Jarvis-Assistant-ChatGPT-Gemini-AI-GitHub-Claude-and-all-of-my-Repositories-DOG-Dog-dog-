from __future__ import annotations

import json
import re
from hashlib import sha256
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .control_tower import ControlTower
from .approvals import ApprovalQueue
from .github_inventory import list_repositories
from .models import utc_now


TOKEN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")


class WorkflowError(RuntimeError):
    pass


@dataclass
class WorkflowRunner:
    tower: ControlTower
    workflow_dir: Path = Path("workflows")
    outbox_dir: Path = Path("data/outbox")
    run_dir: Path = Path("data/runs")

    def list(self) -> list[str]:
        return sorted(path.stem for path in self.workflow_dir.glob("*.json"))

    def load(self, name: str) -> dict[str, Any]:
        path = self.workflow_dir / f"{name}.json"
        if not path.is_file():
            raise WorkflowError(f"Workflow '{name}' not found")
        definition = json.loads(path.read_text(encoding="utf-8"))
        errors = self.validate_definition(definition)
        if errors:
            raise WorkflowError("; ".join(errors))
        return definition

    def validate_all(self) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}
        for path in sorted(self.workflow_dir.glob("*.json")):
            try:
                definition = json.loads(path.read_text(encoding="utf-8"))
                results[path.stem] = self.validate_definition(definition)
            except json.JSONDecodeError as exc:
                results[path.stem] = [f"Invalid JSON: {exc.msg}"]
        return results

    @staticmethod
    def validate_definition(definition: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        steps = definition.get("steps")
        if not isinstance(steps, list) or not steps:
            return ["Workflow must contain at least one step"]
        seen: set[str] = set()
        for index, step in enumerate(steps):
            prefix = f"step {index + 1}"
            if not isinstance(step, dict):
                errors.append(f"{prefix} must be an object")
                continue
            step_id = step.get("id")
            if not step_id or not re.fullmatch(r"[a-zA-Z0-9_-]+", str(step_id)):
                errors.append(f"{prefix} has an invalid id")
            elif step_id in seen:
                errors.append(f"{prefix} duplicates id '{step_id}'")
            else:
                seen.add(step_id)
            if step.get("type") not in {"ai", "github_inventory", "handoff", "approval"}:
                errors.append(f"{prefix} has an unsupported type")
            if step.get("type") == "ai" and not step.get("prompt"):
                errors.append(f"{prefix} requires prompt")
        return errors

    def run(self, name: str, input_text: str, allow_external: bool = False,
            force: bool = False) -> dict[str, Any]:
        definition = self.load(name)
        idempotency_key = sha256(f"{name}\0{input_text}".encode()).hexdigest()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.run_dir / f"{idempotency_key}.json"
        if cache_path.is_file() and not force:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached["reused"] = True
            return cached
        run_id = str(uuid4())
        context: dict[str, Any] = {"input": input_text, "run_id": run_id, "steps": {}}
        results: list[dict[str, Any]] = []
        for step in definition["steps"]:
            step_id = step["id"]
            kind = step["type"]
            if kind == "ai":
                provider = step.get("provider", "mock")
                if provider != "mock" and not allow_external:
                    result = {"status": "skipped", "output": "[Step skipped: external provider not enabled]",
                              "reason": "external providers require --allow-external"}
                else:
                    prompt = self._render(step["prompt"], context)
                    response = self.tower.run(prompt, provider, step.get("system"))
                    result = {"status": "completed", "output": response.content,
                              "task_id": response.task_id, "provider": response.provider,
                              "model": response.model, "content_sha256": response.content_sha256}
            elif kind == "github_inventory":
                repos = list_repositories(step.get("owner"), self.tower.settings.timeout_seconds)
                result = {"status": "completed", "output": json.dumps(repos, indent=2),
                          "repository_count": len(repos)}
            elif kind == "handoff":
                content = self._render(step["content"], context)
                self.outbox_dir.mkdir(parents=True, exist_ok=True)
                destination = re.sub(r"[^a-zA-Z0-9_-]", "-", step.get("destination", "workspace"))
                path = self.outbox_dir / f"{run_id}-{step_id}-{destination}.md"
                path.write_text(content, encoding="utf-8")
                result = {"status": "drafted", "output": content, "path": str(path),
                          "destination": destination,
                          "note": "Draft only; no message was sent or published."}
            elif kind == "approval":
                summary = self._render(step["summary"], context)
                approval_id = f"{run_id}-{step_id}"
                approval_root = self.run_dir.parent / "approvals"
                record = ApprovalQueue(approval_root).create(
                    approval_id, run_id, step.get("action", step_id), summary)
                result = {"status": "pending_approval", "output": summary,
                          "approval_id": approval_id, "approval": record}
            else:
                raise WorkflowError(f"Unsupported step type '{kind}'")
            context["steps"][step_id] = result
            results.append({"id": step_id, "type": kind, **result})
        report = {"workflow": name, "run_id": run_id, "idempotency_key": idempotency_key,
                  "created_at": utc_now(),
                  "status": "completed", "steps": results}
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        (self.outbox_dir / f"{run_id}-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        cache_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    @classmethod
    def _render(cls, template: str, context: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            value: Any = context
            for key in match.group(1).split("."):
                if not isinstance(value, dict) or key not in value:
                    raise WorkflowError(f"Unknown template value '{match.group(1)}'")
                value = value[key]
            return str(value)
        return TOKEN.sub(replace, template)
