from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PreventionLibrary:
    def __init__(self, path: Path = Path("config/prevention-patterns.json")):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self._validate()

    def _validate(self) -> None:
        controls = self.data.get("controls")
        if not isinstance(controls, list) or not controls:
            raise ValueError("Prevention library requires controls")
        ids = [item.get("id") for item in controls]
        if len(ids) != len(set(ids)):
            raise ValueError("Prevention control IDs must be unique")
        if any(not item.get("title") or not item.get("viability_dimension") for item in controls):
            raise ValueError("Every prevention control requires title and viability_dimension")

    def recommend(self, domains: list[str] | None = None) -> dict[str, Any]:
        requested = {item.strip().lower() for item in (domains or []) if item.strip()}
        selected = []
        for control in self.data["controls"]:
            tags = set(control.get("tags", []))
            if "core" in tags or requested & tags:
                selected.append(control)
        return {
            "schema_version": self.data.get("schema_version"),
            "domains": sorted(requested),
            "controls": selected,
            "control_count": len(selected),
            "sources": self.data.get("sources", []),
            "claim": "Control recommendations require tailoring and do not guarantee prevention.",
        }
