from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import Settings
from .control_tower import ControlTower
from .providers import ProviderError
from .workflows import WorkflowError, WorkflowRunner
from .approvals import ApprovalQueue
from .bundles import BundleError, RunBundler
from .doctor import Doctor
from .intake import IntakeBridge, IntakeError
from .patrol import Patrol
from .improvement import ImprovementLoop
from .problem_intake import Problem, SolvabilityEngine
from .viability import ViabilityEngine
from .prevention import PreventionLibrary
from .outcomes import OutcomeEvidence
from .business_context import load_business_context
from .studio_production import build_production_plan, verify_production_plan
from .studio_economics import load_studio_economics


def _emit(value: Any, as_json: bool) -> None:
    print(json.dumps(value, indent=2, default=str) if as_json or not isinstance(value, str) else value)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="jarvis", description="Jarvis Control Tower")
    commands = root.add_subparsers(dest="command", required=True)
    health = commands.add_parser("health", help="Check local configuration")
    health.add_argument("--json", action="store_true")
    ask = commands.add_parser("ask", help="Run and record an AI task")
    ask.add_argument("prompt")
    ask.add_argument("--provider")
    ask.add_argument("--system")
    ask.add_argument("--json", action="store_true")
    history = commands.add_parser("history", help="List recorded tasks")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--json", action="store_true")
    show = commands.add_parser("show", help="Show one task and its provenance")
    show.add_argument("task_id")
    show.add_argument("--json", action="store_true")
    workflows = commands.add_parser("workflows", help="List automated workflows")
    workflows.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="Run an automated workflow")
    run.add_argument("workflow")
    run.add_argument("input")
    run.add_argument("--allow-external", action="store_true",
                     help="Allow configured providers to make billable network requests")
    run.add_argument("--json", action="store_true")
    run.add_argument("--force", action="store_true",
                     help="Ignore an existing idempotent run and execute again")
    run.add_argument("--allow-sensitive", action="store_true",
                     help="Allow detected credentials in input (strongly discouraged)")
    run.add_argument("--business-context", metavar="PATH",
                     help="Add an allowed projection of a local owner business record as task data")
    plan = commands.add_parser("plan", help="Preview a workflow without executing it")
    plan.add_argument("workflow")
    plan.add_argument("input")
    plan.add_argument("--json", action="store_true")
    plan.add_argument("--business-context", metavar="PATH",
                      help="Identify a local business-context projection without executing steps")
    business_context = commands.add_parser("business-context", help="Export sanitized local owner business facts")
    business_context.add_argument("path", metavar="PATH")
    business_context.add_argument("--json", action="store_true")
    studio_plan = commands.add_parser("studio-plan", help="Build a local production packet from a filled brief and text sources")
    studio_plan.add_argument("path", metavar="BRIEF")
    studio_plan.add_argument("--output", required=True, metavar="DIRECTORY",
                             help="Fresh local output directory; existing paths are refused")
    studio_plan.add_argument("--json", action="store_true")
    studio_verify = commands.add_parser("verify-studio-plan", help="Verify an archived local production packet")
    studio_verify.add_argument("path", metavar="DIRECTORY")
    studio_verify.add_argument("--json", action="store_true")
    studio_economics = commands.add_parser("studio-economics", help="Evaluate hypothetical studio costs and unit economics")
    studio_economics.add_argument("path", metavar="ASSUMPTIONS")
    studio_economics.add_argument("--json", action="store_true")
    validate = commands.add_parser("validate-workflows", help="Validate every workflow definition")
    validate.add_argument("--json", action="store_true")
    approvals = commands.add_parser("approvals", help="List approval requests")
    approvals.add_argument("--status", choices=["pending", "approved"])
    approvals.add_argument("--json", action="store_true")
    approve = commands.add_parser("approve", help="Approve a queued action without executing it")
    approve.add_argument("approval_id")
    approve.add_argument("--json", action="store_true")
    bundle = commands.add_parser("bundle", help="Create a portable verified run bundle")
    bundle.add_argument("run_id")
    bundle.add_argument("--json", action="store_true")
    verify = commands.add_parser("verify-bundle", help="Verify a Jarvis transfer bundle")
    verify.add_argument("path")
    verify.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor", help="Run a non-billable readiness audit")
    doctor.add_argument("--json", action="store_true")
    intake = commands.add_parser("intake", help="Capture a file from another AI workspace")
    intake.add_argument("source", help="Source system, such as gemini or claude")
    intake.add_argument("path", help="UTF-8 text, Markdown, or JSON export")
    intake.add_argument("--title")
    intake.add_argument("--allow-sensitive", action="store_true")
    intake.add_argument("--json", action="store_true")
    intakes = commands.add_parser("intakes", help="List captured cross-system intakes")
    intakes.add_argument("--json", action="store_true")
    patrol = commands.add_parser("patrol", help="Run a bounded read-only repository patrol")
    patrol.add_argument("--owner", default=None)
    patrol.add_argument("--json", action="store_true")
    improve = commands.add_parser("improve", help="Turn diagnostic evidence into reviewable experiments")
    improve.add_argument("path", help="JSON patrol or observation report")
    improve.add_argument("--json", action="store_true")
    assess = commands.add_parser("assess-problem", help="Classify and safely route a problem")
    assess.add_argument("path", help="Problem intake JSON")
    assess.add_argument("--json", action="store_true")
    viability = commands.add_parser("assess-viability", help="Run preventive design and conflict gates")
    viability.add_argument("path", help="Viability design JSON")
    viability.add_argument("--json", action="store_true")
    controls = commands.add_parser("recommend-controls", help="Select sourced preventive controls")
    controls.add_argument("--domain", action="append", default=[])
    controls.add_argument("--json", action="store_true")
    outcomes = commands.add_parser("rank-outcomes", help="Rank controls from observed outcome evidence")
    outcomes.add_argument("path", help="Append-only JSONL outcome ledger")
    outcomes.add_argument("--json", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "business-context":
            _emit(load_business_context(args.path).as_dict(), args.json)
            return 0
        if args.command == "studio-plan":
            result = build_production_plan(Path.cwd(), Path(args.path), Path(args.output))
            _emit(result, args.json)
            return 0 if result["status"] == "prepared_for_review" else 1
        if args.command == "verify-studio-plan":
            _emit(verify_production_plan(Path(args.path)), args.json)
            return 0
        if args.command == "studio-economics":
            _emit(load_studio_economics(Path(args.path)), args.json)
            return 0
        tower = ControlTower(Settings.from_env())
        if args.command == "health":
            _emit(tower.health(), args.json)
        elif args.command == "ask":
            response = tower.run(args.prompt, args.provider, args.system)
            _emit(response.as_dict() if args.json else response.content, args.json)
        elif args.command == "history":
            if not 1 <= args.limit <= 1000:
                raise ValueError("--limit must be between 1 and 1000")
            _emit(tower.ledger.history(args.limit), args.json)
        elif args.command == "show":
            record = tower.ledger.get(args.task_id)
            if record is None:
                print("Task not found", file=sys.stderr)
                return 1
            _emit(record, args.json)
        elif args.command == "workflows":
            _emit(WorkflowRunner(tower).list(), args.json)
        elif args.command == "run":
            result = WorkflowRunner(tower).run(args.workflow, args.input,
                                                args.allow_external, args.force,
                                                args.allow_sensitive,
                                                business_context=args.business_context)
            _emit(result, args.json)
            return 0 if result["status"] == "completed" else 1
        elif args.command == "plan":
            _emit(WorkflowRunner(tower).plan(args.workflow, args.input,
                                             business_context=args.business_context), args.json)
        elif args.command == "validate-workflows":
            result = WorkflowRunner(tower).validate_catalog()
            _emit(result, args.json)
            return 0 if result["valid"] else 1
        elif args.command == "approvals":
            _emit(ApprovalQueue().list(args.status), args.json)
        elif args.command == "approve":
            _emit(ApprovalQueue().approve(args.approval_id), args.json)
        elif args.command == "bundle":
            _emit(RunBundler().create(args.run_id), args.json)
        elif args.command == "verify-bundle":
            _emit(RunBundler().verify(Path(args.path)), args.json)
        elif args.command == "doctor":
            result = Doctor(tower).run()
            _emit(result, args.json)
            return 0 if result["status"] == "ready_local" else 1
        elif args.command == "intake":
            _emit(IntakeBridge().capture(args.source, Path(args.path), args.title,
                                           args.allow_sensitive), args.json)
        elif args.command == "intakes":
            _emit(IntakeBridge().list(), args.json)
        elif args.command == "patrol":
            _emit(Patrol().run(args.owner), args.json)
        elif args.command == "improve":
            _emit(ImprovementLoop().run(Path(args.path)), args.json)
        elif args.command == "assess-problem":
            payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
            _emit(SolvabilityEngine().assess(Problem.from_dict(payload)), args.json)
        elif args.command == "assess-viability":
            payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
            _emit(ViabilityEngine().assess(payload).as_dict(), args.json)
        elif args.command == "recommend-controls":
            _emit(PreventionLibrary().recommend(args.domain), args.json)
        elif args.command == "rank-outcomes":
            _emit(OutcomeEvidence().evaluate(Path(args.path)), args.json)
        return 0
    except (ProviderError, WorkflowError, BundleError, IntakeError, ValueError) as exc:
        print(f"Jarvis error: {exc}", file=sys.stderr)
        return 2
