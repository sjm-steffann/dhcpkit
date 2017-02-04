"""
Test transaction bundle
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption
from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage, ReplyMessage, SolicitMessage, UnknownMessage
from dhcpkit.ipv6.options import IANAOption, IATAOption, RelayMessageOption
from dhcpkit.ipv6.server.handlers.interface_id import InterfaceIdOptionHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.tests.ipv6.messages.test_advertise_message import advertise_message
from dhcpkit.tests.ipv6.messages.test_relay_forward_message import relayed_solicit_message
from dhcpkit.tests.ipv6.messages.test_relay_reply_message import relayed_advertise_message
from dhcpkit.tests.ipv6.messages.test_solicit_message import solicit_message


class TransactionBundleTestCase(unittest.TestCase):
    def setUp(self):
        self.bundle = TransactionBundle(relayed_solicit_message, received_over_multicast=False)
        self.shallow_bundle = TransactionBundle(solicit_message, received_over_multicast=True)
        self.deep_bundle = TransactionBundle(RelayForwardMessage(
            hop_count=0,
            link_address=IPv6Address('2001:db8:ffff:2::1'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=relayed_solicit_message),
            ]
        ), received_over_multicast=False, marks=['some', 'marks'])
        self.ia_bundle = TransactionBundle(SolicitMessage(options=[
            IANAOption(b'0001'),
            IANAOption(b'0002'),
            IATAOption(b'0003'),
            IATAOption(b'0004'),
            IAPDOption(b'0005'),
            IAPDOption(b'0006'),
        ]), received_over_multicast=False)
        self.option_handlers = [
            InterfaceIdOptionHandler(),
        ]

    def test_str(self):
        bundle_str = str(self.bundle)
        self.assertEqual(bundle_str, "SolicitMessage from 000300013431c43cb2f1 at fe80::3631:c4ff:fe3c:b2f1 "
                                     "via LDRA -> 2001:db8:ffff:1::1")
        bundle_str = str(self.shallow_bundle)
        self.assertEqual(bundle_str, "SolicitMessage from 000300013431c43cb2f1")
        bundle_str = str(self.deep_bundle)
        self.assertRegex(bundle_str, "^SolicitMessage from 000300013431c43cb2f1 at fe80::3631:c4ff:fe3c:b2f1 "
                                     "via LDRA -> 2001:db8:ffff:1::1 -> 2001:db8:ffff:2::1 with marks .*$")
        bundle_str = str(self.ia_bundle)
        self.assertEqual(bundle_str, "SolicitMessage from unknown")

    def test_shallow_bundle(self):
        self.shallow_bundle.response = advertise_message
        self.shallow_bundle.create_outgoing_relay_messages()
        self.assertEqual(self.shallow_bundle.outgoing_message, advertise_message)
        self.assertEqual(self.shallow_bundle.outgoing_relay_messages, [])

    def test_request(self):
        self.assertEqual(self.bundle.request, solicit_message)

    def test_incoming_relay_messages(self):
        self.assertEqual(len(self.bundle.incoming_relay_messages), 2)
        self.assertEqual(self.bundle.incoming_relay_messages[0].hop_count, 0)
        self.assertEqual(self.bundle.incoming_relay_messages[1].hop_count, 1)

    def test_bad_response(self):
        self.bundle.response = SolicitMessage()
        with self.assertLogs() as cm:
            self.assertIsNone(self.bundle.outgoing_message)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], 'server should not send')

    def test_outgoing_message(self):
        # Set the response and let the option handlers do their work
        # Which in this case is copy the InterfaceId to the response
        self.bundle.response = advertise_message
        self.bundle.create_outgoing_relay_messages()
        for option_handler in self.option_handlers:
            option_handler.handle(self.bundle)

        self.assertEqual(self.bundle.outgoing_message, relayed_advertise_message)

    def test_direct_outgoing_message(self):
        self.ia_bundle.response = advertise_message
        self.assertEqual(self.ia_bundle.outgoing_message, advertise_message)

    def test_auto_create_outgoing_relay_messages(self):
        self.bundle.response = advertise_message
        self.assertIsInstance(self.bundle.outgoing_message, RelayReplyMessage)

    def test_no_outgoing_message(self):
        self.assertIsNone(self.bundle.outgoing_message)

    def test_get_unhandled_options(self):
        unanswered_options = self.ia_bundle.get_unhandled_options((IANAOption, IATAOption))
        self.assertEqual(len(unanswered_options), 4)
        self.assertIn(IANAOption(b'0001'), unanswered_options)
        self.assertIn(IANAOption(b'0002'), unanswered_options)
        self.assertIn(IATAOption(b'0003'), unanswered_options)
        self.assertIn(IATAOption(b'0004'), unanswered_options)

    def test_marks(self):
        self.assertEqual(self.bundle.marks, set())
        self.bundle.marks.add('one')
        self.bundle.marks.add('two')
        self.assertEqual(self.bundle.marks, {'one', 'two'})
        self.bundle.marks.add('two')
        self.assertEqual(self.bundle.marks, {'one', 'two'})

    def test_mark_handled(self):
        self.ia_bundle.mark_handled(IANAOption(b'0001'))
        self.ia_bundle.mark_handled(IATAOption(b'0004'))
        unanswered_options = self.ia_bundle.get_unhandled_options((IANAOption, IATAOption))
        self.assertEqual(len(unanswered_options), 2)
        self.assertIn(IANAOption(b'0002'), unanswered_options)
        self.assertIn(IATAOption(b'0003'), unanswered_options)

    def test_unanswered_iana_options(self):
        unanswered_options = self.ia_bundle.get_unhandled_options(IANAOption)
        self.assertEqual(len(unanswered_options), 2)
        self.assertIn(IANAOption(b'0001'), unanswered_options)
        self.assertIn(IANAOption(b'0002'), unanswered_options)

    def test_unanswered_iata_options(self):
        unanswered_options = self.ia_bundle.get_unhandled_options(IATAOption)
        self.assertEqual(len(unanswered_options), 2)
        self.assertIn(IATAOption(b'0003'), unanswered_options)
        self.assertIn(IATAOption(b'0004'), unanswered_options)

    def test_unanswered_iapd_options(self):
        unanswered_options = self.ia_bundle.get_unhandled_options(IAPDOption)
        self.assertEqual(len(unanswered_options), 2)
        self.assertIn(IAPDOption(b'0005'), unanswered_options)
        self.assertIn(IAPDOption(b'0006'), unanswered_options)

    def test_unknown_message(self):
        with self.assertLogs() as cm:
            TransactionBundle(UnknownMessage(1608, b'Unknown'), False)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], 'unrecognised message')

    def test_wrong_way(self):
        with self.assertLogs() as cm:
            TransactionBundle(ReplyMessage(), False)
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], 'server should not receive')

    def test_link_address(self):
        self.assertEqual(self.bundle.link_address, IPv6Address('2001:db8:ffff:1::1'))
        self.assertEqual(self.ia_bundle.link_address, IPv6Address('::'))


if __name__ == '__main__':
    unittest.main()
