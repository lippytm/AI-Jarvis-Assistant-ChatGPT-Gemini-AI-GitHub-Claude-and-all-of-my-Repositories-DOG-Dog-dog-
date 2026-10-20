from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Risk(str, Enum):
    READ = "read"
    DRAFT = "draft"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ConnectorAction:
    name: str
    risk: Risk
    payload: dict[str, Any]


class Connector(ABC):
    name: str

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def execute(self, action: ConnectorAction,
                approval_token: str | None = None) -> dict[str, Any]: ...

    @staticmethod
    def require_approval(action: ConnectorAction, approval_token: str | None) -> None:
        if action.risk in {Risk.WRITE, Risk.DESTRUCTIVE} and not approval_token:
            raise PermissionError(f"Action '{action.name}' requires explicit approval")
        if action.risk is Risk.DESTRUCTIVE:
            raise PermissionError("Destructive connector actions are disabled in v0.1")
