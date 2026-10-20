from __future__ import annotations

import json
import re
import time
from hashlib import sha256
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .control_tower import ControlTower
from .approvals import ApprovalQueue
from .github_inventory import list_repositories
from .models import utc_now
from .prompt_profiles import (PromptProfile, PromptProfileError, load_prompt_profile,
                              validate_reference)
from .safety import find_sensitive, redact
from .business_context import BusinessContext, load_business_context


TOKEN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")
WORKFLOW_NAME = re.compile(r"[a-zA-Z0-9_-]+")


class WorkflowError(RuntimeError):
    pass


@dataclass
class WorkflowRunner:
    tower: ControlTower
    workflow_dir: Path = Path("workflows")
    outbox_dir: Path = Path("data/outbox")
    run_dir: Path = Path("data/runs")
    # Explicit compatibility for isolated API/test workflows. Catalog validation
    # always requires profiles, regardless of this plan/run-only option.
    allow_unprofiled: bool = False

    def list(self) -> list[str]:
        return sorted(path.stem for path in self.workflow_dir.glob("*.json")
                      if WORKFLOW_NAME.fullmatch(path.stem))

    def load(self, name: str) -> dict[str, Any]:
        return self._load(name)[0]

    def _load(self, name: str) -> tuple[dict[str, Any], PromptProfile | None]:
        if not WORKFLOW_NAME.fullmatch(name):
            raise WorkflowError("Workflow name must be a registered filename without a path")
        path = self.workflow_dir / f"{name}.json"
        if not path.is_file():
            raise WorkflowError(f"Workflow '{name}' not found")
        return self._read_definition(path, required_profile=not self.allow_unprofiled)

    def _read_definition(self, path: Path, *, required_profile: bool
                         ) -> tuple[dict[str, Any], PromptProfile | None]:
        try:
            definition = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise WorkflowError(f"Cannot read workflow: {type(exc).__name__}") from exc
        errors = self.validate_definition(definition)
        if errors:
            raise WorkflowError("; ".join(errors))
        if "prompt_profile" not in definition:
            if required_profile:
                raise WorkflowError("Workflow requires a prompt_profile reference")
            return definition, None
        try:
            profile = load_prompt_profile(definition["prompt_profile"], self.workflow_dir.parent)
        except PromptProfileError as exc:
            raise WorkflowError(str(exc)) from exc
        return definition, profile

    def validate_all(self) -> dict[str, list[str]]:
        return self.validate_catalog()["workflows"]

    def validate_catalog(self) -> dict[str, Any]:
        """Validate and attest every JSON entry, with no unprofiled exemption."""
        results: dict[str, list[str]] = {}
        covered: dict[str, Any] = {}
        for path in sorted(self.workflow_dir.glob("*.json")):
            if not WORKFLOW_NAME.fullmatch(path.stem):
                results[path.stem] = ["Workflow filename must contain only letters, numbers, underscores or hyphens"]
                continue
            try:
                definition, profile = self._read_definition(path, required_profile=True)
                assert profile is not None
                results[path.stem] = []
                covered[path.stem] = {"workflow_sha256": self._definition_hash(definition),
                                      "prompt_profile": profile.metadata()}
            except WorkflowError as exc:
                results[path.stem] = [str(exc)]
        valid = bool(results) and not any(results.values())
        coverage = {"scope": "repository_workflow_catalog", "required": True,
                    "complete": valid, "workflow_count": len(results),
                    "covered_count": len(covered),
                    "uncovered_workflows": sorted(set(results) - set(covered)),
                    "workflows": covered,
                    "catalog_sha256": self._definition_hash(covered)}
        return {"valid": valid, "workflows": results, "prompt_profile_coverage": coverage}

    @staticmethod
    def _definition_hash(value: dict[str, Any]) -> str:
        return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _profile_evidence(profile: PromptProfile | None) -> dict[str, Any]:
        return {"prompt_profile": profile.metadata() if profile else None,
                "profile_status": "resolved" if profile else "unprofiled_ad_hoc"}

    def plan(self, name: str, input_text: str, *,
             business_context: Path | str | None = None) -> dict[str, Any]:
        definition, profile = self._load(name)
        business = load_business_context(business_context) if business_context is not None else None
        planned = []
        external_calls = 0
        for step in definition["steps"]:
            provider = step.get("provider") if step.get("type") == "ai" else None
            external = bool(provider and provider != "mock")
            external_calls += int(external)
            planned.append({"id": step["id"], "type": step["type"], "provider": provider,
                            "external": external,
                            "configured": (self.tower.providers[provider].configured()
                                           if provider in self.tower.providers else None)})
        findings = sorted({finding.kind for finding in find_sensitive(input_text)})
        return {"workflow": name, "workflow_sha256": self._definition_hash(definition),
                **self._profile_evidence(profile), "valid": True, "steps": planned,
                **({"business_context": business.metadata()} if business else {}),
                "external_calls": external_calls,
                "external_call_budget": self.tower.settings.max_external_calls,
                "within_budget": external_calls <= self.tower.settings.max_external_calls,
                "sensitive_findings": findings,
                "will_execute": False}

    @staticmethod
    def validate_definition(definition: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(definition, dict):
            return ["Workflow must be an object"]
        if "prompt_profile" in definition:
            try:
                validate_reference(definition["prompt_profile"])
            except PromptProfileError as exc:
                errors.append(str(exc))
        steps = definition.get("steps")
        if not isinstance(steps, list) or not steps:
            return errors + ["Workflow must contain at least one step"]
        seen: set[str] = set()
        for index, step in enumerate(steps):
            prefix = f"step {index + 1}"
            if not isinstance(step, dict):
                errors.append(f"{prefix} must be an object")
                continue
            step_id = step.get("id")
            if not isinstance(step_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", step_id):
                errors.append(f"{prefix} has an invalid id")
            elif step_id in seen:
                errors.append(f"{prefix} duplicates id '{step_id}'")
            else:
                seen.add(step_id)
            kind = step.get("type")
            if not isinstance(kind, str) or kind not in {"ai", "github_inventory", "handoff", "approval"}:
                errors.append(f"{prefix} has an unsupported type")
                continue
            required = {"ai": "prompt", "handoff": "content", "approval": "summary"}.get(kind)
            if required and (not isinstance(step.get(required), str) or not step[required].strip()):
                errors.append(f"{prefix} requires nonempty text in {required}")
            for field in ("provider", "system", "destination", "action", "owner"):
                if field in step and (not isinstance(step[field], str) or not step[field].strip()):
                    errors.append(f"{prefix} requires nonempty text in {field}")
        return errors

    def run(self, name: str, input_text: str, allow_external: bool = False,
            force: bool = False, allow_sensitive: bool = False, *,
            business_context: Path | str | None = None) -> dict[str, Any]:
        definition, profile = self._load(name)
        business = load_business_context(business_context) if business_context is not None else None
        external_calls = sum(1 for step in definition["steps"]
                             if step.get("type") == "ai" and step.get("provider", "mock") != "mock")
        if external_calls > self.tower.settings.max_external_calls:
            raise WorkflowError(f"Workflow requires {external_calls} external calls but budget is "
                                f"{self.tower.settings.max_external_calls}")
        findings = find_sensitive(input_text)
        if findings and not allow_sensitive:
            kinds = ", ".join(sorted({finding.kind for finding in findings}))
            raise WorkflowError(f"Sensitive input detected ({kinds}); remove it or explicitly allow it")
        definition_hash = self._definition_hash(definition)
        profile_evidence = self._profile_evidence(profile)
        business_evidence = {"business_context": business.metadata()} if business else {}
        identity = {"contract": 3, "workflow": name, "workflow_sha256": definition_hash,
                    **profile_evidence,
                    **business_evidence,
                    "input": input_text, "allow_external": allow_external,
                    "allow_sensitive": allow_sensitive}
        idempotency_key = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.run_dir / f"{idempotency_key}.json"
        if cache_path.is_file() and not force:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("status") in {"completed", "pending_approval"}:
                cached["reused"] = True
                return cached
        run_id = str(uuid4())
        context: dict[str, Any] = {"input": input_text, "run_id": run_id, "steps": {}}
        results: list[dict[str, Any]] = []
        status = "completed"
        for step in definition["steps"]:
            started = time.monotonic()
            started_at = utc_now()
            step_id = step["id"]
            kind = step["type"]
            try:
                result = self._execute_step(step, context, run_id, allow_external, profile, business)
            except Exception as exc:
                # Preserve failure evidence without logging prompts, keys or response bodies.
                result = {"status": "failed", "output": "[Step failed; downstream work stopped]",
                          "error_type": type(exc).__name__}
            context["steps"][step_id] = result
            results.append({"id": step_id, "type": kind, "started_at": started_at,
                            "duration_ms": round((time.monotonic() - started) * 1000, 2), **result})
            if result["status"] not in {"completed", "drafted"}:
                status = "blocked" if result["status"] == "skipped" else result["status"]
                break
        report = {"workflow": name, "workflow_sha256": definition_hash,
                  **profile_evidence,
                  **business_evidence,
                  "run_id": run_id, "idempotency_key": idempotency_key,
                  "created_at": utc_now(), "status": status, "steps": results,
                  "not_run_steps": [step["id"] for step in definition["steps"][len(results):]]}
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        safe_report = json.loads(redact(json.dumps(report)))
        (self.outbox_dir / f"{run_id}-report.json").write_text(
            json.dumps(safe_report, indent=2), encoding="utf-8")
        if status in {"completed", "pending_approval"}:
            cache_path.write_text(json.dumps(safe_report, indent=2), encoding="utf-8")
        return safe_report

    def _execute_step(self, step: dict[str, Any], context: dict[str, Any],
                      run_id: str, allow_external: bool,
                      profile: PromptProfile | None = None,
                      business_context: BusinessContext | None = None) -> dict[str, Any]:
        step_id = step["id"]
        kind = step["type"]
        if kind == "ai":
            provider = step.get("provider", "mock")
            if provider != "mock" and not allow_external:
                result = {"status": "skipped", "output": "[Step skipped: external provider not enabled]",
                          "reason": "external providers require --allow-external"}
            else:
                prompt = self._render(step["prompt"], context)
                if business_context:
                    prompt = business_context.task_data() + "\n\nStep task:\n" + prompt
                system = (profile.system_instructions(step.get("system"))
                          if profile else step.get("system"))
                response = self.tower.run(prompt, provider, system)
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
        return result

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
