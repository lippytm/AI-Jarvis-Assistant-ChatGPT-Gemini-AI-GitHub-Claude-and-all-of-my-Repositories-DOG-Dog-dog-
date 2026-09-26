import re
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_pattern_avoids_docs_false_positive(self):
        workflow = Path('.github/workflows/jarvis-sync.yml').read_text(encoding='utf-8')
        docs_template = Path('docs/jarvis-task-templates.md').read_text(encoding='utf-8')

        match = re.search(r"grep\s+-RInE\s+(['\"])(.+?)\1", workflow, flags=re.DOTALL)
        self.assertIsNotNone(match)

        pattern = match.group(2)
        self.assertIn('sk-[A-Za-z0-9_-]{20,}', pattern)
        self.assertIn('AIza[A-Za-z0-9_-]{30,}', pattern)
        self.assertIn('AKIA[A-Z0-9]{16}', pattern)
        self.assertIn('-----BEGIN [A-Z ]*PRIVATE KEY-----', pattern)
        self.assertNotIn('sk-[A-Za-z0-9]|', pattern)

        self.assertIsNone(re.search(pattern, 'docs/jarvis-task-templates.md'))
        self.assertIsNone(re.search(pattern, docs_template))
        self.assertIsNotNone(re.search(pattern, 'sk-' + 'A' * 20))
        self.assertIsNotNone(re.search(pattern, 'AIza' + 'A' * 30))
        self.assertIsNotNone(re.search(pattern, 'AKIA' + 'A' * 16))


if __name__ == '__main__':
    unittest.main()
