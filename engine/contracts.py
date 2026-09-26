"""Offline contract verification; never contacts a coding provider."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def digest(value: object) -> str:
    """Hash a canonical JSON value, independent of dictionary insertion order."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate(kind: str, value: dict) -> None:
    if kind not in {"work-envelope", "diagnostic-receipt"}:
        raise ValueError("Unknown contract")
    schema = json.loads((SCHEMA_DIR / f"{kind}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)


def verify_round_trip(envelope: dict, receipts: list[dict], results: dict[str, object]) -> dict:
    """Verify two *offline* receipts against one envelope and their provided results.

    The caller must supply independently captured results keyed by provider ID.
    A valid hash proves consistency with those bytes, not provider authenticity.
    """
    validate("work-envelope", envelope)
    if envelope["approval_state"] != "pending":
        raise ValueError("This comparison requires a pending draft envelope")
    expected = {"openai-codex", "github-copilot"}
    providers = [receipt.get("provider") for receipt in receipts]
    if len(receipts) != 2 or set(providers) != expected or set(results) != expected:
        raise ValueError("Exactly one receipt and result per provider are required")
    for receipt in receipts:
        validate("diagnostic-receipt", receipt)
        if any(receipt[key] != envelope[key] for key in ("bundle_id", "repository", "input_hash")):
            raise ValueError("Receipt does not belong to the work envelope")
        if receipt["result_hash"] != digest(results[receipt["provider"]]):
            raise ValueError("Result hash mismatch")
        if receipt["approval_state"] != "pending":
            raise ValueError("Receipt cannot confer approval")
    return {
        "bundle_id": envelope["bundle_id"],
        "providers": sorted(expected),
        "result_agreement": digest(results["openai-codex"]) == digest(results["github-copilot"]),
        "simulated": any(receipt["simulation"] for receipt in receipts),
        "verified_scope": "schema, bundle identity and local result bytes only",
    }
