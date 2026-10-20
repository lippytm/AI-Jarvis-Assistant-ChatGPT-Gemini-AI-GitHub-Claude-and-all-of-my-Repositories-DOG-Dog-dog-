import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jarvis.hermes import MemPalace, Stage, run_swarm
from jarvis.hostinger import list_websites


class HermesTests(unittest.TestCase):
    def test_bounded_handoff_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = MemPalace(Path(root) / "memory.sqlite")
            stages = [Stage("research", "gemini-ai"), Stage("review", "claude-coworker"),
                      Stage("release", "hostinger", "publish")]
            calls = []
            def fake(name):
                def handle(value):
                    calls.append(name)
                    return {"from": name, "previous": value}
                return handle
            report = run_swarm(stages, {"goal": "test"},
                               {name: fake(name) for name in ("gemini-ai", "claude-coworker", "hostinger")}, ledger)
            self.assertEqual(calls, ["gemini-ai", "claude-coworker"])
            self.assertEqual(report["receipts"][-1]["status"], "pending_owner_approval")
            self.assertTrue(report["chain_valid"])
            with sqlite3.connect(ledger.path) as db:
                db.execute("UPDATE events SET evidence_json=? WHERE run_id=? AND sequence=0",
                           ('{"tampered":true}', report["run_id"]))
            self.assertFalse(ledger.verify(report["run_id"]))

    def test_unverified_station_and_recursive_fleet_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = MemPalace(Path(root) / "m.sqlite")
            with self.assertRaises(ValueError):
                run_swarm([Stage("x", "unknown")], {}, {}, ledger)
            with self.assertRaises(ValueError):
                run_swarm([Stage(str(i), "github") for i in range(9)], {}, {}, ledger)

    def test_hostinger_inventory_requires_opt_in_and_redacts_errors(self):
        with self.assertRaises(PermissionError):
            list_websites(token="test-token")
        with self.assertRaises(ValueError):
            list_websites(allow_external=True, token="")

        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        def opener(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            return Response(json.dumps({"data": []}).encode())
        self.assertEqual(list_websites(allow_external=True, token="test-token", opener=opener), {"data": []})


if __name__ == "__main__":
    unittest.main()
