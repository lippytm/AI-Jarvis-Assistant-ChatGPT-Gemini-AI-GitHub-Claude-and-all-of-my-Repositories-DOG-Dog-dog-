"""Studio packet tests use synthetic local records and never contact accounts."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from jarvis.business_context import load_business_context
from jarvis.creative_studio import (
    BRAND, CONFIG_PATH, DECLARATION_KEYS, EXECUTION, MAX_CONFIG_BYTES,
    MAX_FILE_BYTES, MAX_INPUT_BYTES, PAYLOAD_PATHS, REQUIRED_PATHS,
    StudioError, build_packet, load_studio_config, main,
    validate_business_context, verify_packet,
)
from jarvis.prompt_profiles import PROFILE_ID, PROFILE_REVISION, load_prompt_profile


PROJECT = Path(__file__).resolve().parents[1]


class CreativeStudioTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        (self.project / "config").mkdir(parents=True)
        self.config_path = self.project / CONFIG_PATH
        shutil.copyfile(PROJECT / CONFIG_PATH, self.config_path)
        self.config = load_studio_config(self.project)
        self.profile = load_prompt_profile({"id": PROFILE_ID, "revision": PROFILE_REVISION}, PROJECT).metadata()
        self.workflow = {"name": "creative_studio_package", "sha256": "a" * 64}
        self.output = self.root / "packet"
        self.input = "Prepare studio structures. SYNTHETIC_RAW_REQUEST_NOT_FOR_EXPORT"

    def build(self, output=None, **overrides):
        arguments = {"run_id": "synthetic-run-1", "input_text": self.input,
                     "prompt_profile": self.profile, "workflow": self.workflow}
        arguments.update(overrides)
        return build_packet(self.config, output or self.output, **arguments)

    def context(self, *, studio=True, mutate=None):
        value = {
            "schema": "jarvis.owner-business-context.v1",
            "record_id": "synthetic-studio-owner",
            "source": {"kind": "owner_supplied_in_conversation",
                       "verification_status": "owner_reported_not_independently_verified"},
            "business": {"legal_name": "Example Business LLC", "support_email": "support@example.invalid",
                         "formation_date": "2020-01-02",
                         "private_admin": "SYNTHETIC_PRIVATE_ADMIN_NOT_FOR_EXPORT"},
            "funding_channels": [],
            "prior_project_baseline": {"canonical_website_domain": "example.invalid",
                                       "funding_gateway_path": "/funding",
                                       "domain_basis": "Synthetic prior owner record"},
            "private_account": {"secret": "SYNTHETIC_PRIVATE_ACCOUNT_NOT_FOR_EXPORT"},
        }
        if studio:
            value["creative_studio"] = {key: self.config.as_dict()[key] for key in DECLARATION_KEYS
                                       if key not in {"declaration_status", "connection_status"}}
        if mutate:
            mutate(value)
        path = self.root / "synthetic-private-owner.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return load_business_context(path)

    def manifest(self, output=None):
        return json.loads(((output or self.output) / "manifest.json").read_bytes())

    def write_manifest(self, value, output=None):
        ((output or self.output) / "manifest.json").write_text(json.dumps(value), encoding="utf-8")

    def rewrite_payload_and_hash(self, path, data, output=None):
        output = output or self.output
        (output / path).write_bytes(data)
        manifest = self.manifest(output)
        record = next(item for item in manifest["files"] if item["path"] == path)
        record.update({"bytes": len(data), "sha256": sha256(data).hexdigest()})
        self.write_manifest(manifest, output)

    def test_config_pins_exact_bytes_and_returns_immutable_copies(self):
        self.assertEqual(BRAND, self.config.as_dict()["brand_name"])
        self.assertEqual(["Videos", "eBooks", "Audiobooks", "Video Books"], self.config.as_dict()["formats"])
        self.assertEqual(sha256(self.config_path.read_bytes()).hexdigest(), self.config.metadata()["sha256"])
        copy = self.config.as_dict()
        copy["formats"].append("Unapproved format")
        self.assertEqual(4, len(self.config.as_dict()["formats"]))
        with self.assertRaises(FrozenInstanceError):
            self.config.sha256 = "b" * 64

    def test_config_rejects_unknown_identity_revision_and_declaration_changes(self):
        for field, value in (("schema", "unknown"), ("id", "other"), ("revision", "next"),
                             ("brand_name", BRAND + " altered"), ("formats", ["Videos"]),
                             ("connection_status", "connected"), ("extra", "not allowed")):
            data = self.config.as_dict()
            data[field] = value
            self.config_path.write_text(json.dumps(data), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(StudioError):
                load_studio_config(self.project)

    def test_config_rejects_missing_malformed_large_duplicate_and_symlinked_files(self):
        for data in (b"[]", b"\xff", b"{", b'{"id":"one","id":"two"}',
                     b'{"value":NaN}', b"x" * (MAX_CONFIG_BYTES + 1)):
            self.config_path.write_bytes(data)
            with self.subTest(data=data[:20]), self.assertRaises(StudioError):
                load_studio_config(self.project)
        self.config_path.unlink()
        with self.assertRaises(StudioError):
            load_studio_config(self.project)
        self.config_path.symlink_to(PROJECT / CONFIG_PATH)
        with self.assertRaises(StudioError):
            load_studio_config(self.project)

    def test_packet_is_complete_template_only_and_makes_no_network_calls(self):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")) as network, \
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")) as request:
            result = self.build()
            verified = verify_packet(self.output)
        network.assert_not_called()
        request.assert_not_called()
        self.assertEqual(result, verified)
        self.assertEqual("intake_required", result["status"])
        self.assertIs(result["template_only"], True)
        self.assertEqual(EXECUTION, result["execution"])
        self.assertEqual(20, result["file_count"])
        actual = {str(path.relative_to(self.output)) for path in self.output.rglob("*") if path.is_file()}
        self.assertEqual(REQUIRED_PATHS, actual)
        self.assertEqual(sha256((self.output / "manifest.json").read_bytes()).hexdigest(), result["manifest_sha256"])
        self.assertEqual(self.profile, result["prompt_profile"])
        self.assertEqual(self.workflow, result["workflow"])
        self.assertEqual(sha256(self.input.encode()).hexdigest(), result["input_sha256"])
        for path in actual:
            self.assertNotIn("SYNTHETIC_RAW_REQUEST_NOT_FOR_EXPORT", (self.output / path).read_text())

    def test_substantive_or_empty_input_never_claims_finished_content(self):
        for number, text in enumerate(("", "A detailed topic and production brief with finished assets asserted.")):
            result = self.build(self.root / f"packet-{number}", input_text=text)
            self.assertEqual("intake_required", result["status"])
            self.assertIs(result["template_only"], True)
            intake = json.loads((Path(result["package_path"]) / "intake.json").read_bytes())
            self.assertTrue(all(value is None for value in intake["brief"].values()))
            self.assertTrue(intake["missing_inputs"])

    def test_invalid_or_sensitive_input_fails_before_output(self):
        for value in ("x" * (MAX_INPUT_BYTES + 1), "sk-" + "SYNTHETICKEY" * 4, "\ud800", None):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(StudioError):
                self.build(input_text=value)
            self.assertFalse(self.output.exists())

    def test_bad_run_profile_or_workflow_metadata_fails_before_output(self):
        overrides = [
            {"run_id": "../escape"},
            {"prompt_profile": {**self.profile, "revision": "unknown"}},
            {"prompt_profile": {**self.profile, "sha256": "not-a-hash"}},
            {"prompt_profile": {**self.profile, "approved": True}},
            {"workflow": {"name": "../escape", "sha256": "a" * 64}},
            {"workflow": {"name": "case", "sha256": "not-a-hash"}},
        ]
        for value in overrides:
            with self.subTest(value=value), self.assertRaises(StudioError):
                self.build(**value)
            self.assertFalse(self.output.exists())

    def test_matching_optional_context_uses_only_metadata_and_exact_studio_labels(self):
        context = self.context()
        validate_business_context(self.config, context)
        self.assertFalse(self.output.exists())
        result = self.build(business_context=context)
        self.assertEqual(context.metadata(), result["business_context"])
        record = json.loads((self.output / "business-context.json").read_bytes())
        self.assertEqual({"supplied", "metadata", "creative_studio"}, set(record))
        self.assertEqual(context.as_dict()["creative_studio"], record["creative_studio"])
        for path in self.output.rglob("*"):
            if path.is_file():
                text = path.read_text()
                for private in ("SYNTHETIC_PRIVATE", "Example Business LLC", "support@example.invalid",
                                "private_admin", "private_account", "synthetic-private-owner.json"):
                    self.assertNotIn(private, text)

    def test_absent_optional_studio_is_explicit_and_does_not_infer_a_declaration(self):
        context = self.context(studio=False)
        result = self.build(business_context=context)
        self.assertEqual(context.metadata(), result["business_context"])
        record = json.loads((self.output / "business-context.json").read_bytes())
        self.assertIs(record["creative_studio"], None)
        self.assertIs(record["supplied"], True)

    def test_conflicting_studio_declarations_fail_before_output(self):
        for field in ("brand_name", "formats", "purposes", "intended_distribution_channels", "intended_ai_workspaces"):
            def change(value):
                current = value["creative_studio"][field]
                value["creative_studio"][field] = current + " changed" if isinstance(current, str) else ["Other"]
            context = self.context(mutate=change)
            with self.subTest(field=field), self.assertRaises(StudioError):
                validate_business_context(self.config, context)
            with self.assertRaises(StudioError):
                self.build(business_context=context)
            self.assertFalse(self.output.exists())

    def test_existing_destination_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("preserve this existing file")
        with self.assertRaises(StudioError):
            self.build()
        self.assertEqual("preserve this existing file", marker.read_text())
        self.assertEqual(["keep.txt"], sorted(path.name for path in self.output.iterdir()))

    def test_symlinked_output_parent_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "linked"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(StudioError):
            self.build(link / "packet")
        self.assertEqual([], list(outside.iterdir()))

    def test_missing_extra_and_symlinked_packet_entries_fail(self):
        for number, kind in enumerate(("missing", "extra", "file_symlink", "directory_symlink", "root_symlink")):
            output = self.root / f"packet-{number}"
            self.build(output)
            if kind == "missing":
                (output / "formats/videos.md").unlink()
            elif kind == "extra":
                (output / "unlisted.txt").write_text("unlisted")
            elif kind == "file_symlink":
                (output / "formats/videos.md").unlink()
                (output / "formats/videos.md").symlink_to(PROJECT / "README.md")
            elif kind == "directory_symlink":
                shutil.rmtree(output / "formats")
                (output / "formats").symlink_to(PROJECT / "docs", target_is_directory=True)
            else:
                link = self.root / "packet-link"
                link.symlink_to(output, target_is_directory=True)
                output = link
            with self.subTest(kind=kind), self.assertRaises(StudioError):
                verify_packet(output)

    def test_manifest_rejects_escape_duplicate_and_unlisted_paths(self):
        self.build()
        original = self.manifest()
        for path in ("../escape", "/absolute", "formats/../../escape", "https://example.invalid/file",
                     original["files"][1]["path"], "unlisted.md"):
            value = deepcopy(original)
            value["files"][0]["path"] = path
            self.write_manifest(value)
            with self.subTest(path=path), self.assertRaises(StudioError):
                verify_packet(self.output)

    def test_file_tampering_fails_even_when_local_hash_is_rewritten(self):
        self.build()
        path = "formats/videos.md"
        altered = (self.output / path).read_bytes() + b"\nPublication complete; ready to release.\n"
        (self.output / path).write_bytes(altered)
        with self.assertRaises(StudioError):
            verify_packet(self.output)
        self.rewrite_payload_and_hash(path, altered)
        with self.assertRaisesRegex(StudioError, "template contents"):
            verify_packet(self.output)

    def test_manifest_numeric_and_context_boolean_aliases_are_rejected(self):
        self.build()
        data = self.manifest()
        data["files"][0]["bytes"] = float(data["files"][0]["bytes"])
        self.write_manifest(data)
        with self.assertRaises(StudioError):
            verify_packet(self.output)
        output = self.root / "boolean-case"
        self.build(output)
        context = {"supplied": 0, "metadata": None, "creative_studio": None}
        self.rewrite_payload_and_hash("business-context.json", json.dumps(context).encode(), output)
        with self.assertRaises(StudioError):
            verify_packet(output)

    def test_unsupported_readiness_and_activation_assertions_fail(self):
        self.build()
        original = self.manifest()
        changes = [
            lambda data: data.update(status="completed"),
            lambda data: data.update(template_only=False),
            lambda data: data.update(approved=True),
            lambda data: data["execution"].update(provider_calls=1),
            lambda data: data["execution"].update(provider_calls=False),
            lambda data: data["execution"].update(published=True),
            lambda data: data["execution"].update(shared_memory_sync=True),
        ]
        for change in changes:
            data = deepcopy(original)
            change(data)
            self.write_manifest(data)
            with self.assertRaises(StudioError):
                verify_packet(self.output)

    def test_profile_config_context_and_input_provenance_are_checked(self):
        self.build(business_context=self.context())
        original = self.manifest()
        changes = [
            lambda data: data["prompt_profile"].update(id="unknown"),
            lambda data: data["prompt_profile"].update(sha256="invalid"),
            lambda data: data["studio_config"].update(sha256="b" * 64),
            lambda data: data["business_context"].update(sha256="b" * 64),
            lambda data: data.update(input_sha256="b" * 64),
            lambda data: data.update(input_bytes=True),
            lambda data: data.update(created_at="2026-01-01T00:00:00"),
        ]
        for change in changes:
            data = deepcopy(original)
            change(data)
            self.write_manifest(data)
            with self.assertRaises(StudioError):
                verify_packet(self.output)

    def test_duplicate_json_fields_and_oversized_evidence_are_rejected(self):
        self.build()
        original = (self.output / "manifest.json").read_bytes()
        (self.output / "manifest.json").write_bytes(b'{"schema":"one","schema":"two"}')
        with self.assertRaises(StudioError):
            verify_packet(self.output)
        (self.output / "manifest.json").write_bytes(original)
        (self.output / "formats/videos.md").write_bytes(b"x" * (MAX_FILE_BYTES + 1))
        with self.assertRaises(StudioError):
            verify_packet(self.output)
        with patch("jarvis.creative_studio.MAX_PACKET_BYTES", 1), self.assertRaises(StudioError):
            self.build(self.root / "too-large")
        self.assertFalse((self.root / "too-large").exists())

    def test_partial_write_never_leaves_a_verifiable_success(self):
        real_open = os.open

        def fail_manifest(path, flags, *args, **kwargs):
            if Path(path).name == "manifest.json" and flags & os.O_WRONLY:
                raise OSError("SYNTHETIC_PRIVATE_OS_DETAILS")
            return real_open(path, flags, *args, **kwargs)

        with patch("jarvis.creative_studio.os.open", side_effect=fail_manifest), self.assertRaises(StudioError) as caught:
            self.build()
        self.assertNotIn("SYNTHETIC_PRIVATE", str(caught.exception))
        self.assertFalse((self.output / "manifest.json").exists())
        with self.assertRaises(StudioError):
            verify_packet(self.output)

    def test_cli_verifies_and_returns_static_errors_for_invalid_packets(self):
        self.build()
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(0, main(["verify", str(self.output)]))
        self.assertEqual("intake_required", json.loads(stdout.getvalue())["status"])
        (self.output / "README.md").unlink()
        with redirect_stdout(io.StringIO()), redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            main(["verify", str(self.output)])
        self.assertEqual(2, caught.exception.code)
        self.assertNotIn(str(self.output), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
