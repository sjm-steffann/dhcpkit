"""
Tests for a relay message handler
"""
import unittest

from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.server.handlers import RelayHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class TestRelayHandler(RelayHandler):
    """
    A relay handler that doesn't do anything
    """

    def handle_relay(self, bundle: TransactionBundle,
                     relay_message_in: RelayForwardMessage, relay_message_out: RelayReplyMessage):
        """
        Handler implementation that doesn't do anything
        """


class RelayHandlerTestCase(unittest.TestCase):
    def test_str(self):
        handler = TestRelayHandler()
        self.assertEqual(str(handler), 'TestRelayHandler')


if __name__ == '__main__':
    unittest.main()
