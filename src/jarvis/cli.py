from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .config import Settings
from .control_tower import ControlTower
from .providers import ProviderError


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
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
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
        return 0
    except (ProviderError, ValueError) as exc:
        print(f"Jarvis error: {exc}", file=sys.stderr)
        return 2
