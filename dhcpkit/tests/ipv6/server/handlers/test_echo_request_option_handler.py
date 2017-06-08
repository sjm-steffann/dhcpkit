"""
Tests for a relay message handler
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.duids import LinkLayerDUID, LinkLayerTimeDUID
from dhcpkit.ipv6.extensions.relay_echo_request import EchoRequestOption
from dhcpkit.ipv6.extensions.remote_id import OPTION_REMOTE_ID, RemoteIdOption
from dhcpkit.ipv6.extensions.subscriber_id import OPTION_SUBSCRIBER_ID
from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage, SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, ElapsedTimeOption, IANAOption, InterfaceIdOption, \
    OPTION_INTERFACE_ID, RelayMessageOption, UnknownOption
from dhcpkit.ipv6.server.message_handler import MessageHandler
from dhcpkit.ipv6.server.statistics import StatisticsSet
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class RelayHandlerTestCase(unittest.TestCase):
    def setUp(self):
        # This is the DUID that is used in the message fixtures
        self.duid = LinkLayerTimeDUID(hardware_type=1, time=488458703, link_layer_address=bytes.fromhex('00137265ca42'))

        # Create a message handler
        self.message_handler = MessageHandler(server_id=self.duid)

    def test_empty_echo_request(self):
        relayed_solicit_message = RelayForwardMessage(
            hop_count=1,
            link_address=IPv6Address('2001:db8:ffff:1::1'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=SolicitMessage(
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        ElapsedTimeOption(elapsed_time=0),
                        ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                          link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                        IANAOption(iaid=bytes.fromhex('c43cb2f1')),
                    ],
                )),
                EchoRequestOption(requested_options=[]),
                UnknownOption(option_type=65535),
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RemoteIdOption(enterprise_number=9,
                               remote_id=bytes.fromhex('020023000001000a0003000100211c7d486e')),
            ]
        )

        bundle = TransactionBundle(incoming_message=relayed_solicit_message, received_over_multicast=True)
        self.message_handler.handle(bundle, StatisticsSet())

        self.assertIsInstance(bundle.outgoing_message, RelayReplyMessage)
        self.assertEqual(len(bundle.outgoing_message.options), 2)
        self.assertIsInstance(bundle.outgoing_message.options[0], InterfaceIdOption)
        self.assertIsInstance(bundle.outgoing_message.options[1], RelayMessageOption)

    def test_unnecessary_echo_request(self):
        relayed_solicit_message = RelayForwardMessage(
            hop_count=1,
            link_address=IPv6Address('2001:db8:ffff:1::1'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=SolicitMessage(
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        ElapsedTimeOption(elapsed_time=0),
                        ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                          link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                        IANAOption(iaid=bytes.fromhex('c43cb2f1')),
                    ],
                )),
                EchoRequestOption(requested_options=[OPTION_INTERFACE_ID]),
                UnknownOption(option_type=65535),
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RemoteIdOption(enterprise_number=9,
                               remote_id=bytes.fromhex('020023000001000a0003000100211c7d486e')),
            ]
        )

        bundle = TransactionBundle(incoming_message=relayed_solicit_message, received_over_multicast=True)
        self.message_handler.handle(bundle, StatisticsSet())

        self.assertIsInstance(bundle.outgoing_message, RelayReplyMessage)
        self.assertEqual(len(bundle.outgoing_message.options), 2)
        self.assertIsInstance(bundle.outgoing_message.options[0], InterfaceIdOption)
        self.assertIsInstance(bundle.outgoing_message.options[1], RelayMessageOption)

    def test_absent_option_echo_request(self):
        relayed_solicit_message = RelayForwardMessage(
            hop_count=1,
            link_address=IPv6Address('2001:db8:ffff:1::1'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=SolicitMessage(
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        ElapsedTimeOption(elapsed_time=0),
                        ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                          link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                        IANAOption(iaid=bytes.fromhex('c43cb2f1')),
                    ],
                )),
                EchoRequestOption(requested_options=[OPTION_SUBSCRIBER_ID]),
                UnknownOption(option_type=65535),
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RemoteIdOption(enterprise_number=9,
                               remote_id=bytes.fromhex('020023000001000a0003000100211c7d486e')),
            ]
        )

        bundle = TransactionBundle(incoming_message=relayed_solicit_message, received_over_multicast=True)
        self.message_handler.handle(bundle, StatisticsSet())

        self.assertIsInstance(bundle.outgoing_message, RelayReplyMessage)
        self.assertEqual(len(bundle.outgoing_message.options), 2)
        self.assertIsInstance(bundle.outgoing_message.options[0], InterfaceIdOption)
        self.assertIsInstance(bundle.outgoing_message.options[1], RelayMessageOption)

    def test_remote_id_echo_request(self):
        relayed_solicit_message = RelayForwardMessage(
            hop_count=1,
            link_address=IPv6Address('2001:db8:ffff:1::1'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=SolicitMessage(
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        ElapsedTimeOption(elapsed_time=0),
                        ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                          link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                        IANAOption(iaid=bytes.fromhex('c43cb2f1')),
                    ],
                )),
                EchoRequestOption(requested_options=[OPTION_REMOTE_ID]),
                UnknownOption(option_type=65535),
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RemoteIdOption(enterprise_number=9,
                               remote_id=bytes.fromhex('020023000001000a0003000100211c7d486e')),
            ]
        )

        bundle = TransactionBundle(incoming_message=relayed_solicit_message, received_over_multicast=True)
        self.message_handler.handle(bundle, StatisticsSet())

        self.assertIsInstance(bundle.outgoing_message, RelayReplyMessage)
        self.assertEqual(len(bundle.outgoing_message.options), 3)
        self.assertIsInstance(bundle.outgoing_message.options[0], InterfaceIdOption)
        self.assertIsInstance(bundle.outgoing_message.options[1], RelayMessageOption)
        self.assertIsInstance(bundle.outgoing_message.options[2], RemoteIdOption)


if __name__ == '__main__':
    unittest.main()
