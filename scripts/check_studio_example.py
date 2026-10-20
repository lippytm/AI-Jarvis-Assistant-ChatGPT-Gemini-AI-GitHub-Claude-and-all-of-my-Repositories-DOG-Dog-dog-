#!/usr/bin/env python3
"""Run the checked-in public studio pilot and retain bounded local evidence.

This exercises real CLI calls, not a provider or publishing integration. GitHub
CI retains the outputs and its source identity; local dirty worktrees are labeled.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/studio-workforce-pilot"


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def run_cli(arguments):
    result = subprocess.run([sys.executable, "-m", "jarvis", *map(str, arguments), "--json"],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError("Public studio example CLI check failed")
    return json.loads(result.stdout)


def git_output(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    checkout_revision = git_output("rev-parse", "HEAD")
    clean = not bool(git_output("status", "--porcelain"))
    if args.require_clean and not clean:
        raise RuntimeError("Studio evidence requires a clean reviewed checkout")
    source_revision = os.environ.get("JARVIS_STUDIO_SOURCE_SHA")
    if source_revision is not None and not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise RuntimeError("Invalid CI source revision")
    output = args.output.absolute()
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    economics_input = (EXAMPLE / "economics.json").read_bytes()
    built = run_cli(["studio-plan", EXAMPLE / "production-brief.json", "--output", output / "packet"])
    verified = run_cli(["verify-studio-plan", output / "packet"])
    economics = run_cli(["studio-economics", EXAMPLE / "economics.json"])
    if built != verified or verified["status"] != "prepared_for_review" or verified["blockers"]:
        raise RuntimeError("Studio example did not produce matching source-ready verification")
    expected_execution = {"provider_calls": 0, "media_rendered": False, "published": False,
                          "external_handoff_sent": False, "approval_granted": False,
                          "shared_memory_sync": False}
    if (verified["release_status"] != "release_blocked" or verified["execution"] != expected_execution
            or verified["file_count"] != 13 or len(verified["assets"]) != 4
            or len(verified["formats"]) != 4):
        raise RuntimeError("Studio example scope or inventory changed")
    canonical_input = json.dumps(json.loads(economics_input), sort_keys=True,
                                separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if (economics["status"] != "hypothetical_scenarios_only"
            or economics["input_sha256"] != sha256(canonical_input).hexdigest()
            or economics["qualifications"]["measured_actuals_included"]
            or economics["qualifications"]["spend_approved"]
            or economics["qualifications"]["provider_calls"] != 0):
        raise RuntimeError("Studio economics evidence or qualifications changed")
    receipts = {"build.json": json_bytes(built), "verification.json": json_bytes(verified),
                "economics-input.json": economics_input,
                "economics-report.json": json_bytes(economics)}
    for name, raw in receipts.items():
        (output / name).write_bytes(raw)
    evidence = {
        "schema": "jarvis.studio-example-check.v1", "status": "passed",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local_public_example_source_packet_and_hypothetical_economics",
        "checkout_revision": checkout_revision,
        "event_source_revision": source_revision,
        "source_worktree_clean": clean,
        "source_state": "clean_checkout" if clean else "working_tree_with_changes",
        "production": {key: verified[key] for key in ("project_id", "revision", "manifest_sha256",
                       "brief_sha256", "file_count", "status", "release_status", "studio_config", "prompt_profile")},
        "execution": expected_execution,
        "economics": {"status": economics["status"], "input_sha256": economics["input_sha256"],
                      "scenario_count": len(economics["scenarios"]),
                      "assumptions_status": economics["qualifications"]["assumptions_status"]},
        "receipts": [{"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
                     for name, raw in sorted(receipts.items())],
        "limits": ["No independent content QA or reader outcomes established.",
                   "No rendered media, account connection, delivery, release, or actual sale established.",
                   "Hashes establish local consistency, not signatures or authenticated author identity.",
                   "A local dirty-worktree check does not bind its changes to the checkout commit."],
    }
    (output / "evidence.json").write_bytes(json_bytes(evidence))
    print(json.dumps(evidence, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Studio example check failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2) from None
