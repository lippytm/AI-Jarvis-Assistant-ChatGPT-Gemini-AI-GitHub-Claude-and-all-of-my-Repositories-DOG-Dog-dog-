"""Exercise studio packets through the real local workflow gates and cache."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from jarvis.business_context import load_business_context
from jarvis.config import Settings
from jarvis.control_tower import ControlTower
from jarvis.creative_studio import load_studio_config, verify_packet
from jarvis.workflows import WorkflowError, WorkflowRunner
from tests.test_business_context import synthetic_record, studio_declaration


REPOSITORY = Path(__file__).resolve().parents[1]


class StudioWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workflows = self.root / "workflows"
        self.workflows.mkdir()
        (self.root / "config").mkdir()
        for relative in ("config/prompt-11-profile.json", "config/creative-studio.public.json",
                         "workflows/creative_studio_package.json"):
            shutil.copyfile(REPOSITORY / relative, self.root / relative)
        self.definition_path = self.workflows / "creative_studio_package.json"
        self.definition = json.loads(self.definition_path.read_text())
        self.tower = ControlTower(Settings("mock", self.root / "tasks.sqlite3", 5))
        self.runner = WorkflowRunner(self.tower, self.workflows,
                                     self.root / "outbox", self.root / "runs")

    def write_definition(self):
        self.definition_path.write_text(json.dumps(self.definition))

    def studio_step(self, report):
        return next(step for step in report["steps"] if step["type"] == "studio_package")

    def test_plan_resolves_configuration_without_creating_a_packet_or_calling_providers(self):
        with patch.object(self.tower, "run") as invoke, \
                patch("jarvis.workflows.build_packet") as build, \
                patch("socket.create_connection", side_effect=AssertionError("network forbidden")) as network:
            plan = self.runner.plan("creative_studio_package", "Prepare local intake")
        self.assertFalse(plan["will_execute"])
        self.assertEqual(0, plan["external_calls"])
        self.assertEqual(load_studio_config(self.root).metadata(), plan["creative_studio"])
        self.assertFalse((self.root / "outbox").exists())
        self.assertFalse((self.root / "runs").exists())
        invoke.assert_not_called()
        build.assert_not_called()
        network.assert_not_called()
        catalog = self.runner.validate_catalog()
        self.assertTrue(catalog["valid"])
        self.assertEqual(plan["creative_studio"], catalog["prompt_profile_coverage"]["workflows"]
                         ["creative_studio_package"]["creative_studio"])

    def test_packet_and_local_review_are_written_before_approval_and_nothing_runs_after(self):
        self.definition["steps"].append({"id": "after_approval", "type": "ai", "provider": "mock",
                                         "prompt": "Must not execute"})
        self.write_definition()
        with patch.object(self.tower, "run") as invoke, \
                patch("socket.create_connection", side_effect=AssertionError("network forbidden")) as network:
            report = self.runner.run("creative_studio_package", "Prepare local intake")
        invoke.assert_not_called()
        network.assert_not_called()
        self.assertEqual("pending_approval", report["status"])
        self.assertEqual(["after_approval"], report["not_run_steps"])
        packet = self.studio_step(report)
        self.assertEqual("drafted", packet["status"])
        self.assertEqual("intake_required", packet["package_status"])
        self.assertIs(packet["template_only"], True)
        verified = verify_packet(Path(packet["package_path"]))
        self.assertIs(verified["valid"], True)
        self.assertEqual(packet["manifest_sha256"], verified["manifest_sha256"])
        self.assertEqual(report["run_id"], verified["run_id"])
        handoffs = [step for step in report["steps"] if step["type"] == "handoff"]
        self.assertEqual(1, len(handoffs))
        self.assertTrue(Path(handoffs[0]["path"]).is_file())
        self.assertIn(packet["manifest_sha256"], Path(handoffs[0]["path"]).read_text())
        self.assertEqual(1, len(list((self.root / "approvals").glob("*.json"))))

    def test_cached_packet_is_verified_before_reuse_and_tampering_requires_fresh_run(self):
        first = self.runner.run("creative_studio_package", "Same intake")
        repeated = self.runner.run("creative_studio_package", "Same intake")
        self.assertTrue(repeated["reused"])
        self.assertEqual(first["run_id"], repeated["run_id"])
        package = Path(self.studio_step(first)["package_path"])
        payload = next(path for path in package.rglob("*.md") if path.is_file())
        payload.write_text(payload.read_text() + "\nAltered outside the retained packet.\n")
        with self.assertRaisesRegex(WorkflowError, "Cached studio packet is missing or invalid"):
            self.runner.run("creative_studio_package", "Same intake")
        fresh = self.runner.run("creative_studio_package", "Same intake", force=True)
        self.assertNotEqual(first["run_id"], fresh["run_id"])
        self.assertTrue(verify_packet(Path(self.studio_step(fresh)["package_path"]))["valid"])
        self.assertIn("Altered outside", payload.read_text())

    def test_cached_paths_and_manifest_anchors_cannot_substitute_another_packet(self):
        first = self.runner.run("creative_studio_package", "Same intake")
        cache = self.root / "runs" / (first["idempotency_key"] + ".json")
        for field, value in (("package_path", str(self.root / "outside")),
                             ("manifest_sha256", "0" * 64)):
            altered = json.loads(json.dumps(first))
            self.studio_step(altered)[field] = value
            cache.write_text(json.dumps(altered))
            with self.assertRaisesRegex(WorkflowError, "Cached studio packet is missing or invalid"):
                self.runner.run("creative_studio_package", "Same intake")
        self.assertFalse((self.root / "outside").exists())

    def test_cache_reuse_rejects_inconsistent_execution_and_activation_assertions(self):
        first = self.runner.run("creative_studio_package", "Same intake")
        cache = self.root / "runs" / (first["idempotency_key"] + ".json")
        changes = [
            ("overall status", lambda r: r.update(status="completed")),
            ("workflow", lambda r: r.update(workflow="different_workflow")),
            ("workflow hash", lambda r: r.update(workflow_sha256="0" * 64)),
            ("cache identity", lambda r: r.update(idempotency_key="0" * 64)),
            ("profile status", lambda r: r.update(profile_status="unprofiled_ad_hoc")),
            ("extra assertion", lambda r: r.update(published=True)),
            ("remaining suffix", lambda r: r.update(not_run_steps=["studio_templates"])),
            ("step order", lambda r: r["steps"].reverse()),
            ("missing executed step", lambda r: r["steps"].pop(1)),
            ("studio type", lambda r: self.studio_step(r).update(type="ai")),
            ("studio status", lambda r: self.studio_step(r).update(status="completed")),
            ("studio output", lambda r: self.studio_step(r).update(output="Published and approved")),
            ("studio count", lambda r: self.studio_step(r).update(file_count=19)),
            ("studio template assertion", lambda r: self.studio_step(r).update(template_only=False)),
            ("activation", lambda r: self.studio_step(r)["execution"].update(
                provider_calls=3, published=True, approval_granted=True)),
            ("numeric boolean alias", lambda r: self.studio_step(r)["execution"].update(provider_calls=False)),
            ("approval claim", lambda r: r["steps"][-1]["approval"].update(status="approved")),
        ]
        for label, change in changes:
            with self.subTest(change=label):
                altered = json.loads(json.dumps(first))
                change(altered)
                cache.write_text(json.dumps(altered))
                with patch.object(self.tower, "run") as invoke:
                    with self.assertRaisesRegex(WorkflowError, "Cached studio packet is missing or invalid"):
                        self.runner.run("creative_studio_package", "Same intake")
                invoke.assert_not_called()
        self.assertTrue(verify_packet(Path(self.studio_step(first)["package_path"]))["valid"])

    def test_approval_before_studio_reuses_the_valid_unexecuted_suffix(self):
        self.definition["steps"].insert(0, {"id": "early_review", "type": "approval",
                                            "summary": "Review before creating any templates"})
        self.write_definition()
        first = self.runner.run("creative_studio_package", "Same intake")
        with patch("jarvis.workflows.verify_packet") as verify, \
                patch("jarvis.workflows.build_packet") as build, \
                patch.object(self.tower, "run") as invoke:
            reused = self.runner.run("creative_studio_package", "Same intake")
        self.assertTrue(reused["reused"])
        self.assertEqual(first["run_id"], reused["run_id"])
        self.assertEqual("pending_approval", reused["status"])
        self.assertEqual(["early_review"], [step["id"] for step in reused["steps"]])
        self.assertEqual([step["id"] for step in self.definition["steps"][1:]], reused["not_run_steps"])
        self.assertEqual([], list((self.root / "outbox").glob("*-studio")))
        verify.assert_not_called()
        build.assert_not_called()
        invoke.assert_not_called()

    def test_completed_studio_workflow_without_approval_can_reuse_its_packet(self):
        self.definition["steps"].pop()
        self.write_definition()
        first = self.runner.run("creative_studio_package", "Same intake")
        reused = self.runner.run("creative_studio_package", "Same intake")
        self.assertTrue(reused["reused"])
        self.assertEqual(first["run_id"], reused["run_id"])
        self.assertEqual("completed", reused["status"])
        self.assertEqual([], reused["not_run_steps"])
        self.assertEqual("intake_required", self.studio_step(reused)["package_status"])

    def test_configuration_bytes_change_plan_catalog_and_cache_identity(self):
        first_plan = self.runner.plan("creative_studio_package", "Same intake")
        first_catalog = self.runner.validate_catalog()["prompt_profile_coverage"]["catalog_sha256"]
        first = self.runner.run("creative_studio_package", "Same intake")
        path = self.root / "config/creative-studio.public.json"
        path.write_bytes(path.read_bytes() + b"\n")
        changed_plan = self.runner.plan("creative_studio_package", "Same intake")
        changed = self.runner.run("creative_studio_package", "Same intake")
        self.assertEqual(first["workflow_sha256"], changed["workflow_sha256"])
        self.assertEqual(first["prompt_profile"], changed["prompt_profile"])
        self.assertNotEqual(first_plan["creative_studio"], changed_plan["creative_studio"])
        self.assertNotEqual(first_catalog, self.runner.validate_catalog()["prompt_profile_coverage"]["catalog_sha256"])
        self.assertNotEqual(first["idempotency_key"], changed["idempotency_key"])
        self.assertNotEqual(first["run_id"], changed["run_id"])

    def test_missing_config_and_per_step_overrides_fail_before_artifact_creation(self):
        config = self.root / "config/creative-studio.public.json"
        config.unlink()
        with self.assertRaisesRegex(WorkflowError, "Cannot resolve local creative studio configuration"):
            self.runner.plan("creative_studio_package", "Intake")
        with self.assertRaises(WorkflowError):
            self.runner.run("creative_studio_package", "Intake")
        self.assertFalse(self.runner.validate_catalog()["valid"])
        self.assertFalse((self.root / "outbox").exists())
        shutil.copyfile(REPOSITORY / "config/creative-studio.public.json", config)
        step = next(step for step in self.definition["steps"] if step["type"] == "studio_package")
        step["config_url"] = "https://example.invalid/unreviewed"
        self.write_definition()
        with self.assertRaisesRegex(WorkflowError, "accepts only id and type"):
            self.runner.run("creative_studio_package", "Intake")
        self.assertFalse((self.root / "outbox").exists())

    def test_business_context_is_bound_by_metadata_and_conflicts_stop_plan_and_run(self):
        source = synthetic_record()
        source["creative_studio"] = studio_declaration()
        source_path = self.root / "private-source.json"
        source_path.write_text(json.dumps(source))
        first = self.runner.run("creative_studio_package", "Same intake", business_context=source_path)
        expected = load_business_context(source_path).metadata()
        self.assertEqual(expected, first["business_context"])
        verified = verify_packet(Path(self.studio_step(first)["package_path"]))
        self.assertEqual(expected, verified["business_context"])
        repeated = self.runner.run("creative_studio_package", "Same intake", business_context=source_path)
        self.assertTrue(repeated["reused"])
        source["creative_studio"]["brand_name"] = "A different owner-declared studio"
        source_path.write_text(json.dumps(source))
        before = sorted(str(path) for path in (self.root / "outbox").rglob("*"))
        for action in (self.runner.plan, self.runner.run):
            with self.assertRaisesRegex(WorkflowError, "Business context conflicts"):
                action("creative_studio_package", "Same intake", business_context=source_path)
        self.assertEqual(before, sorted(str(path) for path in (self.root / "outbox").rglob("*")))


if __name__ == "__main__":
    unittest.main()
