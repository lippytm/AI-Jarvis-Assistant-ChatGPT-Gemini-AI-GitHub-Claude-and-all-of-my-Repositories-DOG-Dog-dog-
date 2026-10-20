"""Bounded Hermes handoffs with a local MemPalace evidence ledger.

Providers are explicit callables; this module has no autonomous network or publish path.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
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


class AccessBlocked(PermissionError):
    """An authorized adapter reports that this access route is unavailable.

    Raising this does not grant access. Its message is excluded from receipts.
    """


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
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS events (run_id TEXT NOT NULL, sequence INTEGER NOT NULL, stage TEXT NOT NULL, evidence_json TEXT NOT NULL, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL, PRIMARY KEY (run_id, sequence))")

    def append(self, run_id: str, stage: str, evidence: dict) -> str:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute("SELECT sequence, entry_hash FROM events WHERE run_id=? ORDER BY sequence DESC LIMIT 1", (run_id,)).fetchone()
            sequence, previous = (last[0] + 1, last[1]) if last else (0, "0" * 64)
            entry = {"run_id": run_id, "sequence": sequence, "stage": stage,
                     "evidence": evidence, "previous_hash": previous}
            digest = _hash(entry)
            db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                       (run_id, sequence, stage, _canonical(evidence).decode(), previous, digest))
        return digest

    def _verified_history(self, run_id: str) -> list[dict]:
        # Validate and return the same snapshot, not a second unverified read.
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute("SELECT sequence, stage, evidence_json, previous_hash, entry_hash FROM events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
        previous = "0" * 64
        events = []
        for index, (sequence, stage, evidence_json, stored_previous, digest) in enumerate(rows):
            if sequence != index or stored_previous != previous:
                raise ValueError("Invalid MemPalace evidence chain")
            try:
                evidence = json.loads(evidence_json)
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid MemPalace evidence JSON") from exc
            entry = {"run_id": run_id, "sequence": sequence, "stage": stage,
                     "evidence": evidence, "previous_hash": previous}
            if _hash(entry) != digest:
                raise ValueError("Invalid MemPalace evidence hash")
            events.append({**entry, "entry_hash": digest})
            previous = digest
        return events

    def verify(self, run_id: str) -> bool:
        try:
            return bool(self._verified_history(run_id))
        except ValueError:
            return False

    def history(self, run_id: str, *, expected_head: str | None = None) -> list[dict]:
        """Retrieve verified local evidence, not prompts or provider truth.

        Keep an expected head hash separately to detect removal of tail events.
        Without that anchor, a valid prefix remains indistinguishable from a run.
        """
        events = self._verified_history(run_id)
        if not events:
            raise ValueError("No MemPalace evidence for this run")
        if expected_head is not None and events[-1]["entry_hash"] != expected_head:
            raise ValueError("MemPalace head does not match expected anchor")
        return events


def run_swarm(stages: list[Stage], input_value: object, handlers: dict[str, Callable],
              ledger: MemPalace, *, max_stages: int = 8,
              blocked_stations: frozenset[str] = frozenset()) -> dict:
    """Execute a bounded sequence; external handlers must be injected explicitly.

    Only input and output hashes enter the ledger. Failed or blocked stages stop.
    Caller-supplied blocks are restrictions, never authentication or permission.
    Consequential actions always return pending approval without calling a handler.
    """
    if not stages or len(stages) > max_stages or len({s.id for s in stages}) != len(stages):
        raise ValueError("Invalid stage count or duplicate stage ID")
    if any(s.station not in STATIONS or not s.id or s.action not in {"draft", "read", *WRITE_ACTIONS} for s in stages):
        raise ValueError("Unregistered station or action")
    if not isinstance(blocked_stations, (set, frozenset)) or not blocked_stations.issubset(STATIONS):
        raise ValueError("Invalid blocked-station policy")
    run_id = str(uuid4())
    value = input_value
    receipts = []
    for stage in stages:
        if stage.action in WRITE_ACTIONS:
            evidence = {"station": stage.station, "action": stage.action, "status": "pending_owner_approval", "input_sha256": _hash(value)}
            receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
            break
        if stage.station in blocked_stations:
            evidence = {"station": stage.station, "action": stage.action, "status": "blocked_access", "input_sha256": _hash(value)}
            receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
            break
        handler = handlers.get(stage.station)
        if handler is None:
            raise ValueError(f"No verified handler for {stage.station}")
        input_hash = _hash(value)
        try:
            output = handler(value)
            output_hash = _hash(output)
        except AccessBlocked:
            evidence = {"station": stage.station, "action": stage.action, "status": "blocked_access", "input_sha256": input_hash, "error_type": "AccessBlocked"}
            receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
            break
        except Exception as exc:
            evidence = {"station": stage.station, "action": stage.action, "status": "failed", "input_sha256": input_hash, "error_type": type(exc).__name__}
            receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
            break
        evidence = {"station": stage.station, "action": stage.action, "status": "completed", "input_sha256": input_hash, "output_sha256": output_hash}
        receipts.append({"stage": stage.id, **evidence, "entry_hash": ledger.append(run_id, stage.id, evidence)})
        value = output
    return {"run_id": run_id, "receipts": receipts, "chain_valid": ledger.verify(run_id),
            "output_sha256": _hash(value), "output": value}
