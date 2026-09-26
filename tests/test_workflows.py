import re
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_scan_ignores_its_own_workflow_file(self):
        repository = Path(__file__).resolve().parents[1]
        workflow = repository / ".github/workflows/jarvis-sync.yml"
        self.assertIn("--exclude='jarvis-sync.yml'", workflow.read_text(encoding="utf-8"))
        allowed_suffixes = {".json", ".md", ".yaml", ".yml"}

        pattern = re.compile(
            r"(sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
        )
        matches = []
        for root in (repository / ".jarvis", repository / ".github"):
            for path in root.rglob("*"):
                if path.is_dir() or path.name == workflow.name or path.suffix not in allowed_suffixes:
                    continue
                content = path.read_text(encoding="utf-8")
                if pattern.search(content):
                    matches.append(path.relative_to(repository).as_posix())
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
