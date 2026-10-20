from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jarvis.patrol import Patrol, PatrolPolicy


class PatrolTests(unittest.TestCase):
    def test_patrol_is_read_only_and_records_findings(self) -> None:
        stale = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        inventory = lambda owner=None: [
            {"full_name": "lippytm/old", "private": False,
             "default_branch": "main", "updated_at": stale},
            {"full_name": "lippytm/private", "private": True,
             "default_branch": None, "updated_at": datetime.now(timezone.utc).isoformat()},
        ]
        with tempfile.TemporaryDirectory() as directory:
            report = Patrol(
                PatrolPolicy(max_repositories=10, stale_days=120),
                inventory=inventory,
                output_dir=Path(directory),
            ).run("lippytm")
            self.assertEqual("read_only", report["mode"])
            self.assertEqual(2, report["repositories_scanned"])
            codes = {item["code"] for item in report["findings"]}
            self.assertEqual(
                {"stale-repository", "missing-default-branch", "private-data-boundary"},
                codes,
            )
            self.assertTrue(all(item["requires_approval"] for item in report["findings"]))
            stored = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))
            self.assertNotIn("report_path", stored)

    def test_repository_limit_is_a_circuit_breaker(self) -> None:
        inventory = lambda owner=None: [
            {"full_name": f"lippytm/repo-{number}"} for number in range(3)
        ]
        with tempfile.TemporaryDirectory() as directory:
            patrol = Patrol(
                PatrolPolicy(max_repositories=2),
                inventory=inventory,
                output_dir=Path(directory),
            )
            with self.assertRaisesRegex(RuntimeError, "Circuit breaker"):
                patrol.run("lippytm")

    def test_invalid_timestamp_does_not_crash_patrol(self) -> None:
        inventory = lambda owner=None: [{
            "full_name": "lippytm/example", "private": False,
            "default_branch": "main", "updated_at": "not-a-date",
        }]
        with tempfile.TemporaryDirectory() as directory:
            report = Patrol(
                inventory=inventory, output_dir=Path(directory)
            ).run("lippytm")
            self.assertEqual([], report["findings"])


if __name__ == "__main__":
    unittest.main()
