import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_scan_targets_control_plane_files_only(self):
        workflow = Path(".github/workflows/jarvis-sync.yml").read_text(encoding="utf-8")
        self.assertIn("find .jarvis .github -type f", workflow)
        self.assertIn("! -name 'jarvis-sync.yml'", workflow)
        self.assertIn("-name '*.md' -o -name '*.yml' -o -name '*.yaml' -o -name '*.json'", workflow)
        self.assertIn("xargs -0 grep -InE", workflow)


if __name__ == "__main__":
    unittest.main()
