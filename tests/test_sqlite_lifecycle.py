import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.hermes import MemPalace, Stage, run_swarm
from jarvis.ledger import Ledger
from jarvis.models import ProviderResponse, Task


_REAL_CONNECT = sqlite3.connect


class InjectedDatabaseFailure(RuntimeError):
    """An offline failure after a statement has reached the real database."""


class TrackingConnection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        cursor = super().execute(sql, parameters)
        self.tracker.after_statement(self, sql)
        return cursor

    def executescript(self, sql_script):
        cursor = super().executescript(sql_script)
        self.tracker.after_statement(self, sql_script)
        return cursor


class ConnectionTracker:
    def __init__(self):
        self.connections = []
        self.fail_after_sql = None
        self.failed_in_transaction = False

    def connect(self, *args, **kwargs):
        db = _REAL_CONNECT(*args, **kwargs, factory=TrackingConnection)
        db.tracker = self
        self.connections.append(db)
        return db

    def after_statement(self, db, sql):
        if self.fail_after_sql and sql.lstrip().startswith(self.fail_after_sql):
            self.fail_after_sql = None
            self.failed_in_transaction = db.in_transaction
            raise InjectedDatabaseFailure("Injected local database failure")

    def close(self):
        for db in self.connections:
            db.close()


class SQLiteLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tracker = ConnectionTracker()
        self.addCleanup(self.tracker.close)
        # Both modules use the same sqlite3 module; keep the real factory above.
        patcher = patch("sqlite3.connect", side_effect=self.tracker.connect)
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_connections_closed(self):
        self.assertTrue(self.tracker.connections)
        for db in self.tracker.connections:
            with self.assertRaisesRegex(sqlite3.ProgrammingError, "closed"):
                db.execute("SELECT 1")

    def test_ledger_successful_operations_commit_and_close(self):
        ledger = Ledger(self.root / "tasks.sqlite3")
        self.assert_connections_closed()
        task = Task(prompt="Local test task", provider="mock")
        ledger.create_task(task)
        self.assert_connections_closed()
        response = ProviderResponse(task.id, "mock", "mock-local", "Local draft")
        ledger.complete_task(response)
        self.assert_connections_closed()
        record = ledger.get(task.id)
        self.assert_connections_closed()
        self.assertEqual(record["task"]["status"], "completed")
        self.assertEqual(record["response"]["content"], response.content)
        self.assertEqual(record["response"]["content_sha256"], response.content_sha256)
        self.assertEqual([event["event_type"] for event in record["events"]],
                         ["task.created", "task.completed"])
        self.assertEqual(ledger.history()[0]["id"], task.id)
        self.assert_connections_closed()
        self.assertIsNone(ledger.get("missing-task"))
        self.assert_connections_closed()
        failed = Task(prompt="Local failed task", provider="mock")
        ledger.create_task(failed)
        ledger.fail_task(failed.id, ValueError("Local failure"))
        self.assert_connections_closed()
        record = ledger.get(failed.id)
        self.assert_connections_closed()
        self.assertEqual(record["task"]["status"], "failed")
        self.assertEqual(record["events"][-1]["event_type"], "task.failed")

    def test_ledger_partial_writes_roll_back_without_damaging_prior_events(self):
        ledger = Ledger(self.root / "tasks.sqlite3")
        task = Task(prompt="Local test task", provider="mock")
        ledger.create_task(task)
        original = ledger.get(task.id)
        response = ProviderResponse(task.id, "mock", "mock-local", "Local draft")
        operations = {
            "create": lambda: ledger.create_task(Task(prompt="Uncommitted", provider="mock")),
            "complete": lambda: ledger.complete_task(response),
            "fail": lambda: ledger.fail_task(task.id, ValueError("Local failure")),
        }
        for name, operation in operations.items():
            with self.subTest(operation=name):
                # Fail after the task/response write AND its event insert execute.
                self.tracker.fail_after_sql = "INSERT INTO events"
                with self.assertRaises(InjectedDatabaseFailure):
                    operation()
                self.assertTrue(self.tracker.failed_in_transaction)
                self.assert_connections_closed()
                self.assertEqual(ledger.get(task.id), original)
                self.assertEqual([row["id"] for row in ledger.history()], [task.id])
                self.assert_connections_closed()

    def test_initialization_failure_closes_each_database_connection(self):
        for name, store in (("ledger", Ledger), ("mempalace", MemPalace)):
            with self.subTest(store=name):
                self.tracker.fail_after_sql = "CREATE TABLE"
                with self.assertRaises(InjectedDatabaseFailure):
                    store(self.root / f"{name}.sqlite3")
                self.assert_connections_closed()

    def test_read_failure_closes_connections_and_preserves_stored_data(self):
        ledger = Ledger(self.root / "tasks.sqlite3")
        task = Task(prompt="Local test task", provider="mock")
        ledger.create_task(task)
        original_task = ledger.get(task.id)
        memory = MemPalace(self.root / "memory.sqlite3")
        head = memory.append("local-run", "draft", {"status": "completed"})
        original_events = memory.history("local-run", expected_head=head)
        reads = {
            "get": lambda: ledger.get(task.id),
            "history": ledger.history,
            "memory_history": lambda: memory.history("local-run", expected_head=head),
        }
        for name, read in reads.items():
            with self.subTest(operation=name):
                self.tracker.fail_after_sql = "SELECT"
                with self.assertRaises(InjectedDatabaseFailure):
                    read()
                self.assert_connections_closed()
        self.assertEqual(ledger.get(task.id), original_task)
        self.assertEqual(memory.history("local-run", expected_head=head), original_events)
        self.assert_connections_closed()

    def test_mempalace_commits_receipts_and_closes_every_connection(self):
        memory = MemPalace(self.root / "memory.sqlite3")
        self.assert_connections_closed()
        report = run_swarm(
            [Stage("draft", "gemini-ai"), Stage("release", "hostinger", "publish")],
            {"goal": "Local lifecycle test"},
            {"gemini-ai": lambda value: {"draft": value["goal"]}},
            memory,
        )
        self.assert_connections_closed()
        self.assertTrue(report["chain_valid"])
        self.assertEqual([receipt["status"] for receipt in report["receipts"]],
                         ["completed", "pending_owner_approval"])
        head = report["receipts"][-1]["entry_hash"]
        events = memory.history(report["run_id"], expected_head=head)
        self.assert_connections_closed()
        self.assertEqual([event["entry_hash"] for event in events],
                         [receipt["entry_hash"] for receipt in report["receipts"]])
        self.assertEqual(events[-1]["evidence"]["input_sha256"], report["output_sha256"])
        with self.assertRaisesRegex(ValueError, "No MemPalace evidence"):
            memory.history("missing-run")
        self.assert_connections_closed()

    def test_mempalace_partial_append_rolls_back_and_preserves_receipt_chain(self):
        memory = MemPalace(self.root / "memory.sqlite3")
        head = memory.append("local-run", "first", {"status": "completed"})
        original = memory.history("local-run", expected_head=head)
        self.tracker.fail_after_sql = "INSERT INTO events"
        with self.assertRaises(InjectedDatabaseFailure):
            memory.append("local-run", "uncommitted", {"status": "completed"})
        self.assertTrue(self.tracker.failed_in_transaction)
        self.assert_connections_closed()
        self.assertEqual(memory.history("local-run", expected_head=head), original)
        self.assertTrue(memory.verify("local-run"))
        self.assert_connections_closed()
        next_head = memory.append("local-run", "second", {"status": "completed"})
        self.assert_connections_closed()
        events = memory.history("local-run", expected_head=next_head)
        self.assert_connections_closed()
        self.assertEqual([event["stage"] for event in events], ["first", "second"])
        self.assertEqual(events[1]["sequence"], 1)
        self.assertEqual(events[1]["previous_hash"], head)


if __name__ == "__main__":
    unittest.main()
