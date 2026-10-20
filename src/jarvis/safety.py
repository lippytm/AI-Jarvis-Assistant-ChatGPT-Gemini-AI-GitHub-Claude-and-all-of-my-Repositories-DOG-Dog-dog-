from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SensitiveFinding:
    kind: str
    start: int


PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "google_api_key": re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}\b", re.IGNORECASE),
}


def find_sensitive(text: str) -> list[SensitiveFinding]:
    return [SensitiveFinding(kind, match.start())
            for kind, pattern in PATTERNS.items() for match in pattern.finditer(text)]


def redact(text: str) -> str:
    result = text
    for kind, pattern in PATTERNS.items():
        result = pattern.sub(f"[REDACTED:{kind}]", result)
    return result
