"""Bounded Hermes handoffs with a local MemPalace evidence ledger.

Providers are explicit callables; this module has no autonomous network or publish path.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4


STATIONS = frozenset({"gemini-ai", "chatgpt-business", "github", "claude-coworker", "hostinger"})
WRITE_ACTIONS = frozenset({"merge", "deploy", "publish", "spend", "message", "delete", "credential_access"})


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class Stage:
    id: str
    station: str
    action: str = "draft"


class MemPalace:
    """Store evidence metadata only, with a per-run SHA-256 chain."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS events (run_id TEXT NOT NULL, sequence INTEGER NOT NULL, stage TEXT NOT NULL, evidence_json TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL, PRIMARY KEY (run_id, sequence))")

    def append(self, run_id: str, stage: str, evidence: dict) -> str:
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute("SELECT sequence, entry_hash FROM events WHERE run_id=? ORDER BY sequence DESC LIMIT 1", (run_id,)).fetchone()
            sequence, previous = (last[0] + 1, last[1]) if last else (0, "0" * 64)
            entry = {"run_id": run_id, "sequence": sequence, "stage": stage,
                     "evidence": evidence, "previous_hash": previous}
            digest = _hash(entry)
            db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                       (run_id, sequence, stage, _canonical(evidence).decode(), previous, digest))
        return digest

    def verify(self, run_id: str) -> bool:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT sequence, stage, evidence_json, previous_hash, entry_hash FROM events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
        previous = "0" * 64
        for index, (sequence, stage, evidence_json, stored_previous, digest) in enumerate(rows):
            if sequence != index or stored_previous != previous:
                return False
            entry = {"run_id": run_id, "sequence": sequence, "stage": stage,
                     "evidence": json.loads(evidence_json), "previous_hash": previous}
            if _hash(entry) != digest:
                return False
            previous = digest
        return bool(rows)


def run_swarm(stages: list[Stage], input_value: object, handlers: dict[str, Callable],
              ledger: MemPalace, *, max_stages: int = 8) -> dict:
    """Execute a bounded sequence; external handlers must be injected explicitly.

    Only input and output hashes enter the ledger. A failed stage stops the chain.
    Consequential actions always return pending approval without calling a handler.
    """
    if not stages or len(stages) > max_stages or len({s.id for s in stages}) != len(stages):
        raise ValueError("Invalid stage count or duplicate stage ID")
    if any(s.station not in STATIONS or not s.id or s.action not in {"draft", "read", *WRITE_ACTIONS} for s in stages):
        raise ValueError("Unregistered station or action")
    run_id = str(uuid4())
    value = input_value
    receipts = []
    for stage in stages:
        if stage.action in WRITE_ACTIONS:
            evidence = {"station": stage.station, "action": stage.action, "status": "pending_owner_approval", "input_sha256": _hash(value)}
            receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
            break
        handler = handlers.get(stage.station)
        if handler is None:
            raise ValueError(f"No verified handler for {stage.station}")
        input_hash = _hash(value)
        try:
            output = handler(value)
            output_hash = _hash(output)
        except Exception as exc:
            evidence = {"station": stage.station, "action": stage.action, "status": "failed", "input_sha256": input_hash, "error_type": type(exc).__name__}
            receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
            break
        evidence = {"station": stage.station, "action": stage.action, "status": "completed", "input_sha256": input_hash, "output_sha256": output_hash}
        receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
        value = output
    return {"run_id": run_id, "receipts": receipts, "chain_valid": ledger.verify(run_id),
            "output_sha256": _hash(value), "output": value}
