import subprocess
import tempfile
import unittest
from pathlib import Path

from engine.jarvis_engine import inspect_repository, route


class EngineTests(unittest.TestCase):
    def git(self, repository: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True)

    def test_routes_implementation_to_pilot_coding_providers(self):
        self.assertEqual(route("implement"), ["github-copilot", "openai-codex"])

    def test_unverified_forge_is_not_selected_for_execution(self):
        self.assertEqual(route("merge_request"), [])

    def test_read_only_repository_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            self.git(repository, "init", "-b", "main")
            self.git(repository, "config", "user.email", "test@example.invalid")
            self.git(repository, "config", "user.name", "Jarvis Test")
            (repository / "README.md").write_text("# Test\n", encoding="utf-8")
            self.git(repository, "add", "README.md")
            self.git(repository, "commit", "-m", "Initial test commit")
            report = inspect_repository(repository)
            self.assertEqual(report["mode"], "read-only")
            self.assertEqual(report["branch"], "main")
            self.assertFalse(report["dirty"])
            self.assertEqual(len(report["commits"]), 1)
            self.assertEqual(report["commits"][0]["subject"], "Initial test commit")


if __name__ == "__main__":
    unittest.main()
