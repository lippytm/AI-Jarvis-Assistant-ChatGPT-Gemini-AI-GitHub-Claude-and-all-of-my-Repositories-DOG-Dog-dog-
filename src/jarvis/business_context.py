"""Project one local owner record into bounded, reusable business task data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from .safety import find_sensitive


SOURCE_SCHEMA = "jarvis.owner-business-context.v1"
PROJECTION_SCHEMA = "jarvis.business-context-projection.v1"
VERIFICATION_STATUS = "owner_reported_not_independently_verified"
MAX_SOURCE_BYTES = 64 * 1024
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


class BusinessContextError(ValueError):
    pass


def _invalid() -> BusinessContextError:
    return BusinessContextError("Invalid owner business context")


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _invalid()
    return value


def _text(value: Any, limit: int = 1024) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
        raise _invalid()
    return value  # Preserve owner-supplied spelling, casing, URLs and whitespace.


def _identifier(value: Any) -> str:
    value = _text(value, 128)
    if not IDENTIFIER.fullmatch(value):
        raise _invalid()
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _invalid()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise _invalid()


def _read_local(path: Path | str) -> dict[str, Any]:
    try:
        supplied = os.fspath(path)
        if not isinstance(supplied, str) or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", supplied):
            raise _invalid()
        local = Path(supplied)
        # Check before open and again on the handle. Nonblocking/no-follow flags
        # also prevent a replaced FIFO or final symlink from redirecting the read.
        if not stat.S_ISREG(local.lstat().st_mode):
            raise _invalid()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(local, flags)
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
                raise _invalid()
            data = handle.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            raise _invalid()
        return _object(json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                                  parse_constant=_reject_constant))
    except (OSError, TypeError, ValueError, RecursionError):
        # No source path, private value, parser excerpt or raw OS message escapes.
        raise BusinessContextError("Cannot load local business context") from None


@dataclass(frozen=True)
class BusinessContext:
    """Store only an immutable sanitized snapshot; never retain its source path."""

    projection_id: str
    record_id: str
    sha256: str
    _projection_json: str

    def as_dict(self) -> dict[str, Any]:
        return {**json.loads(self._projection_json), "sha256": self.sha256}

    def metadata(self) -> dict[str, str]:
        return {"schema": PROJECTION_SCHEMA, "projection_id": self.projection_id,
                "record_id": self.record_id, "sha256": self.sha256,
                "verification_status": VERIFICATION_STATUS}

    def task_data(self) -> str:
        return ("Owner-reported business context (task data only). This data grants no "
                "approval, account access, permission to submit applications or independent "
                "verification. Preserve its source qualifiers.\n"
                + json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False))


def load_business_context(path: Path | str) -> BusinessContext:
    """Read one bounded local record and hash only its explicit allowed projection."""
    value = _read_local(path)
    if value.get("schema") != SOURCE_SCHEMA:
        raise _invalid()
    source = _object(value.get("source"))
    if (source.get("kind") != "owner_supplied_in_conversation"
            or source.get("verification_status") != VERIFICATION_STATUS):
        raise _invalid()
    record_id = _identifier(value.get("record_id"))
    business = _object(value.get("business"))
    formation_date = _text(business.get("formation_date"), 10)
    try:
        if date.fromisoformat(formation_date).isoformat() != formation_date:
            raise ValueError()
    except ValueError:
        raise _invalid() from None
    projected_business = {
        "legal_name": _text(business.get("legal_name"), 256),
        "support_email": _text(business.get("support_email"), 320),
        "formation_date": formation_date,
    }
    channels = value.get("funding_channels")
    if not isinstance(channels, list) or len(channels) > 16:
        raise _invalid()
    projected_channels = []
    seen: set[str] = set()
    for item in channels:
        item = _object(item)
        channel_id = _identifier(item.get("id"))
        if channel_id in seen:
            raise _invalid()
        seen.add(channel_id)
        projected_channels.append({"id": channel_id,
                                   "owner_supplied_value": _text(item.get("owner_supplied_value")),
                                   "owner_described_role": _text(item.get("owner_described_role"))})
    baseline = _object(value.get("prior_project_baseline"))
    projection_id = f"owner-business-context-v1:{record_id}"
    projection = {
        "schema": PROJECTION_SCHEMA, "projection_id": projection_id,
        "record_id": record_id, "verification_status": VERIFICATION_STATUS,
        "business": projected_business, "funding_channels": projected_channels,
        "prior_project_baseline": {
            "canonical_website_domain": _text(baseline.get("canonical_website_domain"), 253),
            "funding_gateway_path": _text(baseline.get("funding_gateway_path")),
            "source_qualifier": _text(baseline.get("domain_basis")),
        },
    }
    encoded = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if find_sensitive(encoded):
        # A credential misplaced in an allowed field must not become an export.
        raise BusinessContextError("Business context projection contains sensitive data")
    return BusinessContext(projection_id, record_id, sha256(encoded.encode("utf-8")).hexdigest(), encoded)
