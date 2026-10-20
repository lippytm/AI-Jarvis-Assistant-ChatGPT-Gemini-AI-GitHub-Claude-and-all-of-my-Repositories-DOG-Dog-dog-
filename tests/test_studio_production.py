"""Synthetic local source-DAG and immutable production-packet regressions."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from jarvis.creative_studio import CONFIG_PATH
from jarvis.prompt_profiles import PROFILE_PATH, PROFILE_ID, PROFILE_REVISION, load_prompt_profile
from jarvis.studio_production import (
    BRIEF_SCHEMA, EXECUTION, MAX_ASSET_BYTES, MAX_BRIEF_BYTES, MAX_REVIEWS,
    StudioProductionError, build_production_plan, verify_production_plan,
)


PROJECT = Path(__file__).resolve().parents[1]


class StudioProductionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        (self.project / "config").mkdir(parents=True)
        for path in (CONFIG_PATH, PROFILE_PATH):
            shutil.copyfile(PROJECT / path, self.project / path)
        self.work = self.root / "brief-work"
        (self.work / "assets").mkdir(parents=True)
        self.brief_path = self.work / "brief.json"
        self.output = self.root / "packet"
        asset_data = (
            ("ebook", "ebook_manuscript", b"# A useful human-led workflow\n\nA draft chapter explains task boundaries, evidence and review.\n"),
            ("narration", "narration_script", b"# Narration draft\n\nExplain the chapter slowly, then pause before the review example.\n"),
            ("video", "video_script", b"# Video script draft\n\nScene one: show the source artifact and its review state.\n"),
            ("video-book", "video_book_storyboard", b"# Video Book storyboard draft\n\nMap the chapter to narration, scenes and captions.\n"),
        )
        assets = []
        for asset_id, kind, raw in asset_data:
            path = "assets/" + asset_id + ".md"
            (self.work / path).write_bytes(raw)
            assets.append({"id": asset_id, "kind": kind, "path": path,
                           "sha256": sha256(raw).hexdigest(), "parents": []})
        parent = {"asset_id": "ebook", "sha256": assets[0]["sha256"]}
        assets[1]["parents"] = [dict(parent)]
        assets[2]["parents"] = [dict(parent)]
        assets[3]["parents"] = [dict(parent), {"asset_id": "narration", "sha256": assets[1]["sha256"]}]
        self.brief = {
            "schema": BRIEF_SCHEMA, "project_id": "synthetic-production", "revision": "draft-1",
            "title": "A human-led production example", "objective": "Make four reviewable adaptations of one local draft.",
            "audience": "Operators learning to inspect source and review evidence.", "language": "en",
            "purposes": ["Educational", "Business of Businesses Systems of Systems"],
            "formats": ["Videos", "eBooks", "Audiobooks", "Video Books"],
            "source_declaration": "provided_local_drafts", "assets": assets, "reviews": [],
        }
        self.save()

    def save(self):
        self.brief_path.write_text(json.dumps(self.brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def build(self, output=None):
        return build_production_plan(self.project, self.brief_path, output or self.output)

    def manifest(self):
        return json.loads((self.output / "manifest.json").read_bytes())

    def write_manifest(self, value):
        (self.output / "manifest.json").write_text(json.dumps(value), encoding="utf-8")

    def rehash(self, path, raw):
        (self.output / path).write_bytes(raw)
        manifest = self.manifest()
        record = next(item for item in manifest["files"] if item["path"] == path)
        record.update({"sha256": sha256(raw).hexdigest(), "bytes": len(raw)})
        self.write_manifest(manifest)

    def review(self, *, asset="ebook", result="pass", digest=None, reviewer="Synthetic reviewer"):
        declared = next(item for item in self.brief["assets"] if item["id"] == asset)
        return {"asset_id": asset, "asset_sha256": digest or declared["sha256"],
                "reviewer": reviewer, "result": result, "note": "Synthetic recorded assertion; identity and review are unverified."}

    def test_complete_draft_graph_packages_actual_sources_and_never_calls_network(self):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")) as socket, \
                patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")) as request, \
                patch("jarvis.control_tower.ControlTower", side_effect=AssertionError("runtime forbidden")) as tower:
            result = self.build()
            self.assertEqual(result, verify_production_plan(self.output))
        socket.assert_not_called()
        request.assert_not_called()
        tower.assert_not_called()
        self.assertEqual("prepared_for_review", result["status"])
        self.assertEqual("release_blocked", result["release_status"])
        self.assertEqual(EXECUTION, result["execution"])
        self.assertEqual(["ebook", "narration", "video", "video-book"], result["dependency_order"])
        self.assertEqual(13, result["file_count"])
        self.assertTrue(result["draft_assets_only"])
        self.assertTrue(result["contains_source_drafts"])
        self.assertEqual([], result["blockers"])
        self.assertTrue(result["release_blockers"])
        self.assertEqual(self.brief_path.read_bytes(), (self.output / "brief.json").read_bytes())
        for asset in self.brief["assets"]:
            self.assertEqual((self.work / asset["path"]).read_bytes(), (self.output / "sources" / (asset["id"] + ".md")).read_bytes())
        self.assertTrue(all(item["status"] == "prepared_for_review" and not item["finished_edition_produced"]
                            for item in result["formats"]))
        self.assertEqual("unverified", result["evidence_scope"]["rights"])
        self.assertEqual("not_established", result["evidence_scope"]["independent_content_qa"])

    def test_exact_profile_config_bytes_and_guidance_are_bound_to_handoffs(self):
        result = self.build()
        profile = load_prompt_profile({"id": PROFILE_ID, "revision": PROFILE_REVISION}, self.project)
        self.assertEqual(profile.metadata(), result["prompt_profile"])
        for path in (CONFIG_PATH, PROFILE_PATH):
            self.assertEqual((self.project / path).read_bytes(), (self.output / path).read_bytes())
        for path in (self.output / "ai-workspaces").iterdir():
            text = path.read_text()
            self.assertIn(profile.sha256, text)
            self.assertIn("draft_not_sent", text)
            self.assertIn(self.brief["objective"], text)
            self.assertTrue(all(guidance in text for guidance in profile.guidance))
        self.assertEqual(sha256((self.output / "manifest.json").read_bytes()).hexdigest(), result["manifest_sha256"])

    def test_missing_source_blocks_itself_and_descendants_without_fake_copy(self):
        (self.work / self.brief["assets"][0]["path"]).unlink()
        result = self.build()
        self.assertEqual("blocked", result["status"])
        self.assertEqual("missing_source", result["assets"][0]["status"])
        self.assertIsNone(result["assets"][0]["packet_path"])
        self.assertFalse((self.output / "sources/ebook.md").exists())
        self.assertTrue(all(item["status"] == "blocked" for item in result["assets"][1:]))
        self.assertTrue(all(item["status"] != "prepared_for_review" for item in result["formats"]))
        self.assertEqual(result, verify_production_plan(self.output))

    def test_changed_source_copies_actual_bytes_and_marks_all_dependents_stale(self):
        source = self.work / self.brief["assets"][0]["path"]
        changed = source.read_bytes() + b"\nA changed chapter paragraph.\n"
        source.write_bytes(changed)
        result = self.build()
        first = result["assets"][0]
        self.assertEqual("stale", first["source_status"])
        self.assertEqual("stale_source", first["status"])
        self.assertEqual(sha256(changed).hexdigest(), first["observed_sha256"])
        self.assertEqual(changed, (self.output / first["packet_path"]).read_bytes())
        self.assertTrue(all(item["status"] == "blocked" for item in result["assets"][1:]))
        self.assertIn("parent_observed_hash_mismatch:ebook", result["assets"][1]["blockers"])

    def test_parent_pin_must_match_declared_and_actual_hashes(self):
        self.brief["assets"][1]["parents"][0]["sha256"] = "a" * 64
        self.save()
        result = self.build()
        self.assertEqual("prepared_for_review", result["assets"][0]["status"])
        self.assertEqual("blocked", result["assets"][1]["status"])
        self.assertIn("parent_declared_hash_mismatch:ebook", result["assets"][1]["blockers"])
        self.assertEqual("blocked", result["assets"][3]["status"])

    def test_current_change_request_blocks_review_readiness_and_descendants(self):
        self.brief["reviews"] = [self.review(result="changes_requested"),
                                 self.review(result="pass", reviewer="Another asserted reviewer")]
        self.save()
        result = self.build()
        self.assertEqual("blocked", result["status"])
        self.assertTrue(all(item["status"] == "blocked" for item in result["assets"]))
        self.assertIn("recorded_changes_requested:Synthetic reviewer", result["assets"][0]["blockers"])
        self.assertFalse(result["execution"]["approval_granted"])

    def test_pass_is_untrusted_and_cannot_establish_release_or_rights(self):
        self.brief["reviews"] = [self.review()]
        self.save()
        result = self.build()
        self.assertEqual("prepared_for_review", result["status"])
        self.assertEqual("recorded_untrusted", result["assets"][0]["review_assertions"][0]["trust"])
        self.assertEqual("release_blocked", result["release_status"])
        self.assertFalse(result["execution"]["approval_granted"])
        self.assertEqual("unverified", result["evidence_scope"]["authorship"])

    def test_stale_review_assertion_is_flagged_and_does_not_clear_current_blocker(self):
        self.brief["reviews"] = [self.review(digest="a" * 64, result="pass"),
                                 self.review(result="changes_requested", reviewer="Current assertion")]
        self.save()
        result = self.build()
        first = result["assets"][0]
        self.assertEqual("blocked", first["status"])
        self.assertFalse(first["review_assertions"][0]["hash_matches_observed"])
        self.assertIn("stale_review_assertion:Synthetic reviewer", first["warnings"])

    def test_missing_kind_and_zero_assets_are_blocked_without_invented_lineage(self):
        self.brief["assets"] = []
        self.save()
        result = self.build()
        self.assertEqual("blocked", result["status"])
        self.assertFalse(result["contains_source_drafts"])
        self.assertEqual(9, result["file_count"])
        self.assertEqual([], result["dependency_order"])
        self.assertTrue(all(item["status"] == "missing_source" for item in result["formats"]))

    def test_unrelated_drafts_have_no_inferred_parent_and_order_is_topological(self):
        self.brief["assets"] = list(reversed(self.brief["assets"]))
        self.save()
        result = self.build()
        order = result["dependency_order"]
        self.assertLess(order.index("ebook"), order.index("narration"))
        self.assertLess(order.index("narration"), order.index("video-book"))
        self.assertLess(order.index("ebook"), order.index("video"))
        for asset in self.brief["assets"]:
            asset["parents"] = []
        self.save()
        result = self.build(self.root / "independent-packet")
        self.assertTrue(all(item["parents"] == [] for item in result["assets"]))

    def test_invalid_schema_extra_fields_and_empty_or_duplicate_selections_fail_before_write(self):
        original = deepcopy(self.brief)
        for field, value in (("schema", "unknown"), ("source_declaration", "owner_declared_local_drafts"),
                             ("approval", True), ("objective", " "), ("language", "../en"),
                             ("formats", ["Video"]), ("formats", ["Videos", "Videos"]),
                             ("purposes", []), ("project_id", "../../escape")):
            self.brief = {**deepcopy(original), field: value}
            self.save()
            with self.subTest(field=field, value=value), self.assertRaises(StudioProductionError):
                self.build()
            self.assertFalse(self.output.exists())

    def test_duplicate_unknown_self_and_cyclic_graphs_fail_before_write(self):
        original = deepcopy(self.brief)
        mutations = (
            lambda a: a[1].update(id="ebook"),
            lambda a: a[1].update(path=a[0]["path"]),
            lambda a: a[1].update(kind="ebook_manuscript"),
            lambda a: a[1]["parents"].append(dict(a[1]["parents"][0])),
            lambda a: a[0]["parents"].append({"asset_id": "ebook", "sha256": a[0]["sha256"]}),
            lambda a: a[0]["parents"].append({"asset_id": "unknown", "sha256": a[0]["sha256"]}),
            lambda a: a[0]["parents"].append({"asset_id": "video-book", "sha256": a[3]["sha256"]}),
        )
        for number, mutation in enumerate(mutations):
            self.brief = deepcopy(original)
            mutation(self.brief["assets"])
            self.save()
            with self.subTest(case=number), self.assertRaises(StudioProductionError):
                self.build()
            self.assertFalse(self.output.exists())

    def test_malformed_asset_and_review_fields_fail_closed(self):
        original = deepcopy(self.brief)
        mutations = (
            lambda b: b["assets"][0].update(sha256="ABC" * 21 + "D"),
            lambda b: b["assets"][0].update(kind="rendered_video"),
            lambda b: b["assets"][0].update(approved=True),
            lambda b: b["assets"][0].update(parents=None),
            lambda b: b.update(reviews=[{**self.review(), "verified": True}]),
            lambda b: b.update(reviews=[{**self.review(), "result": "approved"}]),
            lambda b: b.update(reviews=[{**self.review(), "asset_id": "unknown"}]),
            lambda b: b.update(reviews=[self.review(), self.review()]),
            lambda b: b.update(reviews=[self.review(reviewer=f"Reviewer-{i}") for i in range(MAX_REVIEWS + 1)]),
        )
        for number, mutation in enumerate(mutations):
            self.brief = deepcopy(original)
            mutation(self.brief)
            self.save()
            with self.subTest(case=number), self.assertRaises(StudioProductionError):
                self.build()

    def test_json_duplicates_constants_invalid_utf8_and_depth_are_rejected(self):
        for raw in (b"[]", b"{", b"\xff", b'{"schema":"a","schema":"b"}',
                    b'{"value":NaN}', b'{"value":Infinity}',
                    b'{"value":' + b"[" * 30 + b"0" + b"]" * 30 + b"}"):
            self.brief_path.write_bytes(raw)
            with self.subTest(raw=raw[:20]), self.assertRaises(StudioProductionError):
                self.build()
            self.assertFalse(self.output.exists())

    def test_escaped_credential_strings_and_overflow_numbers_fail_before_output(self):
        self.brief["project_id"] = "sk-" + "SYNTHETICKEY" * 4
        raw = json.dumps(self.brief).replace("sk-", "\\u0073\\u006b-").encode()
        self.brief_path.write_bytes(raw)
        with self.assertRaises(StudioProductionError):
            self.build()
        self.assertFalse(self.output.exists())
        self.brief["project_id"] = "synthetic-production"
        self.save()
        profile_path = self.project / PROFILE_PATH
        raw = profile_path.read_bytes()
        profile_path.write_bytes(b'{"overflow":1e999,' + raw.lstrip()[1:])
        with self.assertRaises(StudioProductionError):
            self.build()
        self.assertFalse(self.output.exists())

    def test_local_asset_paths_reject_escape_absolute_url_and_nontext_extensions(self):
        for path in ("../outside.md", "/tmp/asset.md", "assets/../asset.md", "assets//ebook.md",
                     "https://example.invalid/draft.md", "C:\\draft.md", "assets/ebook.pdf",
                     "assets/.hidden.md", "assets/./ebook.md", "assets/ebook.md/ignored"):
            self.brief["assets"][0]["path"] = path
            self.save()
            with self.subTest(path=path), self.assertRaises(StudioProductionError):
                self.build()
            self.assertFalse(self.output.exists())

    def test_symlinked_sources_directories_brief_config_and_output_are_refused(self):
        source = self.work / self.brief["assets"][0]["path"]
        real_source = self.root / "real.md"
        source.rename(real_source)
        source.symlink_to(real_source)
        with self.assertRaises(StudioProductionError):
            self.build()
        source.unlink()
        real_source.rename(source)
        assets_dir = self.work / "assets"
        moved_assets = self.root / "moved-assets"
        assets_dir.rename(moved_assets)
        assets_dir.symlink_to(moved_assets, target_is_directory=True)
        with self.assertRaises(StudioProductionError):
            self.build()
        assets_dir.unlink()
        moved_assets.rename(assets_dir)
        linked_brief = self.root / "linked-brief.json"
        linked_brief.symlink_to(self.brief_path)
        with self.assertRaises(StudioProductionError):
            build_production_plan(self.project, linked_brief, self.output)
        self.output.symlink_to(self.root / "missing-output", target_is_directory=True)
        with self.assertRaises(StudioProductionError):
            self.build()
        self.output.unlink()
        profile = self.project / PROFILE_PATH
        profile.unlink()
        profile.symlink_to(PROJECT / PROFILE_PATH)
        with self.assertRaises(StudioProductionError):
            self.build()

    def test_empty_binary_oversized_sensitive_sources_and_brief_fail_before_output(self):
        source = self.work / self.brief["assets"][0]["path"]
        original = source.read_bytes()
        for raw in (b"", b"   \n", b"binary\0data", b"\xff", b"x" * (MAX_ASSET_BYTES + 1),
                    b"sk-" + b"SYNTHETICKEY" * 4):
            source.write_bytes(raw)
            with self.subTest(raw=raw[:20]), self.assertRaises(StudioProductionError):
                self.build()
            self.assertFalse(self.output.exists())
        source.write_bytes(original)
        self.brief["objective"] = "sk-" + "SYNTHETICKEY" * 4
        self.save()
        with self.assertRaises(StudioProductionError):
            self.build()
        self.brief_path.write_bytes(b" " * (MAX_BRIEF_BYTES + 1))
        with self.assertRaises(StudioProductionError):
            self.build()

    def test_nonregular_source_is_rejected_without_opening_fifo(self):
        source = self.work / self.brief["assets"][0]["path"]
        source.unlink()
        source.mkdir()
        with self.assertRaises(StudioProductionError):
            self.build()
        source.rmdir()
        if hasattr(os, "mkfifo"):
            os.mkfifo(source)
            with self.assertRaises(StudioProductionError):
                self.build()
        self.assertFalse(self.output.exists())

    def test_packet_never_overwrites_existing_destination(self):
        original = self.build()
        manifest = (self.output / "manifest.json").read_bytes()
        with self.assertRaises(StudioProductionError):
            self.build()
        self.assertEqual(manifest, (self.output / "manifest.json").read_bytes())
        self.assertEqual(original, verify_production_plan(self.output))

    def test_verifier_reports_internal_consistency_not_later_worktree_freshness(self):
        result = self.build()
        (self.work / self.brief["assets"][0]["path"]).write_text("A later working edit.")
        self.assertEqual(result, verify_production_plan(self.output))
        self.assertEqual("not_rechecked_by_packet_verification", result["evidence_scope"]["external_source_freshness"])
        self.assertEqual("local_hash_consistency_not_signature", result["evidence_scope"]["manifest_trust"])

    def test_verifier_rejects_missing_extra_renamed_and_symlinked_packet_entries(self):
        self.build()
        source = self.output / "sources/ebook.md"
        source.rename(self.output / "sources/renamed.md")
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)
        (self.output / "sources/renamed.md").rename(source)
        extra = self.output / "sources/extra.md"
        extra.write_text("Unexpected input.")
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)
        extra.unlink()
        source.unlink()
        source.symlink_to(self.work / self.brief["assets"][0]["path"])
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)
        source.unlink()
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)

    def test_rehashed_source_tampering_does_not_keep_prepared_for_review(self):
        self.build()
        raw = (self.output / "sources/ebook.md").read_bytes() + b"\nAn untracked edit.\n"
        self.rehash("sources/ebook.md", raw)
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)

    def test_rehashed_plan_and_handoff_cannot_assert_false_readiness(self):
        self.build()
        plan_path = self.output / "production-plan.json"
        plan_raw = plan_path.read_bytes()
        plan = json.loads(plan_raw)
        for change in ({"release_status": "published"}, {"status": "approved"},
                       {"execution": {**EXECUTION, "provider_calls": 1}}):
            self.rehash("production-plan.json", (json.dumps({**plan, **change}, sort_keys=True, indent=2) + "\n").encode())
            with self.subTest(change=change), self.assertRaises(StudioProductionError):
                verify_production_plan(self.output)
        self.rehash("production-plan.json", plan_raw)
        handoff = "ai-workspaces/claude.md"
        self.rehash(handoff, (self.output / handoff).read_bytes() + b"\nApproved to publish.\n")
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)

    def test_manifest_unknown_fields_paths_hashes_and_boolean_number_aliases_fail(self):
        self.build()
        original = self.manifest()
        mutations = (
            lambda m: m.update(approved=True),
            lambda m: m.update(release_status="approved"),
            lambda m: m["execution"].update(provider_calls=False),
            lambda m: m["execution"].update(published=0),
            lambda m: m["files"][0].update(path="../../escape.md"),
            lambda m: m["files"][0].update(bytes=True),
            lambda m: m["files"][0].update(sha256="0" * 64),
            lambda m: m["files"].append(dict(m["files"][0])),
            lambda m: m.update(created_at="2026-10-20T00:00:00"),
        )
        for number, mutate in enumerate(mutations):
            value = deepcopy(original)
            mutate(value)
            self.write_manifest(value)
            with self.subTest(case=number), self.assertRaises(StudioProductionError):
                verify_production_plan(self.output)

    def test_unknown_profile_identity_revision_and_studio_declaration_fail_closed(self):
        original = (self.project / PROFILE_PATH).read_bytes()
        for field, value in (("id", "unknown"), ("revision", "future"), ("guidance", [])):
            profile = json.loads(original)
            profile[field] = value
            (self.project / PROFILE_PATH).write_text(json.dumps(profile))
            with self.subTest(field=field), self.assertRaises(StudioProductionError):
                self.build()
            self.assertFalse(self.output.exists())
        (self.project / PROFILE_PATH).write_bytes(original)
        config = json.loads((self.project / CONFIG_PATH).read_bytes())
        config["connection_status"] = "connected"
        (self.project / CONFIG_PATH).write_text(json.dumps(config))
        with self.assertRaises(StudioProductionError):
            self.build()

    def test_rehashed_profile_or_config_identity_tampering_is_rejected(self):
        self.build()
        profile = json.loads((self.output / PROFILE_PATH).read_bytes())
        profile["revision"] = "other"
        self.rehash(PROFILE_PATH.as_posix(), json.dumps(profile).encode())
        with self.assertRaises(StudioProductionError):
            verify_production_plan(self.output)


if __name__ == "__main__":
    unittest.main()
