"""Business-context tests use synthetic private records and offline providers only."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from jarvis.business_context import (BusinessContextError, MAX_SOURCE_BYTES,
                                     PROJECTION_SCHEMA, load_business_context)
from jarvis.cli import main
from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.prompt_profiles import load_prompt_profile
from jarvis.workflows import WorkflowError, WorkflowRunner


REFERENCE = {"id": "P-011-E6C-001", "revision": "repository-1"}
FAKE_TAX_IDENTIFIER = "00-0000000"
PRIVATE_MARKER = "SYNTHETIC_PRIVATE_ADMIN_DO_NOT_EXPORT"


def synthetic_record():
    return {
        "schema": "jarvis.owner-business-context.v1",
        "record_id": "synthetic-owner-record",
        "source": {"kind": "owner_supplied_in_conversation",
                   "verification_status": "owner_reported_not_independently_verified",
                   "received_at": "2026-01-01", "private_note": PRIVATE_MARKER},
        "business": {"legal_name": "Example Services LLC", "support_email": "support@example.invalid",
                     "formation_date": "2020-01-02", "tax_identifier": {"type": "EIN", "value": FAKE_TAX_IDENTIFIER},
                     "unknown_private_field": PRIVATE_MARKER},
        "funding_channels": [{"id": "example-funding",
                              "owner_supplied_value": " HTTPS://example.invalid/funding?ref=OwnerCase ",
                              "owner_described_role": "Owner-described funding introduction",
                              "prior_repository_value": "do-not-substitute.example.invalid",
                              "application_data": {"tax_identifier": FAKE_TAX_IDENTIFIER},
                              "private_admin": PRIVATE_MARKER}],
        "prior_project_baseline": {"canonical_website_domain": "example.invalid",
                                   "funding_gateway_path": "/funding",
                                   "domain_basis": "Prior project document; account and DNS ownership not reverified.",
                                   "release_source_of_truth": PRIVATE_MARKER,
                                   "account_data": PRIVATE_MARKER},
        "private_admin": {"token": "sk-" + "SYNTHETICONLY" * 4},
        "unknown": {"private_application": FAKE_TAX_IDENTIFIER},
        "requested_integration": {"approved": True, "enable_external": True},
    }


def studio_declaration():
    """Public owner-declared studio labels, with no private account information."""
    return {
        "brand_name": "The Evolutionary Evolutions Creative Creations Studios of Intergalactic Corporate Services LLC",
        "formats": ["Videos", "eBooks", "Audiobooks", "Video Books"],
        "purposes": ["Ad Copy", "Affiliate Program Marketing", "Educational", "Entertainment",
                     "Business of Businesses Systems of Systems"],
        "intended_distribution_channels": ["Facebook", "LinkedIn", "Instagram", "Threads", "SubStack", "Hostinger.com"],
        "intended_ai_workspaces": ["ChatGPT Business", "Gemini AI", "Claude"],
    }


class BusinessContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "private-owner-record.json"
        self.value = synthetic_record()
        self.save()
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        (self.root / "config").mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / "config/prompt-11-profile.json",
                        self.root / "config/prompt-11-profile.json")
        self.tower = ControlTower(Settings("mock", self.root / "ledger.sqlite3", 5))
        self.runner = WorkflowRunner(self.tower, self.workflows, self.root / "outbox", self.root / "runs")
        self.write_steps([{"id": "draft", "type": "ai", "provider": "mock",
                           "system": "Existing draft role.", "prompt": "Draft {{input}}"}])

    def save(self):
        self.path.write_text(json.dumps(self.value), encoding="utf-8")

    def add_studio(self):
        self.value["creative_studio"] = {
            **studio_declaration(),
            "tax_identifier": {"type": "EIN", "value": FAKE_TAX_IDENTIFIER},
            "private_admin": PRIVATE_MARKER,
            "account_data": {"token": "sk-" + "SYNTHETICONLY" * 4},
            "authenticated": True, "approved": True, "enable_external": True,
            "declaration_status": "independently_verified",
            "connection_status": "authenticated",
        }
        self.save()

    def write_steps(self, steps):
        (self.workflows / "case.json").write_text(json.dumps({"prompt_profile": REFERENCE, "steps": steps}), encoding="utf-8")

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(list(args))
        return status, stdout.getvalue(), stderr.getvalue()

    def assert_private_absent(self, value):
        text = value if isinstance(value, str) else json.dumps(value)
        for private in (FAKE_TAX_IDENTIFIER, PRIVATE_MARKER, "tax_identifier", "private_admin",
                        "application_data", "prior_repository_value", "SYNTHETICONLY", str(self.path)):
            self.assertNotIn(private, text)

    def test_projection_copies_only_allowed_facts_and_preserves_exact_owner_values(self):
        projected = load_business_context(self.path).as_dict()
        self.assertEqual(PROJECTION_SCHEMA, projected["schema"])
        self.assertEqual("owner_reported_not_independently_verified", projected["verification_status"])
        self.assertEqual({key: self.value["business"][key] for key in ("legal_name", "support_email", "formation_date")},
                         projected["business"])
        self.assertEqual([{key: self.value["funding_channels"][0][key]
                           for key in ("id", "owner_supplied_value", "owner_described_role")}],
                         projected["funding_channels"])
        self.assertEqual({"canonical_website_domain": "example.invalid", "funding_gateway_path": "/funding",
                          "source_qualifier": self.value["prior_project_baseline"]["domain_basis"]},
                         projected["prior_project_baseline"])
        self.assert_private_absent(projected)

    def test_hash_uses_only_canonical_projection_and_snapshot_cannot_be_mutated(self):
        context = load_business_context(self.path)
        pack = context.as_dict()
        digest = pack.pop("sha256")
        encoded = json.dumps(pack, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(sha256(encoded).hexdigest(), digest)
        self.assertNotEqual(sha256(self.path.read_bytes()).hexdigest(), digest)
        pack["business"]["legal_name"] = "Attempted caller mutation"
        self.assertEqual("Example Services LLC", context.as_dict()["business"]["legal_name"])
        self.value["business"]["tax_identifier"]["value"] = "00-1111111"
        self.value["private_admin"]["new_private_field"] = "SYNTHETIC_NEW_PRIVATE_VALUE"
        self.save()
        self.assertEqual(context.as_dict(), load_business_context(self.path).as_dict())

    def test_omitting_studio_preserves_preextension_projection_bytes_and_hash(self):
        # This fixture and digest were captured before creative_studio was added.
        legacy = (
            '{"business":{"formation_date":"2020-01-02","legal_name":"Example Services LLC",'
            '"support_email":"support@example.invalid"},"funding_channels":[{"id":"example-funding",'
            '"owner_described_role":"Owner-described funding introduction",'
            '"owner_supplied_value":" HTTPS://example.invalid/funding?ref=OwnerCase "}],'
            '"prior_project_baseline":{"canonical_website_domain":"example.invalid",'
            '"funding_gateway_path":"/funding",'
            '"source_qualifier":"Prior project document; account and DNS ownership not reverified."},'
            '"projection_id":"owner-business-context-v1:synthetic-owner-record",'
            '"record_id":"synthetic-owner-record","schema":"jarvis.business-context-projection.v1",'
            '"verification_status":"owner_reported_not_independently_verified"}'
        )
        context = load_business_context(self.path)
        self.assertEqual(legacy.encode("utf-8"), context._projection_json.encode("utf-8"))
        self.assertEqual("ed7fe61b0bce9745ab44db1887c15d6fcd8a670837f6c391cae8e4fb036ebb40", context.sha256)
        self.assertNotIn("creative_studio", context.as_dict())

    def test_studio_projects_exact_labels_and_fixed_qualifications_only(self):
        self.add_studio()
        context = load_business_context(self.path)
        pack = context.as_dict()
        expected = {**studio_declaration(), "declaration_status": "owner_declared_intended_use",
                    "connection_status": "not_asserted_by_this_context"}
        self.assertEqual(expected, pack["creative_studio"])
        self.assertEqual("Example Services LLC", pack["business"]["legal_name"])
        self.assert_private_absent(pack)
        for excluded in ("authenticated", "approved", "enable_external", "account_data"):
            self.assertNotIn(excluded, pack["creative_studio"])
        pack["creative_studio"]["formats"].append("Caller mutation")
        self.assertEqual(expected, context.as_dict()["creative_studio"])

    def test_studio_preserves_accepted_spelling_order_spaces_and_boundary_lengths(self):
        self.add_studio()
        studio = self.value["creative_studio"]
        studio["brand_name"] = " Brand \u00e9 "
        studio["formats"] = [" Video Books ", "eBOOKS", "Videos"]
        studio["purposes"] = [" Educational "]
        studio["intended_distribution_channels"] = ["SubStack", " Facebook "]
        studio["intended_ai_workspaces"] = ["Claude", "Gemini AI", " ChatGPT Business "]
        self.save()
        projected = load_business_context(self.path).as_dict()["creative_studio"]
        for field in studio_declaration():
            self.assertEqual(studio[field], projected[field])
        studio["brand_name"] = "B" * 256
        studio["formats"] = ["F" * 256] + [f"format-{index}" for index in range(15)]
        self.save()
        projected = load_business_context(self.path).as_dict()["creative_studio"]
        self.assertEqual(studio["brand_name"], projected["brand_name"])
        self.assertEqual(studio["formats"], projected["formats"])

    def test_studio_facts_invalidate_cache_but_private_and_auth_claims_do_not(self):
        self.add_studio()
        context = load_business_context(self.path)
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            first = self.runner.run("case", "same brief", business_context=self.path)
            studio = self.value["creative_studio"]
            studio["tax_identifier"]["value"] = "00-3333333"
            studio["private_admin"] = "CHANGED_SYNTHETIC_PRIVATE_VALUE"
            studio["unknown"] = {"application_data": "EXCLUDED_SYNTHETIC_APPLICATION"}
            studio["authenticated"] = False
            studio["connection_status"] = "new_source_claim"
            self.save()
            self.assertEqual(context.as_dict(), load_business_context(self.path).as_dict())
            reused = self.runner.run("case", "same brief", business_context=self.path)
            self.assertTrue(reused["reused"])
            self.assertEqual(first["idempotency_key"], reused["idempotency_key"])
            studio["purposes"].append("Studio training")
            self.save()
            changed = self.runner.run("case", "same brief", business_context=self.path)
        self.assertEqual(2, invoke.call_count)
        self.assertNotEqual(first["business_context"]["sha256"], changed["business_context"]["sha256"])
        self.assertNotEqual(first["idempotency_key"], changed["idempotency_key"])
        self.assertIn("Studio training", invoke.call_args.args[0])
        self.assertNotIn("CHANGED_SYNTHETIC_PRIVATE_VALUE", invoke.call_args.args[0])
        self.assertNotIn("EXCLUDED_SYNTHETIC_APPLICATION", invoke.call_args.args[0])
        before_reorder = load_business_context(self.path).sha256
        studio["formats"].reverse()
        self.save()
        self.assertNotEqual(before_reorder, load_business_context(self.path).sha256)

    def test_invalid_studio_declarations_fail_statically(self):
        invalid_values = [None, [], {}, "private-value", False]
        declarations = [{"creative_studio": value} for value in invalid_values]
        for field in studio_declaration():
            missing = studio_declaration()
            missing.pop(field)
            declarations.append({"creative_studio": missing})
            values = ([None, [], "", " ", "B" * 257, "line\nbreak", "bad\ud800"]
                      if field == "brand_name" else
                      [None, {}, "Videos", [], ["Videos"] * 2, [f"label-{index}" for index in range(17)],
                       [""], [" "], [42], [{"private": PRIVATE_MARKER}], ["L" * 257], ["line\nbreak"], ["bad\ud800"]])
            for value in values:
                declarations.append({"creative_studio": {**studio_declaration(), field: value}})
        for index, declaration in enumerate(declarations):
            with self.subTest(case=index):
                self.value = {**synthetic_record(), **declaration}
                self.save()
                with self.assertRaisesRegex(BusinessContextError, "^Invalid owner business context$"):
                    load_business_context(self.path)
        with patch.object(self.tower, "run") as invoke:
            with self.assertRaises(BusinessContextError):
                self.runner.run("case", "brief", business_context=self.path)
        invoke.assert_not_called()

    def test_credential_in_each_allowed_studio_field_blocks_export_and_execution(self):
        credential = "sk-" + "SYNTHETICONLY" * 3
        for field in studio_declaration():
            with self.subTest(field=field):
                self.add_studio()
                self.value["creative_studio"][field] = credential if field == "brand_name" else [credential]
                self.save()
                with self.assertRaisesRegex(BusinessContextError, "^Business context projection contains sensitive data$"):
                    load_business_context(self.path)
                status, stdout, stderr = self.cli("business-context", str(self.path), "--json")
                self.assertEqual((2, "", "Jarvis error: Business context projection contains sensitive data\n"),
                                 (status, stdout, stderr))
                with patch.object(self.tower, "run") as invoke:
                    with self.assertRaises(BusinessContextError):
                        self.runner.run("case", "brief", allow_sensitive=True, business_context=self.path)
                invoke.assert_not_called()

    def test_projection_and_plan_make_no_network_or_provider_calls(self):
        self.add_studio()
        self.write_steps([{"id": "inventory", "type": "github_inventory"},
                          {"id": "ai", "type": "ai", "provider": "chatgpt", "prompt": "{{input}}"}])
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")) as network, \
                patch("socket.create_connection", side_effect=AssertionError("network forbidden")) as socket, \
                patch("jarvis.workflows.list_repositories") as inventory, patch.object(self.tower, "run") as invoke:
            context = load_business_context(self.path)
            plan = self.runner.plan("case", "preview", business_context=self.path)
        for operation in (network, socket, inventory, invoke):
            operation.assert_not_called()
        self.assertFalse(plan["will_execute"])
        self.assertEqual(context.metadata(), plan["business_context"])
        self.assert_private_absent(plan)

    def test_same_safe_context_reaches_every_executed_ai_step_without_system_changes(self):
        self.add_studio()
        roles = ("Existing draft role.", "Independent review role.", "Existing handoff role.")
        self.write_steps([{"id": f"step{index}", "type": "ai", "provider": "mock", "system": role,
                           "prompt": "Review {{input}}"} for index, role in enumerate(roles)])
        context = load_business_context(self.path)
        profile = load_prompt_profile(REFERENCE, self.root)
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            report = self.runner.run("case", "shared brief", business_context=self.path)
        self.assertEqual("completed", report["status"])
        self.assertEqual(3, invoke.call_count)
        for call, role in zip(invoke.call_args_list, roles):
            self.assertEqual(context.task_data() + "\n\nStep task:\nReview shared brief", call.args[0])
            self.assertIn('"creative_studio"', call.args[0])
            self.assertEqual(profile.system_instructions(role), call.args[2])
            self.assertNotIn("Example Services LLC", call.args[2])
            self.assertNotIn(studio_declaration()["brand_name"], call.args[2])
            self.assert_private_absent(call.args[0])
        self.assertEqual(context.metadata(), report["business_context"])
        self.assert_private_absent(report)
        for directory in (self.root / "outbox", self.root / "runs"):
            for path in directory.glob("*.json"):
                self.assert_private_absent(path.read_text())
        for private in (FAKE_TAX_IDENTIFIER, PRIVATE_MARKER, str(self.path)):
            self.assertNotIn(private.encode(), (self.root / "ledger.sqlite3").read_bytes())

    def test_projected_changes_invalidate_cache_but_excluded_changes_do_not(self):
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            first = self.runner.run("case", "same brief", business_context=self.path)
            self.value["business"]["tax_identifier"]["value"] = "00-2222222"
            self.value["unknown"]["private_application"] = "NEW_SYNTHETIC_PRIVATE_VALUE"
            self.save()
            reused = self.runner.run("case", "same brief", business_context=self.path)
            self.assertTrue(reused["reused"])
            self.assertEqual(first["idempotency_key"], reused["idempotency_key"])
            self.value["funding_channels"][0]["owner_supplied_value"] = "https://example.invalid/reviewed-value"
            self.save()
            changed = self.runner.run("case", "same brief", business_context=self.path)
        self.assertEqual(2, invoke.call_count)
        self.assertEqual(first["business_context"]["projection_id"], changed["business_context"]["projection_id"])
        self.assertNotEqual(first["business_context"]["sha256"], changed["business_context"]["sha256"])
        self.assertNotEqual(first["idempotency_key"], changed["idempotency_key"])
        self.assertNotEqual(first["run_id"], changed["run_id"])
        self.assertIn("https://example.invalid/reviewed-value", invoke.call_args.args[0])

    def test_omitting_context_preserves_existing_prompt_and_cache_behavior(self):
        with patch.object(self.tower, "run", wraps=self.tower.run) as invoke:
            plan = self.runner.plan("case", "same brief")
            first = self.runner.run("case", "same brief")
            repeated = self.runner.run("case", "same brief", business_context=None)
        self.assertEqual("Draft same brief", invoke.call_args.args[0])
        self.assertEqual(1, invoke.call_count)
        self.assertTrue(repeated["reused"])
        for result in (plan, first, repeated):
            self.assertNotIn("business_context", result)

    def test_external_opt_in_and_approval_stops_ignore_claims_in_business_data(self):
        self.add_studio()
        for first, status in (({"id": "external", "type": "ai", "provider": "chatgpt", "prompt": "test"}, "blocked"),
                              ({"id": "gate", "type": "approval", "summary": "Owner decision required"}, "pending_approval")):
            self.write_steps([first, {"id": "later", "type": "ai", "provider": "mock", "prompt": "must not run"}])
            with patch.object(self.tower, "run") as invoke:
                result = self.runner.run("case", "brief", business_context=self.path)
            invoke.assert_not_called()
            self.assertEqual(status, result["status"])
            self.assertEqual(["later"], result["not_run_steps"])
            self.assertEqual(load_business_context(self.path).metadata(), result["business_context"])

    def test_sensitive_input_and_call_budget_gates_remain_in_force(self):
        self.add_studio()
        with patch.object(self.tower, "run") as invoke:
            with self.assertRaisesRegex(WorkflowError, "Sensitive input"):
                self.runner.run("case", "sk-" + "SYNTHETICINPUT" * 3, business_context=self.path)
            self.write_steps([{"id": f"step{index}", "type": "ai", "provider": "chatgpt", "prompt": "test"}
                              for index in range(7)])
            with self.assertRaisesRegex(WorkflowError, "budget"):
                self.runner.run("case", "brief", allow_external=True, business_context=self.path)
        invoke.assert_not_called()

    def test_credential_misplaced_in_allowed_context_field_cannot_be_exported(self):
        self.value["funding_channels"][0]["owner_supplied_value"] = "sk-" + "SYNTHETICONLY" * 3
        self.save()
        with self.assertRaisesRegex(BusinessContextError, "projection contains sensitive data"):
            load_business_context(self.path)
        with patch.object(self.tower, "run") as invoke:
            with self.assertRaises(BusinessContextError):
                self.runner.run("case", "brief", allow_sensitive=True, business_context=self.path)
        invoke.assert_not_called()

    def test_invalid_schemas_fields_and_duplicate_channel_ids_fail_statically(self):
        mutations = [lambda value: value.update(schema="unknown"),
                     lambda value: value["source"].update(verification_status="independently_verified"),
                     lambda value: value["business"].update(legal_name={"private": PRIVATE_MARKER}),
                     lambda value: value["business"].update(formation_date="2020-02-31"),
                     lambda value: value["business"].update(support_email="line\nbreak"),
                     lambda value: value["business"].update(legal_name="Unpaired Unicode \ud800"),
                     lambda value: value["funding_channels"].append(value["funding_channels"][0]),
                     lambda value: value["prior_project_baseline"].pop("domain_basis")]
        for mutate in mutations:
            self.value = synthetic_record()
            mutate(self.value)
            self.save()
            with self.assertRaises(BusinessContextError) as caught:
                load_business_context(self.path)
            self.assertEqual("Invalid owner business context", str(caught.exception))

    def test_malformed_oversized_missing_symlinked_and_remote_sources_are_refused(self):
        for data in (b"[]", b"\xff", b'{"private-value":', b'{"schema":"one","schema":"two"}',
                     b'{"value":NaN}', b"x" * (MAX_SOURCE_BYTES + 1)):
            self.path.write_bytes(data)
            with self.assertRaisesRegex(BusinessContextError, "^Cannot load local business context$"):
                load_business_context(self.path)
        self.path.unlink()
        for path in (self.path, self.root, "https://example.invalid/private-owner-record.json"):
            with self.assertRaisesRegex(BusinessContextError, "^Cannot load local business context$"):
                load_business_context(path)
        target = self.root / "synthetic-target.json"
        target.write_text(json.dumps(synthetic_record()))
        self.path.symlink_to(target)
        with self.assertRaisesRegex(BusinessContextError, "^Cannot load local business context$"):
            load_business_context(self.path)

    def test_cli_export_is_sanitized_and_does_not_construct_a_control_tower(self):
        self.add_studio()
        with patch("jarvis.cli.ControlTower") as tower, patch("urllib.request.urlopen") as network:
            status, stdout, stderr = self.cli("business-context", str(self.path), "--json")
        self.assertEqual(0, status, stderr)
        self.assertEqual(load_business_context(self.path).as_dict(), json.loads(stdout))
        self.assert_private_absent(stdout)
        tower.assert_not_called()
        network.assert_not_called()
        status, stdout, stderr = self.cli("business-context", str(self.root / "private-missing.json"), "--json")
        self.assertEqual(2, status)
        self.assertEqual("", stdout)
        self.assertEqual("Jarvis error: Cannot load local business context\n", stderr)

    def test_cli_optional_flags_pass_the_same_projection_into_plan_and_mock_run(self):
        self.add_studio()
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(self.root)
        with patch.dict(os.environ, {"JARVIS_DB_PATH": str(self.root / "cli.sqlite3")}), \
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")) as network:
            plan_status, plan_text, plan_error = self.cli("plan", "case", "brief", "--business-context", str(self.path), "--json")
            run_status, run_text, run_error = self.cli("run", "case", "brief", "--business-context", str(self.path), "--json")
        self.assertEqual((0, 0), (plan_status, run_status), (plan_error, run_error))
        self.assertEqual(json.loads(plan_text)["business_context"], json.loads(run_text)["business_context"])
        self.assert_private_absent(plan_text + run_text)
        network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
