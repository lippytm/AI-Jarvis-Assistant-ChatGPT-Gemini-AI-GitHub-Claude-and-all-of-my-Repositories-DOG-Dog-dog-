import json
import tempfile
import unittest
from pathlib import Path
from jarvis.brain_fleet import ROOT, BrainGateway, hostinger_viability, load_registry

def synthetic_roster():
    return {"platform": [{"id": f"B{i:02}", "name": "Synthetic"} for i in range(1, 23)],
            "personal": [{"id": f"P{i:02}", "name": "Synthetic"} for i in range(1, 8)]}

class BrainFleetTests(unittest.TestCase):
    def test_29_distinct_brains_and_builder_viability(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "private.json"
            path.write_text(json.dumps(synthetic_roster()))
            roster = load_registry(path)
        capabilities = json.loads((ROOT / "config/hostinger-builder-capabilities.json").read_text())
        report = hostinger_viability(roster, capabilities)
        self.assertEqual(report["brains"], 29)
        self.assertEqual(report["possible_pairs"], 145)
        self.assertEqual(report["live_platform_pairs"], 0)
        self.assertEqual(report["personal_pairs"], 0)

    def test_per_brain_memory_and_private_vault_isolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            gateway = BrainGateway(Path(temporary), synthetic_roster())
            platform = gateway.mission("B03", {"task": "mock"}, destination="B15")
            personal = gateway.mission("P02", {"task": "mock"}, destination="P07")
            self.assertTrue(platform["chain_valid"] and personal["chain_valid"])
            self.assertEqual(platform["receipts"][-1]["status"], "pending_owner_approval")
            self.assertTrue((Path(temporary) / "B03/mempalace.sqlite").is_file())
            self.assertTrue((Path(temporary) / "P02/mempalace.sqlite").is_file())
            with self.assertRaises(PermissionError):
                gateway.mission("P02", {"task": "private"}, destination="B03")

    def test_unauthorized_brain_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                BrainGateway(Path(temporary), synthetic_roster()).mission("P08", {})

if __name__ == "__main__":
    unittest.main()
