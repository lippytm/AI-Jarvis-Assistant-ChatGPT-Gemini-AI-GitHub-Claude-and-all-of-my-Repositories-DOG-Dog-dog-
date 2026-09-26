import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_scan_excludes_self(self):
        workflow = Path(".github/workflows/jarvis-sync.yml").read_text(encoding="utf-8")
        self.assertIn("--exclude='jarvis-sync.yml'", workflow)


if __name__ == "__main__":
    unittest.main()
