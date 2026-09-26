import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_scan_excludes_self(self):
        workflow = Path(".github/workflows/jarvis-sync.yml").read_text(encoding="utf-8").splitlines()
        scan_lines = [line for line in workflow if "if grep -RInE" in line]
        self.assertEqual(len(scan_lines), 1)
        self.assertIn("--exclude='jarvis-sync.yml'", scan_lines[0])


if __name__ == "__main__":
    unittest.main()
