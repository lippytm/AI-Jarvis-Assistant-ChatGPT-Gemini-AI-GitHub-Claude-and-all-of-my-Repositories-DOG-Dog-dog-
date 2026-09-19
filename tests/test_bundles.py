import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from jarvis.bundles import BundleError, RunBundler


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.outbox = root / "outbox"
        self.outbox.mkdir()
        self.bundles = root / "bundles"
        self.run_id = "run-123"
        (self.outbox / f"{self.run_id}-report.json").write_text(
            json.dumps({"run_id": self.run_id, "workflow": "test"}), encoding="utf-8")
        (self.outbox / f"{self.run_id}-handoff-chatgpt.md").write_text(
            "verified handoff", encoding="utf-8")
        self.bundler = RunBundler(self.outbox, self.bundles)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_and_verify_round_trip(self):
        created = self.bundler.create(self.run_id)
        verified = self.bundler.verify(Path(created["path"]))
        self.assertEqual(verified["run_id"], self.run_id)
        self.assertEqual(len(verified["verified_files"]), 2)
        self.assertEqual(verified["bundle_sha256"], created["bundle_sha256"])

    def test_tampered_artifact_is_rejected(self):
        created = self.bundler.create(self.run_id)
        original = Path(created["path"])
        tampered = self.bundles / "tampered.jarvis.zip"
        with ZipFile(original) as source, ZipFile(tampered, "w", ZIP_DEFLATED) as target:
            for name in source.namelist():
                data = b"changed" if name.endswith(".md") else source.read(name)
                target.writestr(name, data)
        with self.assertRaisesRegex(BundleError, "Integrity check failed"):
            self.bundler.verify(tampered)


if __name__ == "__main__":
    unittest.main()
