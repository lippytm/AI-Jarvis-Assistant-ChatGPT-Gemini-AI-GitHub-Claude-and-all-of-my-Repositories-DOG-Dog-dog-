import unittest

from jarvis.connectors import Connector, ConnectorAction, Risk


class ConnectorPolicyTests(unittest.TestCase):
    def test_write_requires_approval(self):
        with self.assertRaises(PermissionError):
            Connector.require_approval(ConnectorAction("publish", Risk.WRITE, {}), None)

    def test_destructive_is_disabled_even_with_approval(self):
        with self.assertRaises(PermissionError):
            Connector.require_approval(ConnectorAction("delete", Risk.DESTRUCTIVE, {}), "yes")

    def test_read_does_not_require_approval(self):
        Connector.require_approval(ConnectorAction("inspect", Risk.READ, {}), None)
