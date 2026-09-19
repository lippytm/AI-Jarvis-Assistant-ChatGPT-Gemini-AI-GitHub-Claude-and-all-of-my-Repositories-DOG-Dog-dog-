import tempfile
import unittest
from pathlib import Path

from jarvis.config import Settings
from jarvis.control_tower import ControlTower


class ControlTowerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tower = ControlTower(Settings("mock", Path(self.temp.name) / "jarvis.sqlite3", 5))

    def tearDown(self):
        self.temp.cleanup()

    def test_mock_round_trip_is_recorded(self):
        response = self.tower.run("Build a plan")
        self.assertIn("Build a plan", response.content)
        record = self.tower.ledger.get(response.task_id)
        self.assertEqual(record["task"]["status"], "completed")
        self.assertEqual(record["response"]["content_sha256"], response.content_sha256)
        self.assertEqual([x["event_type"] for x in record["events"]],
                         ["task.created", "task.completed"])

    def test_health_does_not_expose_secret_values(self):
        health = self.tower.health()
        self.assertNotIn("API_KEY", str(health))
        self.assertTrue(health["providers"]["mock"]["configured"])

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesRegex(Exception, "Unknown provider"):
            self.tower.run("test", "unknown")


if __name__ == "__main__":
    unittest.main()
