import re
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def test_jarvis_sync_credential_pattern_avoids_docs_false_positive(self):
        workflow = Path('.github/workflows/jarvis-sync.yml').read_text(encoding='utf-8')
        docs_template = Path('docs/jarvis-task-templates.md').read_text(encoding='utf-8')

        pattern = r'(sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'

        self.assertIn(pattern, workflow)
        self.assertNotIn('sk-[A-Za-z0-9]|', workflow)
        self.assertIsNone(re.search(pattern, 'docs/jarvis-task-templates.md'))
        self.assertIsNone(re.search(pattern, docs_template))
        self.assertIsNotNone(re.search(pattern, 'sk-' + 'A' * 20))


if __name__ == '__main__':
    unittest.main()
