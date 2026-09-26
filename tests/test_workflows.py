import re
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_pattern_avoids_docs_false_positive(self):
        workflow = Path('.github/workflows/jarvis-sync.yml').read_text(encoding='utf-8')

        match = re.search(
            r"grep\s+-RInE\s+(['\"])(?P<pattern>.+?)\1\s+\.jarvis\s+\.github",
            workflow,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)

        pattern = match.group('pattern')
        self.assertIn('sk-[A-Za-z0-9_-]{20,}', pattern)
        self.assertIn('AIza[A-Za-z0-9_-]{30,}', pattern)
        self.assertIn('AKIA[A-Z0-9]{16}', pattern)
        self.assertIn('-----BEGIN [A-Z ]*PRIVATE KEY-----', pattern)
        self.assertNotIn('sk-[A-Za-z0-9]|', pattern)

        benign_paths = [
            'docs/jarvis-task-templates.md',
            '.github/workflows/jarvis-repository-scope.yml',
        ]
        benign_contents = [Path(path).read_text(encoding='utf-8') for path in benign_paths]

        for path in benign_paths:
            self.assertIsNone(re.search(pattern, path))
        for content in benign_contents:
            self.assertIsNone(re.search(pattern, content))

        self.assertIsNotNone(re.search(pattern, 'sk-' + 'A' * 20))
        self.assertIsNotNone(re.search(pattern, 'AIza' + 'A' * 30))
        self.assertIsNotNone(re.search(pattern, 'AKIA' + 'A' * 16))

        self.assertIsNone(re.search(pattern, 'sk-' + 'A' * 19))
        self.assertIsNone(re.search(pattern, 'AIza' + 'A' * 29))
        self.assertIsNone(re.search(pattern, 'AKIA' + 'A' * 15))


if __name__ == '__main__':
    unittest.main()
