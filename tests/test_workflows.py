import re
import subprocess
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def grep_matches(self, pattern: str, sample: str) -> bool:
        result = subprocess.run(
            ['grep', '-E', '-q', pattern],
            input=sample,
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    def test_jarvis_sync_credential_pattern_avoids_docs_false_positive(self):
        workflow = Path('.github/workflows/jarvis-sync.yml').read_text(encoding='utf-8')

        match = re.search(
            r"grep\s+-RInE\s+(['\"])(?P<pattern>.+?)\1",
            workflow,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)

        pattern = match.group('pattern')

        false_positive_examples = [
            'docs/jarvis-task-templates.md',
            'docs/jarvis-task-templates.md; do',
            '.github/workflows/jarvis-repository-scope.yml:28:            docs/jarvis-task-templates.md; do',
        ]
        for sample in false_positive_examples:
            self.assertFalse(self.grep_matches(pattern, sample))

        self.assertTrue(self.grep_matches(pattern, 'sk-' + 'A' * 20))
        self.assertTrue(self.grep_matches(pattern, 'AIza' + 'A' * 30))
        self.assertTrue(self.grep_matches(pattern, 'AKIA' + 'A' * 16))

        self.assertFalse(self.grep_matches(pattern, 'sk-' + 'A' * 19))
        self.assertFalse(self.grep_matches(pattern, 'AIza' + 'A' * 29))
        self.assertFalse(self.grep_matches(pattern, 'AKIA' + 'A' * 15))


if __name__ == '__main__':
    unittest.main()
