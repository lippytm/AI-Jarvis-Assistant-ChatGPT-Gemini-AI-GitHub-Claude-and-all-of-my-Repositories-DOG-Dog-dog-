"""Regression checks for redaction, real-pattern detection, and scan coverage."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_control_secrets as scanner


class ControlSecretScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in scanner.CONTROL_DIRECTORIES:
            (self.root / name).mkdir()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return path

    def invoke(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = scanner.main(["--repository", str(self.root)])
        return status, out.getvalue(), err.getvalue()

    def test_original_workflow_regex_and_task_filename_are_harmless(self):
        self.write(".github/workflows/old-scanner.yml", """
if grep -RInE '(sk-[A-Za-z0-9]|AIza[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN .*PRIVATE KEY-----)' .jarvis .github; then
  echo 'Potential credential detected in control-plane files.'
fi
docs/jarvis-task-templates.md
""")
        self.assertEqual([], scanner.scan(self.root))
        self.assertEqual(0, self.invoke()[0])

    def test_scanner_definitions_do_not_match_themselves(self):
        self.write(".github/scripts/check.py", Path(scanner.__file__).read_bytes())
        self.assertEqual([], scanner.scan(self.root))

    def test_model_api_key_in_control_file_is_detected(self):
        self.write(".jarvis/config.yaml", "token: " + "sk-" + "A" * 48)
        self.assertEqual("model_api_key", scanner.scan(self.root)[0]["rule"])

    def test_project_and_anthropic_keys_in_workflow_are_detected(self):
        for prefix in ("sk-proj-", "sk-svcacct-", "sk-ant-api03-"):
            with self.subTest(prefix=prefix):
                self.write(".github/workflows/build.yml", prefix + "A" * 60)
                self.assertEqual("model_api_key", scanner.scan(self.root)[0]["rule"])

    def test_google_and_aws_patterns_are_detected(self):
        self.write(".jarvis/config.yaml", "\n".join((
            "AIza" + "B" * 35,
            "AKIA" + "C" * 16,
            "ASIA" + "D" * 16,
        )))
        self.assertEqual(
            ["google_api_key", "aws_access_key_id", "aws_access_key_id"],
            [finding["rule"] for finding in scanner.scan(self.root)],
        )

    def test_github_token_families_are_detected(self):
        tokens = [prefix + "E" * 36 for prefix in ("ghp_", "gho_", "ghu_", "ghs_", "ghr_")]
        tokens.append("github_pat_" + "F" * 80)
        self.write(".github/workflows/build.yml", "\n".join(tokens))
        self.assertEqual(6, len(scanner.scan(self.root)))

    def test_private_key_headers_are_detected(self):
        for kind in ("", "RSA ", "EC ", "DSA ", "OPENSSH ", "ENCRYPTED "):
            with self.subTest(kind=kind):
                self.write(".github/private.pem", "-----BEGIN " + kind + "PRIVATE KEY-----\nsynthetic")
                self.assertEqual("private_key_header", scanner.scan(self.root)[0]["rule"])

    def test_report_has_line_and_rule_but_never_value_or_source_line(self):
        token = "sk-" + "G" * 48
        self.write(".github/workflows/build.yml", "name: example\nprivate_label: " + token + "\n")
        status, out, err = self.invoke()
        self.assertEqual(1, status)
        self.assertIn('"line": 2', out)
        self.assertIn('"rule": "model_api_key"', out)
        self.assertNotIn(token, out + err)
        self.assertNotIn("private_label", out + err)

    def test_binary_file_is_scanned_without_utf8_skips(self):
        self.write(".github/asset.bin", b"\xff\x00" + b"sk-" + b"H" * 48)
        self.assertEqual("model_api_key", scanner.scan(self.root)[0]["rule"])

    def test_missing_required_directory_fails_closed(self):
        (self.root / ".github").rmdir()
        status, out, err = self.invoke()
        self.assertEqual(2, status)
        self.assertNotIn("passed", out)
        self.assertIn("missing_or_unreadable_path", err)

    def test_regular_file_cannot_replace_required_directory(self):
        (self.root / ".github").rmdir()
        self.write(".github", "empty")
        self.assertEqual(2, self.invoke()[0])

    def test_unreadable_file_fails_closed_without_exception_details(self):
        path = self.write(".jarvis/config.yaml", "safe")
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("sensitive error detail")):
            status, out, err = self.invoke()
        self.assertEqual(2, status)
        self.assertIn("unreadable_file", err)
        self.assertNotIn("sensitive error detail", out + err)

    def test_symlinked_file_and_directory_fail_closed(self):
        for directory in (False, True):
            with self.subTest(directory=directory):
                link = self.root / ".github" / "link"
                target = self.root / ("target-dir" if directory else "target-file")
                if directory:
                    target.mkdir()
                else:
                    target.write_text("safe")
                link.symlink_to(target, target_is_directory=directory)
                self.assertEqual(2, self.invoke()[0])
                link.unlink()

    def test_symlinked_required_directory_fails_closed(self):
        (self.root / ".github").rmdir()
        (self.root / ".github").symlink_to(self.root / ".jarvis", target_is_directory=True)
        self.assertEqual(2, self.invoke()[0])

    def test_metadata_escapes_filename_newlines(self):
        self.write(".github/workflows/odd\nname.yml", "sk-" + "J" * 48)
        status, out, err = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual(1, len(out.splitlines()))
        self.assertIn("odd\\nname.yml", out)


if __name__ == "__main__":
    unittest.main()
