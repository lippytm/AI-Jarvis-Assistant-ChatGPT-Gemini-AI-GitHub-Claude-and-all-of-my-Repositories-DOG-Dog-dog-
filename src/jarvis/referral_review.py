"""Offline referral-registry validation and MemPalace review receipts.

No network, publishing, applications, payments or provider invocation is implemented.
A status written in JSON is an assertion, not verified access or authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from .hermes import MemPalace

VERSION = "0.1.0"
EXPECTED = {
    "7figures-customer": ("customer_referral", "http://www.7figurescredit.com?a_aid=lippytm"),
    "7figures-partner": ("partner_recruitment", "http://join.7figurespartners.com/?a_aid=lippytm"),
    "lendtrack-partner": ("partner_recruitment", "http://lendtrack.ai/join/lippytmai"),
}
GATES = frozenset({"https_destination", "account_membership", "referral_attribution",
                   "program_terms", "public_copy", "owner_release"})
ROOT_KEYS = {"schema_version", "mode", "network_enabled", "auto_publish", "spend_authorized", "programs"}
PROGRAM_KEYS = {"id", "purpose", "original_url", "https_candidate_url", "link_check",
                "gates", "commission_rate", "payout_status"}


def digest(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def validate_registry(data: object) -> None:
    """Validate this three-program pilot, not arbitrary affiliate programs."""
    if not isinstance(data, dict) or set(data) != ROOT_KEYS:
        raise ValueError("Invalid registry fields")
    if data["schema_version"] != "1.0.0" or data["mode"] != "draft_only":
        raise ValueError("Unsupported schema or non-draft mode")
    if any(data[key] is not False for key in ("network_enabled", "auto_publish", "spend_authorized")):
        raise ValueError("Network, publication and spending must remain disabled")
    programs = data["programs"]
    if not isinstance(programs, list) or len(programs) != len(EXPECTED):
        raise ValueError("Expected exactly three separate referral programs")
    seen = set()
    for program in programs:
        if not isinstance(program, dict) or set(program) != PROGRAM_KEYS:
            raise ValueError("Invalid program fields")
        identity = program["id"]
        if not isinstance(identity, str) or identity not in EXPECTED or identity in seen:
            raise ValueError("Unknown or duplicate program identifier")
        seen.add(identity)
        purpose, original = EXPECTED[identity]
        if program["purpose"] != purpose or program["original_url"] != original:
            raise ValueError("Referral purpose or owner-supplied URL changed")
        if program["https_candidate_url"] != "https:" + original[5:]:
            raise ValueError("HTTPS candidate must preserve host, path and attribution")
        gates = program["gates"]
        if not isinstance(gates, dict) or set(gates) != GATES:
            raise ValueError("Missing or unexpected review gates")
        if any(not isinstance(value, str) or value not in {"unverified", "verified", "blocked"}
               for value in gates.values()):
            raise ValueError("Invalid gate assertion")
        if program["link_check"] not in ("not_checked", "fetch_failed_in_this_session", "public_page_retrieved"):
            raise ValueError("Unsupported link-check assertion")
        if program["commission_rate"] is not None or program["payout_status"] != "unverified":
            raise ValueError("This draft pilot does not establish commissions or payouts")


def build_review(data: object, ledger: MemPalace | None = None) -> dict:
    """Produce a local review packet. Even all-'verified' flags grant no release."""
    validate_registry(data)
    report = {
        "tool_version": VERSION, "mode": "offline_review",
        "registry_sha256": digest(data), "live_execution": False,
        "publication_authorized": False, "spending_authorized": False,
        "provider_calls": 0, "status": "pending_independent_review",
        "programs": [{"id": p["id"], "purpose": p["purpose"],
                      "original_url": p["original_url"],
                      "https_candidate_url": p["https_candidate_url"],
                      "asserted_gates": dict(p["gates"]),
                      "unresolved_gates": sorted(k for k, v in p["gates"].items() if v != "verified")}
                     for p in data["programs"]],
        "required_next_action": "Review source evidence, actual account attribution and owner scope; do not publish from this packet.",
    }
    if ledger is not None:
        run_id = str(uuid4())
        anchor = ledger.append(run_id, "referral_registry_review", {
            "action": "local_validate", "status": "local_validation_passed",
            "tool_version": VERSION, "input_sha256": digest(data),
            "output_sha256": digest(report), "mode": "offline_review"})
        events = ledger.history(run_id, expected_head=anchor)
        report["receipt"] = {"run_id": run_id, "head_sha256": anchor,
                             "chain_valid": bool(events), "scope": "local_metadata_only"}
    return report


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_registry(path: Path) -> object:
    with path.open("rb") as stream:
        data = stream.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Registry exceeds one million bytes")
    return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--ledger", type=Path, help="Private local SQLite evidence path")
    args = parser.parse_args()
    try:
        data = load_registry(args.registry)
        validate_registry(data)  # Fail before creating a ledger for invalid input.
        ledger = MemPalace(args.ledger) if args.ledger is not None else None
        report = build_review(data, ledger)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Review failed ({type(exc).__name__}); no release authorized.\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
