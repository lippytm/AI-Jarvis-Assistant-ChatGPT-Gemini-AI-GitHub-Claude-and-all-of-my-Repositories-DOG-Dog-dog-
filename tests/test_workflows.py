import subprocess
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_scan_ignores_its_own_workflow_file(self):
        repository = Path(__file__).resolve().parents[1]
        pattern = r"(sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
        result = subprocess.run(
            [
                "grep",
                "-RInE",
                "--exclude=jarvis-sync.yml",
                pattern,
                ".jarvis",
                ".github",
            ],
            cwd=repository,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stdout)


if __name__ == "__main__":
    unittest.main()
