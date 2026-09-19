from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    default_provider: str
    db_path: Path
    timeout_seconds: int
    max_external_calls: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        timeout = int(os.getenv("JARVIS_TIMEOUT_SECONDS", "60"))
        if not 1 <= timeout <= 300:
            raise ValueError("JARVIS_TIMEOUT_SECONDS must be between 1 and 300")
        max_calls = int(os.getenv("JARVIS_MAX_EXTERNAL_CALLS", "6"))
        if not 0 <= max_calls <= 50:
            raise ValueError("JARVIS_MAX_EXTERNAL_CALLS must be between 0 and 50")
        return cls(os.getenv("JARVIS_DEFAULT_PROVIDER", "mock").lower(),
                   Path(os.getenv("JARVIS_DB_PATH", "data/jarvis.sqlite3")), timeout, max_calls)
