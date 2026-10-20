import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.doctor import Doctor


class DoctorTests(unittest.TestCase):
    def test_local_readiness_without_provider_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "workflows").mkdir()
            (root / "config").mkdir()
            shutil.copyfile(Path(__file__).resolve().parents[1] / "config/prompt-11-profile.json",
                            root / "config/prompt-11-profile.json")
            (root / "workflows" / "safe.json").write_text(
                json.dumps({"prompt_profile": {"id": "P-011-E6C-001", "revision": "repository-1"},
                            "steps": [{"id": "one", "type": "ai", "provider": "mock", "prompt": "test"}]}),
                encoding="utf-8")
            (root / ".gitignore").write_text(".env\ndata/\n*.sqlite3\n", encoding="utf-8")
            tower = ControlTower(Settings("mock", root / "data" / "test.sqlite3", 5))
            report = Doctor(tower, root).run()
            self.assertEqual(report["status"], "ready_local")
            self.assertEqual(report["readiness_score"], 100)
            self.assertIn("mock", report["providers"])


if __name__ == "__main__":
    unittest.main()
