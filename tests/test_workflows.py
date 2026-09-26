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

        false_positive_examples = [
            'docs/jarvis-task-templates.md',
            'docs/jarvis-task-templates.md; do',
            '.github/workflows/jarvis-repository-scope.yml:28:            docs/jarvis-task-templates.md; do',
        ]
        for sample in false_positive_examples:
            self.assertIsNone(re.search(pattern, sample))

        self.assertIsNotNone(re.search(pattern, 'sk-' + 'A' * 20))
        self.assertIsNotNone(re.search(pattern, 'AIza' + 'A' * 30))
        self.assertIsNotNone(re.search(pattern, 'AKIA' + 'A' * 16))

        self.assertIsNone(re.search(pattern, 'sk-' + 'A' * 19))
        self.assertIsNone(re.search(pattern, 'AIza' + 'A' * 29))
        self.assertIsNone(re.search(pattern, 'AKIA' + 'A' * 15))


if __name__ == '__main__':
    unittest.main()
