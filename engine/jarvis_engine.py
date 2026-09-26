from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


PROVIDERS = {
    "openai-codex": {"capabilities": {"plan", "implement", "test", "diagnose", "review", "patch"}, "status": "pilot"},
    "github-copilot": {"capabilities": {"plan", "implement", "test", "document", "prepare_pull_request"}, "status": "pilot"},
    "gitlab": {"capabilities": {"repository", "merge_request", "pipeline"}, "status": "adapter-planned"},
    "bitbucket": {"capabilities": {"repository", "pull_request", "pipeline"}, "status": "adapter-planned"},
    "azure-devops": {"capabilities": {"repository", "work_item", "pull_request", "pipeline"}, "status": "adapter-planned"},
    "generic-git": {"capabilities": {"inspect", "diff", "history"}, "status": "read-only"},
}


def run_git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def inspect_repository(repository: Path, max_commits: int = 25) -> dict:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError("Repository path must be a directory.")
    inside = run_git(repository, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        raise ValueError("Path is not a Git work tree.")
    top_level = Path(run_git(repository, "rev-parse", "--show-toplevel")).resolve()
    branch = run_git(repository, "branch", "--show-current")
    status_lines = [line for line in run_git(repository, "status", "--porcelain=v1").splitlines() if line]
    log_output = run_git(
        repository,
        "log",
        f"--max-count={max_commits}",
        "--date=iso-strict",
        "--pretty=format:%H%x1f%P%x1f%an%x1f%ad%x1f%s",
    )
    commits = []
    for line in log_output.splitlines():
        commit, parents, author, authored_at, subject = line.split("\x1f", 4)
        commits.append({
            "commit": commit,
            "parents": parents.split() if parents else [],
            "author": author,
            "authored_at": authored_at,
            "subject": subject,
        })
    return {
        "schema_version": "1.0.0",
        "mode": "read-only",
        "repository": str(top_level),
        "branch": branch,
        "dirty": bool(status_lines),
        "status": status_lines,
        "commits": commits,
    }


def route(capability: str) -> list[str]:
    return sorted(
        provider
        for provider, config in PROVIDERS.items()
        if capability in config["capabilities"] and config["status"] in {"pilot", "read-only"}
    )


@dataclass(frozen=True)
class WorkEnvelope:
    bundle_id: str
    repository: str
    goal: str
    scope: str
    risk_class: str
    allowed_tools: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    acceptance_tests: tuple[str, ...]
    approval_state: str
    input_hash: str
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return asdict(self)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis-engine")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("providers")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("repository", type=Path)
    inspect.add_argument("--max-commits", type=int, default=25)
    routing = commands.add_parser("route")
    routing.add_argument("capability")
    args = parser.parse_args(argv)

    if args.command == "providers":
        print(json.dumps(PROVIDERS, indent=2, default=sorted))
        return 0
    if args.command == "route":
        print(json.dumps({"capability": args.capability, "providers": route(args.capability)}, indent=2))
        return 0
    if args.max_commits < 1 or args.max_commits > 100:
        parser.error("--max-commits must be between 1 and 100")
    print(json.dumps(inspect_repository(args.repository, args.max_commits), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
