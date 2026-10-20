"""Hash explicit public-audit artifacts and retain a local MemPalace receipt.

This module makes no network calls. A retained anchor detects later byte changes;
it is not a signed attestation or proof that other services are deployed.
GitHub runners start fresh: receipts belong to one workflow run, with no shared
MemPalace service, restored journal, or cross-run learning history.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping
from uuid import uuid4

from .hermes import MemPalace


REQUIRED_STEPS = ("checkout", "python", "install", "unit_tests", "validation",
                  "doctor", "patrol", "improve")
ARTIFACT_PATHS = ("unit-tests.log", "workflow-validation.json", "jarvis-doctor.json",
                  "jarvis-patrol.json", "jarvis-improvement.json",
                  "data/patrol/latest.json", "data/improvement/latest.json",
                  "data/improvement/journal.jsonl")
MANIFEST_PATH = "data/audit/manifest.json"
ANCHOR_PATH = "data/audit/anchor.json"
LEDGER_PATH = "data/audit/mempalace.sqlite3"
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


class AuditEvidenceError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditEvidenceError("Duplicate JSON object key")
        result[key] = value
    return result


def _json(value: bytes) -> Any:
    return json.loads(value.decode("utf-8"), object_pairs_hook=_object)


def _path(root: Path, relative: str) -> Path:
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise AuditEvidenceError("Audit artifacts must not be symlinks")
    if not path.resolve().is_relative_to(root.resolve()):
        raise AuditEvidenceError("Artifact path leaves the audit directory")
    return path


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def _github(env: Mapping[str, str], issues: list[str]) -> dict[str, Any]:
    fields = {"repository": "GITHUB_REPOSITORY", "sha": "GITHUB_SHA",
              "run_id": "GITHUB_RUN_ID", "run_attempt": "GITHUB_RUN_ATTEMPT",
              "event": "GITHUB_EVENT_NAME", "ref": "GITHUB_REF",
              "pr_head_sha": "JARVIS_AUDIT_PR_HEAD_SHA"}
    context = {key: env.get(variable, "") for key, variable in fields.items()}
    checks = {
        "repository": r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        "run_id": r"[1-9][0-9]*", "run_attempt": r"[1-9][0-9]*",
        "event": r"push|schedule|workflow_dispatch|pull_request",
        "ref": r"refs/(?:heads/[A-Za-z0-9_./-]+|pull/[1-9][0-9]*/merge)",
    }
    for key, pattern in checks.items():
        if not isinstance(context[key], str) or not re.fullmatch(pattern, context[key]):
            context[key] = ""
            issues.append(f"invalid_github_{key}")
    for key in ("sha", "pr_head_sha"):
        required = key == "sha" or context["event"] == "pull_request"
        value = context[key]
        if not isinstance(value, str) or (value and not _SHA.fullmatch(value)) or (required and not value):
            context[key] = ""
            issues.append(f"invalid_github_{key}")
    context["run_url"] = (
        f"https://github.com/{context['repository']}/actions/runs/{context['run_id']}"
        if context["repository"] and context["run_id"] else None)
    return context


def _report_checks(data: dict[str, bytes], owner: str,
                   issues: list[str]) -> tuple[dict[str, Any], str | None]:
    parsed = {}
    for path in ARTIFACT_PATHS:
        if path.endswith(".json") and path in data:
            try:
                value = _json(data[path])
                if not isinstance(value, dict):
                    raise AuditEvidenceError("Report must be an object")
                parsed[path] = value
            except (ValueError, UnicodeDecodeError):
                issues.append(f"invalid_report:{path}")
    summary: dict[str, Any] = {}

    def check(condition: bool, code: str) -> None:
        if not condition:
            issues.append(code)

    test_log = data.get("unit-tests.log", b"").decode("utf-8", errors="replace")
    tests = re.search(r"^Ran ([0-9]+) tests? in [^\n]+\n\s*\nOK\s*\Z",
                      test_log, re.MULTILINE)
    check(bool(tests) and int(tests.group(1)) > 0, "unit_test_summary_not_all_passed")
    summary["tests_passed"] = int(tests.group(1)) if tests else None

    validation = parsed.get("workflow-validation.json", {})
    workflows = validation.get("workflows")
    check(validation.get("valid") is True and isinstance(workflows, dict)
          and bool(workflows) and all(value == [] for value in workflows.values()),
          "workflow_validation_not_passed")
    doctor = parsed.get("jarvis-doctor.json", {})
    checks = doctor.get("checks")
    check(doctor.get("status") == "ready_local" and isinstance(checks, list)
          and bool(checks) and all(isinstance(item, dict) and item.get("passed") is True
                                  for item in checks), "local_readiness_not_passed")

    patrol = parsed.get("data/patrol/latest.json", {})
    count = patrol.get("repositories_scanned")
    policy = patrol.get("policy", {})
    findings = patrol.get("findings")
    read_only = (isinstance(policy, dict) and all(policy.get(key) is False for key in (
        "allow_repository_writes", "allow_merges", "allow_deployments",
        "allow_external_messages", "allow_spending")))
    limit = policy.get("max_repositories") if isinstance(policy, dict) else None
    check(patrol.get("mode") == "read_only" and read_only, "patrol_not_read_only")
    check(type(count) is int and type(limit) is int and 0 <= count <= limit <= 250,
          "patrol_repository_bound_invalid")
    public_findings = isinstance(findings, list) and all(
        isinstance(item, dict) and isinstance(item.get("repository"), str)
        and item["repository"].split("/", 1)[0].casefold() == owner.casefold()
        and item.get("code") != "private-data-boundary" for item in findings)
    check(public_findings, "patrol_scope_not_public_owner")
    summary["repositories_scanned"] = count if type(count) is int else None
    summary["findings"] = len(findings) if isinstance(findings, list) else None
    observed_at = patrol.get("created_at")
    try:
        if not isinstance(observed_at, str) or datetime.fromisoformat(
                observed_at.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Timestamp needs a timezone")
    except ValueError:
        observed_at = None
        issues.append("patrol_observation_time_invalid")

    improvement = parsed.get("data/improvement/latest.json", {})
    learning = improvement.get("learning_contract", {})
    proposals = improvement.get("proposals")
    check(improvement.get("mode") == "proposal_only" and isinstance(learning, dict)
          and learning.get("production_mutation") is False
          and learning.get("model_weights_changed") is False,
          "improvement_not_proposal_only")
    check(isinstance(proposals, list) and len(proposals) <= 50 and all(
        isinstance(item, dict) and item.get("automatic_execution") is False
        for item in proposals), "improvement_execution_or_bound_invalid")
    check(improvement.get("observation_count") == summary["findings"]
          and "data/patrol/latest.json" in data
          and improvement.get("source_sha256") == _digest(data["data/patrol/latest.json"]),
          "improvement_source_mismatch")

    for console, stored in (("jarvis-patrol.json", patrol),
                            ("jarvis-improvement.json", improvement)):
        output = parsed.get(console, {}).copy()
        output.pop("report_path", None)
        check(bool(stored) and output == stored, f"console_report_mismatch:{console}")
    try:
        journal = [_json(line) for line in data.get("data/improvement/journal.jsonl", b"").splitlines()
                   if line.strip()]
        last = journal[-1]
        check(isinstance(last, dict) and all(last.get(key) == improvement.get(key)
              for key in ("cycle_id", "created_at", "source_sha256", "observation_count"))
              and isinstance(proposals, list) and last.get("proposal_count") == len(proposals),
              "improvement_journal_mismatch")
    except (ValueError, UnicodeDecodeError, IndexError):
        issues.append("improvement_journal_invalid")
    return summary, observed_at


def create_evidence(root: Path, outcomes: Mapping[str, str], *, owner: str = "lippytm",
                    env: Mapping[str, str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    issues: list[str] = []
    context = _github(os.environ if env is None else env, issues)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", owner):
        raise AuditEvidenceError("Invalid public inventory owner")
    steps = {step: outcomes.get(step, "missing") for step in REQUIRED_STEPS}
    for step, outcome in steps.items():
        if outcome not in {"success", "failure", "cancelled", "skipped", "missing"}:
            steps[step] = "unknown"
        if outcome != "success":
            issues.append(f"required_step_not_success:{step}")
    data, artifacts = {}, []
    for relative in ARTIFACT_PATHS:
        try:
            path = _path(root, relative)
            content = path.read_bytes()
            data[relative] = content
            artifacts.append({"path": relative, "present": True, "bytes": len(content),
                              "sha256": _digest(content)})
        except (OSError, AuditEvidenceError):
            issues.append(f"missing_or_unsafe_artifact:{relative}")
            artifacts.append({"path": relative, "present": False})
    summary, observed_at = _report_checks(data, owner, issues)
    execution_scope = ("pull_request_public_metadata_audit" if context["event"] == "pull_request"
                       else "main_public_metadata_audit" if context["ref"] == "refs/heads/main"
                       else "branch_public_metadata_audit")
    payload = {"schema": "jarvis.public-audit.v1", "generated_at": datetime.now(timezone.utc).isoformat(),
               "observed_at": observed_at, "github": context, "execution_scope": execution_scope,
               "scope": {"owner": owner, "data": "public_repository_metadata",
                         "repository_ci_inspected": False, "paid_provider_calls": False,
                         "deployment_performed": False,
                         "memory": "per_workflow_run_local_mem_palace",
                         "cross_run_history_restored": False},
               "required_steps": steps, "artifacts": artifacts, "summary": summary,
               "operational_success": not issues, "issues": issues,
               "success_meaning": "Required audit steps and public metadata reports passed; no deployment or cross-provider readiness is attested."}
    payload_hash = _digest(_canonical(payload))
    run_id = (f"github-{context['run_id']}-attempt-{context['run_attempt']}"
              if context["run_id"] and context["run_attempt"] else f"local-{uuid4()}")
    ledger_path = _path(root, LEDGER_PATH)
    ledger = MemPalace(ledger_path)
    head = ledger.append(run_id, "public-metadata-audit", {
        "payload_sha256": payload_hash, "github_sha": context["sha"],
        "execution_scope": execution_scope, "operational_success": not issues})
    manifest = {"payload": payload, "receipt": {"run_id": run_id, "head_sha256": head,
                "payload_sha256": payload_hash, "ledger_path": LEDGER_PATH}}
    manifest_path = _path(root, MANIFEST_PATH)
    _write_json(manifest_path, manifest)
    anchor = {"schema": "jarvis.audit-anchor.v1", "run_id": run_id,
              "head_sha256": head, "payload_sha256": payload_hash,
              "manifest_sha256": _digest(manifest_path.read_bytes()),
              "ledger_sha256": _digest(ledger_path.read_bytes())}
    _write_json(_path(root, ANCHOR_PATH), anchor)
    verify_evidence(root)
    return manifest


def verify_evidence(root: Path) -> dict[str, Any]:
    root = root.resolve()
    try:
        manifest_bytes = _path(root, MANIFEST_PATH).read_bytes()
        manifest = _json(manifest_bytes)
        anchor = _json(_path(root, ANCHOR_PATH).read_bytes())
        payload, receipt = manifest["payload"], manifest["receipt"]
        payload_hash = _digest(_canonical(payload))
        if (anchor["schema"] != "jarvis.audit-anchor.v1"
                or payload["schema"] != "jarvis.public-audit.v1"
                or anchor["manifest_sha256"] != _digest(manifest_bytes)
                or anchor["payload_sha256"] != payload_hash
                or receipt["payload_sha256"] != payload_hash
                or receipt["ledger_path"] != LEDGER_PATH
                or anchor["run_id"] != receipt["run_id"]
                or anchor["head_sha256"] != receipt["head_sha256"]):
            raise AuditEvidenceError("Manifest does not match retained anchor")
        ledger_path = _path(root, LEDGER_PATH)
        if anchor["ledger_sha256"] != _digest(ledger_path.read_bytes()):
            raise AuditEvidenceError("MemPalace bytes differ from retained anchor")
        history = MemPalace(ledger_path).history(receipt["run_id"], expected_head=anchor["head_sha256"])
        expected_receipt = {"payload_sha256": payload_hash, "github_sha": payload["github"]["sha"],
                            "execution_scope": payload["execution_scope"],
                            "operational_success": payload["operational_success"]}
        if history[-1]["stage"] != "public-metadata-audit" or history[-1]["evidence"] != expected_receipt:
            raise AuditEvidenceError("MemPalace receipt does not match audit")
        artifacts = payload["artifacts"]
        if [item["path"] for item in artifacts] != list(ARTIFACT_PATHS):
            raise AuditEvidenceError("Unexpected audit artifact list")
        for artifact in artifacts:
            path = _path(root, artifact["path"])
            if artifact["present"] is True:
                content = path.read_bytes()
                if artifact["bytes"] != len(content) or artifact["sha256"] != _digest(content):
                    raise AuditEvidenceError("Audit artifact differs from retained anchor")
            elif artifact["present"] is not False or path.exists():
                raise AuditEvidenceError("Audit artifact presence changed")
        if payload["operational_success"] is True and (payload["issues"] or any(
                payload["required_steps"].get(step) != "success" for step in REQUIRED_STEPS)
                or not all(item["present"] is True for item in artifacts)):
            raise AuditEvidenceError("Successful audit has incomplete evidence")
        return {"integrity_valid": True, "operational_success": payload["operational_success"],
                "execution_scope": payload["execution_scope"], "run_url": payload["github"]["run_url"]}
    except (OSError, KeyError, TypeError, UnicodeDecodeError, ValueError) as exc:
        raise AuditEvidenceError("Audit evidence verification failed") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--owner", default="lippytm")
    parser.add_argument("--step", action="append", default=[], metavar="ID=OUTCOME")
    parser.add_argument("--require-success", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            outcomes = {}
            for value in args.step:
                key, outcome = value.split("=", 1)
                if key not in REQUIRED_STEPS or key in outcomes:
                    raise AuditEvidenceError("Invalid or duplicate required step")
                outcomes[key] = outcome
            manifest = create_evidence(args.root, outcomes, owner=args.owner)
            print(json.dumps({"manifest": MANIFEST_PATH, "anchor": ANCHOR_PATH,
                              "operational_success": manifest["payload"]["operational_success"],
                              "issues": manifest["payload"]["issues"]}, indent=2))
            return 0 if manifest["payload"]["operational_success"] else 1
        result = verify_evidence(args.root)
        print(json.dumps(result, indent=2))
        return 1 if args.require_success and not result["operational_success"] else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"integrity_valid": False, "error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
