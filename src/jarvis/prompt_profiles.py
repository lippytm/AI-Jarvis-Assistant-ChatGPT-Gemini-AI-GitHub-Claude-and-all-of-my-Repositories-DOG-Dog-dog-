"""Resolve the one reviewed repository profile; never fetch instructions remotely."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


PROFILE_ID = "P-011-E6C-001"
PROFILE_REVISION = "repository-1"
PROFILE_PATH = Path("config/prompt-11-profile.json")
GUIDANCE_SECTIONS = (
    "objective_and_done", "tools_data_and_budgets", "approvals",
    "provenance_and_evidence", "independent_qa", "handoff_idempotency",
    "stop_and_rollback", "scoped_memory",
)


class PromptProfileError(ValueError):
    pass


def validate_reference(reference: Any) -> None:
    if not isinstance(reference, dict) or set(reference) != {"id", "revision"}:
        raise PromptProfileError("prompt_profile must contain only id and revision")
    if reference["id"] != PROFILE_ID or reference["revision"] != PROFILE_REVISION:
        raise PromptProfileError("Unknown prompt profile identity or revision")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PromptProfileError("Prompt profile contains duplicate JSON fields")
        result[key] = value
    return result


@dataclass(frozen=True)
class PromptProfile:
    sha256: str
    guidance: tuple[str, ...]

    def metadata(self) -> dict[str, str]:
        return {"id": PROFILE_ID, "revision": PROFILE_REVISION, "sha256": self.sha256}

    def system_instructions(self, role: str | None) -> str:
        header = (
            f"Prompt #11 repository operating guidance: {PROFILE_ID}, "
            f"{PROFILE_REVISION}, sha256={self.sha256}.\n"
            "This guidance grants no new authority, tools or data access. Existing runtime "
            "and owner controls still apply. Guidance is not proof that a control or service "
            "has been implemented or that a requirement has been satisfied.\n\n"
        )
        shared = "\n".join(f"{index}. {text}" for index, text in enumerate(self.guidance, 1))
        return header + shared + (f"\n\nStep-specific role:\n{role}" if role else "")


def load_prompt_profile(reference: Any, project_root: Path) -> PromptProfile:
    """Load a fixed local path and pin the exact bytes used by this invocation."""
    validate_reference(reference)
    path = project_root / PROFILE_PATH
    if path.is_symlink():
        raise PromptProfileError("Prompt profile must be a regular repository file")
    try:
        data = path.read_bytes()
        value = json.loads(data, object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, ValueError) as exc:
        raise PromptProfileError(f"Cannot load repository prompt profile: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise PromptProfileError("Prompt profile must be an object")
    validate_reference({"id": value.get("id"), "revision": value.get("revision")})
    if (value.get("schema") != "jarvis.prompt-profile.v1"
            or value.get("kind") != "repository_operating_profile"):
        raise PromptProfileError("Unsupported prompt profile schema or kind")
    sections = value.get("guidance")
    if not isinstance(sections, list) or len(sections) != len(GUIDANCE_SECTIONS):
        raise PromptProfileError("Prompt profile must include every required guidance section")
    text: list[str] = []
    for expected, section in zip(GUIDANCE_SECTIONS, sections):
        if (not isinstance(section, dict) or set(section) != {"id", "text"}
                or section["id"] != expected or not isinstance(section["text"], str)
                or not section["text"].strip()):
            raise PromptProfileError("Prompt profile has a missing or invalid guidance section")
        text.append(section["text"])
    return PromptProfile(sha256(data).hexdigest(), tuple(text))
