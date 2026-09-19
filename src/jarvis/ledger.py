from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import ProviderResponse, Task, utc_now


class Ledger:
    """Append-oriented local provenance store. Prompts may contain sensitive data."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, provider TEXT NOT NULL,
                    system TEXT NOT NULL, prompt TEXT NOT NULL, metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS responses (
                    task_id TEXT PRIMARY KEY REFERENCES tasks(id), created_at TEXT NOT NULL,
                    provider TEXT NOT NULL, model TEXT NOT NULL, content TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, usage_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL REFERENCES tasks(id),
                    created_at TEXT NOT NULL, event_type TEXT NOT NULL, detail_json TEXT NOT NULL);
            """)

    def create_task(self, task: Task) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (task.id, task.created_at, task.provider, task.system, task.prompt,
                        json.dumps(task.metadata, sort_keys=True), "created"))
            self._event(db, task.id, "task.created", {"provider": task.provider})

    def complete_task(self, response: ProviderResponse) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO responses VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (response.task_id, response.created_at, response.provider, response.model,
                        response.content, response.content_sha256,
                        json.dumps(response.usage, sort_keys=True)))
            db.execute("UPDATE tasks SET status='completed' WHERE id=?", (response.task_id,))
            self._event(db, response.task_id, "task.completed",
                        {"content_sha256": response.content_sha256})

    def fail_task(self, task_id: str, error: Exception) -> None:
        with self._connect() as db:
            db.execute("UPDATE tasks SET status='failed' WHERE id=?", (task_id,))
            self._event(db, task_id, "task.failed", {"error_type": type(error).__name__})

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT id, created_at, provider, status, substr(prompt,1,120) prompt "
                              "FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task:
                return None
            response = db.execute("SELECT * FROM responses WHERE task_id=?", (task_id,)).fetchone()
            events = db.execute("SELECT * FROM events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
        return {"task": dict(task), "response": dict(response) if response else None,
                "events": [dict(row) for row in events]}

    @staticmethod
    def _event(db: sqlite3.Connection, task_id: str, event_type: str,
               detail: dict[str, Any]) -> None:
        db.execute("INSERT INTO events(task_id,created_at,event_type,detail_json) VALUES(?,?,?,?)",
                   (task_id, utc_now(), event_type, json.dumps(detail, sort_keys=True)))
