from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Task:
    prompt: str
    provider: str
    system: str = "You are Jarvis, a careful and practical business-building assistant."
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderResponse:
    task_id: str
    provider: str
    model: str
    content: str
    created_at: str = field(default_factory=utc_now)
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def content_sha256(self) -> str:
        return sha256(self.content.encode()).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["content_sha256"] = self.content_sha256
        return value
