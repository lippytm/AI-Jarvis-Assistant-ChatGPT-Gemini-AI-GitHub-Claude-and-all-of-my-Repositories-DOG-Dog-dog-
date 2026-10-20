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
from .creative_studio import (StudioConfig, build_packet, load_studio_config,
                              validate_business_context, verify_packet)


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

    def _load(self, name: str) -> tuple[dict[str, Any], PromptProfile | None, StudioConfig | None]:
        if not WORKFLOW_NAME.fullmatch(name):
            raise WorkflowError("Workflow name must be a registered filename without a path")
        path = self.workflow_dir / f"{name}.json"
        if not path.is_file():
            raise WorkflowError(f"Workflow '{name}' not found")
        return self._read_definition(path, required_profile=not self.allow_unprofiled)

    def _read_definition(self, path: Path, *, required_profile: bool
                         ) -> tuple[dict[str, Any], PromptProfile | None, StudioConfig | None]:
        try:
            definition = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise WorkflowError(f"Cannot read workflow: {type(exc).__name__}") from exc
        errors = self.validate_definition(definition)
        if errors:
            raise WorkflowError("; ".join(errors))
        profile = None
        if "prompt_profile" not in definition:
            if required_profile:
                raise WorkflowError("Workflow requires a prompt_profile reference")
        else:
            try:
                profile = load_prompt_profile(definition["prompt_profile"], self.workflow_dir.parent)
            except PromptProfileError as exc:
                raise WorkflowError(str(exc)) from exc
        studio = None
        if any(step["type"] == "studio_package" for step in definition["steps"]):
            if profile is None:
                raise WorkflowError("A studio package requires the shared prompt profile")
            try:
                studio = load_studio_config(self.workflow_dir.parent)
            except (OSError, ValueError):
                raise WorkflowError("Cannot resolve local creative studio configuration") from None
        return definition, profile, studio

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
                definition, profile, studio = self._read_definition(path, required_profile=True)
                assert profile is not None
                results[path.stem] = []
                covered[path.stem] = {"workflow_sha256": self._definition_hash(definition),
                                      "prompt_profile": profile.metadata(),
                                      **self._studio_evidence(studio)}
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

    @staticmethod
    def _studio_evidence(studio: StudioConfig | None) -> dict[str, Any]:
        return {"creative_studio": studio.metadata()} if studio else {}

    @staticmethod
    def _check_studio_context(studio: StudioConfig | None,
                              business: BusinessContext | None) -> None:
        if studio is not None:
            try:
                validate_business_context(studio, business)
            except (TypeError, ValueError):
                raise WorkflowError("Business context conflicts with creative studio configuration") from None

    def plan(self, name: str, input_text: str, *,
             business_context: Path | str | None = None) -> dict[str, Any]:
        definition, profile, studio = self._load(name)
        business = load_business_context(business_context) if business_context is not None else None
        self._check_studio_context(studio, business)
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
                **self._studio_evidence(studio),
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
            if not isinstance(kind, str) or kind not in {"ai", "github_inventory", "handoff", "approval", "studio_package"}:
                errors.append(f"{prefix} has an unsupported type")
                continue
            if kind == "studio_package" and set(step) - {"id", "type"}:
                errors.append(f"{prefix} studio_package accepts only id and type")
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
        definition, profile, studio = self._load(name)
        business = load_business_context(business_context) if business_context is not None else None
        self._check_studio_context(studio, business)
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
        studio_evidence = self._studio_evidence(studio)
        identity = {"contract": 3, "workflow": name, "workflow_sha256": definition_hash,
                    **profile_evidence,
                    **business_evidence,
                    **studio_evidence,
                    "input": input_text, "allow_external": allow_external,
                    "allow_sensitive": allow_sensitive}
        idempotency_key = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.run_dir / f"{idempotency_key}.json"
        if cache_path.is_file() and not force:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("status") in {"completed", "pending_approval"}:
                if studio is not None:
                    self._verify_cached_studio(cached, definition, name, input_text,
                                               profile, studio, business, idempotency_key)
                cached["reused"] = True
                return cached
        run_id = str(uuid4())
        context: dict[str, Any] = {"input": input_text, "run_id": run_id, "steps": {},
                                   "workflow": {"name": name, "sha256": definition_hash}}
        results: list[dict[str, Any]] = []
        status = "completed"
        for step in definition["steps"]:
            started = time.monotonic()
            started_at = utc_now()
            step_id = step["id"]
            kind = step["type"]
            try:
                result = self._execute_step(step, context, run_id, allow_external, profile, business, studio)
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
                  **studio_evidence,
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

    def _verify_cached_studio(self, cached: dict[str, Any], definition: dict[str, Any],
                              name: str, input_text: str, profile: PromptProfile | None,
                              studio: StudioConfig, business: BusinessContext | None,
                              idempotency_key: str) -> None:
        """Reconcile cached execution with its definition and verified local packets."""
        try:
            run_id = cached.get("run_id")
            if (not isinstance(run_id, str) or not re.fullmatch(
                    r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", run_id)
                    or profile is None or not isinstance(cached.get("steps"), list)):
                raise ValueError()
            expected_profile = profile.metadata()
            expected_business = business.metadata() if business else None
            expected_workflow = {"name": name, "sha256": self._definition_hash(definition)}
            report_keys = {"workflow", "workflow_sha256", "prompt_profile", "profile_status",
                           "creative_studio", "run_id", "idempotency_key", "created_at",
                           "status", "steps", "not_run_steps"}
            if business:
                report_keys.add("business_context")
            if (set(cached) != report_keys
                    or cached.get("workflow") != name
                    or cached.get("workflow_sha256") != expected_workflow["sha256"]
                    or cached.get("idempotency_key") != idempotency_key
                    or cached.get("profile_status") != "resolved"
                    or cached.get("prompt_profile") != expected_profile
                    or cached.get("creative_studio") != studio.metadata()
                    or cached.get("business_context") != expected_business
                    or not isinstance(cached.get("created_at"), str)):
                raise ValueError()
            steps = definition["steps"]
            approval_index = next((index for index, step in enumerate(steps)
                                   if step["type"] == "approval"), None)
            executed_count = len(steps) if approval_index is None else approval_index + 1
            expected_status = "completed" if approval_index is None else "pending_approval"
            if (cached.get("status") != expected_status
                    or len(cached["steps"]) != executed_count
                    or cached.get("not_run_steps") != [step["id"] for step in steps[executed_count:]]):
                raise ValueError()
            runtime_keys = {"id", "type", "started_at", "duration_ms"}
            result_keys = {
                "ai": {"status", "output", "task_id", "provider", "model", "content_sha256"},
                "github_inventory": {"status", "output", "repository_count"},
                "handoff": {"status", "output", "path", "destination", "note"},
                "approval": {"status", "output", "approval_id", "approval"},
            }
            statuses = {"ai": "completed", "github_inventory": "completed",
                        "handoff": "drafted", "studio_package": "drafted", "approval": "pending_approval"}
            for step, recorded in zip(steps[:executed_count], cached["steps"]):
                kind = step["type"]
                if (not isinstance(recorded, dict) or recorded.get("id") != step["id"]
                        or recorded.get("type") != kind or recorded.get("status") != statuses[kind]
                        or not isinstance(recorded.get("started_at"), str)
                        or type(recorded.get("duration_ms")) not in {int, float}
                        or recorded["duration_ms"] < 0 or not isinstance(recorded.get("output"), str)):
                    raise ValueError()
                if kind != "studio_package":
                    if set(recorded) != runtime_keys | result_keys[kind]:
                        raise ValueError()
                    if kind == "handoff":
                        destination = re.sub(r"[^a-zA-Z0-9_-]", "-", step.get("destination", "workspace"))
                        path = self.outbox_dir / f"{run_id}-{step['id']}-{destination}.md"
                        if (recorded["path"] != str(path) or recorded["destination"] != destination
                                or recorded["note"] != "Draft only; no message was sent or published."):
                            raise ValueError()
                    if kind == "approval":
                        approval = recorded["approval"]
                        approval_id = f"{run_id}-{step['id']}"
                        if (not isinstance(approval, dict)
                                or set(approval) != {"id", "run_id", "action", "summary", "status", "created_at"}
                                or recorded["approval_id"] != approval_id or approval["id"] != approval_id
                                or approval["run_id"] != run_id or approval["status"] != "pending"
                                or approval["action"] != step.get("action", step["id"])
                                or approval["summary"] != recorded["output"]
                                or not isinstance(approval["created_at"], str)):
                            raise ValueError()
                    continue
                package = (self.outbox_dir / f"{run_id}-{step['id']}-studio").absolute()
                if recorded.get("package_path") != str(package):
                    raise ValueError()
                verified = verify_packet(package)
                if (verified.get("valid") is not True
                        or verified.get("manifest_sha256") != recorded.get("manifest_sha256")
                        or verified.get("run_id") != run_id
                        or verified.get("studio_config") != studio.metadata()
                        or verified.get("prompt_profile") != expected_profile
                        or verified.get("workflow") != expected_workflow
                        or verified.get("business_context") != expected_business
                        or verified.get("input_sha256") != sha256(input_text.encode("utf-8")).hexdigest()):
                    raise ValueError()
                expected_result = {**verified, "status": "drafted", "package_status": verified["status"],
                                   "output": json.dumps(verified, sort_keys=True)}
                actual_result = {key: value for key, value in recorded.items() if key not in runtime_keys}
                # Compare serialized values so bool/int aliases cannot change assertions.
                if json.dumps(actual_result, sort_keys=True, allow_nan=False) != json.dumps(
                        expected_result, sort_keys=True, allow_nan=False):
                    raise ValueError()
            json.dumps(cached, allow_nan=False)
        except (OSError, TypeError, ValueError, KeyError):
            raise WorkflowError("Cached studio packet is missing or invalid; verify it or create a fresh run with --force") from None

    def _execute_step(self, step: dict[str, Any], context: dict[str, Any],
                      run_id: str, allow_external: bool,
                      profile: PromptProfile | None = None,
                      business_context: BusinessContext | None = None,
                      studio_config: StudioConfig | None = None) -> dict[str, Any]:
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
        elif kind == "studio_package":
            if studio_config is None or profile is None:
                raise WorkflowError("Studio configuration and prompt profile must be resolved")
            package = build_packet(
                studio_config, (self.outbox_dir / f"{run_id}-{step_id}-studio").absolute(),
                run_id=run_id, input_text=context["input"], prompt_profile=profile.metadata(),
                workflow=context["workflow"], business_context=business_context)
            result = {**package, "status": "drafted", "package_status": package["status"],
                      "output": json.dumps(package, sort_keys=True)}
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
