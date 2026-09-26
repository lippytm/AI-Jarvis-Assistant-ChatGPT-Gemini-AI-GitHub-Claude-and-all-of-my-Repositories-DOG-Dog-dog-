"""Generic offline fleet gateway; identities arrive from a private local roster."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .hermes import MemPalace, Stage, run_swarm

ROOT = Path(__file__).resolve().parents[2]

def load_registry(path: Path) -> dict:
    registry = json.loads(path.read_text(encoding="utf-8"))
    platform, personal = registry["platform"], registry["personal"]
    ids = [brain["id"] for brain in platform + personal]
    if (len(platform), len(personal), len(set(ids))) != (22, 7, 29):
        raise ValueError("Expected 22 platform and 7 personal unique identities")
    if any(not re.fullmatch(r"B\d\d", b["id"]) for b in platform):
        raise ValueError("Invalid platform identity")
    if any(not re.fullmatch(r"P\d\d", b["id"]) for b in personal):
        raise ValueError("Invalid personal identity")
    return registry

class BrainGateway:
    def __init__(self, root: Path, registry: dict):
        self.root = root
        self.brains = {brain["id"]: brain for group in ("platform", "personal") for brain in registry[group]}
        if len(self.brains) != 29:
            raise ValueError("Invalid roster")

    def mission(self, brain_id: str, payload: dict, *, destination: str | None = None) -> dict:
        if brain_id not in self.brains:
            raise ValueError("Unknown brain identity")
        if destination is not None:
            if destination not in self.brains:
                raise ValueError("Unknown destination brain")
            if brain_id[0] != destination[0]:
                raise PermissionError("Private and platform fleets cannot exchange data")
        ledger = MemPalace(self.root / brain_id / "mempalace.sqlite")
        output = {"brain_id": brain_id, "scope": "personal" if brain_id.startswith("P") else "platform",
                  "input_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                  "status": "mock-only", "destination": destination}
        return run_swarm([Stage("evaluate", "chatgpt-business"), Stage("release", "hostinger", "publish")],
                         payload, {"chatgpt-business": lambda _: output}, ledger)

def hostinger_viability(registry: dict, capabilities: dict) -> dict:
    if len(registry["platform"]) != 22 or len(registry["personal"]) != 7:
        raise ValueError("Invalid roster")
    entries = capabilities["capabilities"]
    if len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate Hostinger capability")
    enabled = [entry["id"] for entry in entries
               if entry["account_connection"] == "verified" and entry["implementation"] == "verified adapter"]
    return {"brains": 29, "builder_capabilities": len(entries), "possible_pairs": 29 * len(entries),
            "live_platform_pairs": 22 * len(enabled), "personal_pairs": 0,
            "enabled_operations": enabled, "status": "planning matrix" if not enabled else "verified platform capabilities only"}
