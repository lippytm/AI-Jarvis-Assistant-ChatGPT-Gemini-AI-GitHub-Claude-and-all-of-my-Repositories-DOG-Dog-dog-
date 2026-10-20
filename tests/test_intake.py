import tempfile
import unittest
from pathlib import Path

from jarvis.intake import IntakeBridge, IntakeError


class IntakeTests(unittest.TestCase):
    def test_gemini_intake_creates_provenance_and_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "gemini-export.md"
            source.write_text("# Gemini Jarvis\nA product-building idea.", encoding="utf-8")
            bridge = IntakeBridge(root / "inbox", root / "outbox")
            result = bridge.capture("Gemini AI Jarvis", source, "Product Idea")
            self.assertEqual(result["source"], "gemini-ai-jarvis")
            self.assertTrue(Path(result["record_path"]).is_file())
            handoff = Path(result["handoff_path"]).read_text(encoding="utf-8")
            self.assertIn(result["intake_id"], handoff)
            self.assertIn(result["original_sha256"], handoff)
            self.assertEqual(len(bridge.list()), 1)

    def test_sensitive_export_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "unsafe.md"
            source.write_text("key sk-abcdefghijklmnopqrstuvwxyz123456", encoding="utf-8")
            with self.assertRaisesRegex(IntakeError, "Sensitive content"):
                IntakeBridge(root / "inbox", root / "outbox").capture("gemini", source)


if __name__ == "__main__":
    unittest.main()
