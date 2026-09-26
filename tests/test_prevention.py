from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.prevention import PreventionLibrary


class PreventionLibraryTests(unittest.TestCase):
    def test_core_controls_are_always_selected(self) -> None:
        library = PreventionLibrary()
        result = library.recommend([])
        ids = {item["id"] for item in result["controls"]}
        self.assertIn("PRE-001", ids)
        self.assertIn("PRE-010", ids)

    def test_domain_adds_specialized_controls(self) -> None:
        library = PreventionLibrary()
        core = library.recommend([])
        ai = library.recommend(["ai"])
        self.assertGreater(ai["control_count"], core["control_count"])
        self.assertIn("PRE-011", {item["id"] for item in ai["controls"]})

    def test_duplicate_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"controls": [
                {"id": "X", "title": "one", "viability_dimension": "evidence"},
                {"id": "X", "title": "two", "viability_dimension": "evidence"},
            ]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unique"):
                PreventionLibrary(path)


if __name__ == "__main__":
    unittest.main()
