from ipaddress import IPv6Address
import unittest

from dhcp.ipv6.options import UnknownOption
from dhcp.ipv6.messages import Message
from dhcp.ipv6.rfc3315.messages import MSG_SOLICIT, MSG_ADVERTISE, MSG_REQUEST, MSG_REPLY, MSG_RELAY_FORW, \
    MSG_RELAY_REPL, ClientServerMessage, RelayServerMessage
from dhcp.ipv6.rfc3315.options import ElapsedTimeOption, ClientIdentifierOption, IANAOption, OptionRequestOption, \
    ServerIdentifierOption, RelayMessageOption, RapidCommitOption, VendorClassOption, InterfaceIdOption, \
    ReconfigureAcceptOption
from tests import dhcpv6_packets


class Solicit(unittest.TestCase):
    def setUp(self):
        self.packet = dhcpv6_packets.solicit_packet
        self.length, self.message = Message.parse(self.packet)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet))

    def test_class(self):
        self.assertIsInstance(self.message, ClientServerMessage)

    def test_type(self):
        self.assertEqual(self.message.message_type, MSG_SOLICIT)

    def test_transaction_id(self):
        self.assertEqual(self.message.transaction_id, bytes.fromhex('f350d6'))

    def test_options(self):
        self.assertIsInstance(self.message.options[0], ElapsedTimeOption)
        self.assertIsInstance(self.message.options[1], ClientIdentifierOption)
        self.assertIsInstance(self.message.options[2], RapidCommitOption)
        self.assertIsInstance(self.message.options[3], IANAOption)
        self.assertIsInstance(self.message.options[4], UnknownOption)  # TODO
        self.assertIsInstance(self.message.options[5], ReconfigureAcceptOption)
        self.assertIsInstance(self.message.options[6], OptionRequestOption)
        self.assertIsInstance(self.message.options[7], VendorClassOption)

    def test_save(self):
        self.assertEqual(self.packet, self.message.save())


class Advertise(unittest.TestCase):
    def setUp(self):
        self.packet = dhcpv6_packets.advertise_packet
        self.length, self.message = Message.parse(self.packet)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet))

    def test_class(self):
        self.assertIsInstance(self.message, ClientServerMessage)

    def test_type(self):
        self.assertEqual(self.message.message_type, MSG_ADVERTISE)

    def test_transaction_id(self):
        self.assertEqual(self.message.transaction_id, bytes.fromhex('f350d6'))

    def test_options(self):
        self.assertIsInstance(self.message.options[0], IANAOption)
        self.assertIsInstance(self.message.options[1], UnknownOption)  # TODO
        self.assertIsInstance(self.message.options[2], ClientIdentifierOption)
        self.assertIsInstance(self.message.options[3], ServerIdentifierOption)
        self.assertIsInstance(self.message.options[4], ReconfigureAcceptOption)
        self.assertIsInstance(self.message.options[5], UnknownOption)  # TODO

    def test_save(self):
        self.assertEqual(self.packet, self.message.save())


class Request(unittest.TestCase):
    def setUp(self):
        self.packet = dhcpv6_packets.request_packet
        self.length, self.message = Message.parse(self.packet)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet))

    def test_class(self):
        self.assertIsInstance(self.message, ClientServerMessage)

    def test_type(self):
        self.assertEqual(self.message.message_type, MSG_REQUEST)

    def test_transaction_id(self):
        self.assertEqual(self.message.transaction_id, bytes.fromhex('f350d6'))

    def test_options(self):
        self.assertIsInstance(self.message.options[0], ElapsedTimeOption)
        self.assertIsInstance(self.message.options[1], ClientIdentifierOption)
        self.assertIsInstance(self.message.options[2], ServerIdentifierOption)
        self.assertIsInstance(self.message.options[3], IANAOption)
        self.assertIsInstance(self.message.options[4], UnknownOption)  # TODO
        self.assertIsInstance(self.message.options[5], ReconfigureAcceptOption)
        self.assertIsInstance(self.message.options[6], OptionRequestOption)
        self.assertIsInstance(self.message.options[7], VendorClassOption)

    def test_save(self):
        self.assertEqual(self.packet, self.message.save())


class Reply(unittest.TestCase):
    def setUp(self):
        self.packet = dhcpv6_packets.reply_packet
        self.length, self.message = Message.parse(self.packet)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet))

    def test_class(self):
        self.assertIsInstance(self.message, ClientServerMessage)

    def test_type(self):
        self.assertEqual(self.message.message_type, MSG_REPLY)

    def test_transaction_id(self):
        self.assertEqual(self.message.transaction_id, bytes.fromhex('f350d6'))

    def test_options(self):
        self.assertIsInstance(self.message.options[0], IANAOption)
        self.assertIsInstance(self.message.options[1], UnknownOption)  # TODO
        self.assertIsInstance(self.message.options[2], ClientIdentifierOption)
        self.assertIsInstance(self.message.options[3], ServerIdentifierOption)
        self.assertIsInstance(self.message.options[4], ReconfigureAcceptOption)
        self.assertIsInstance(self.message.options[5], UnknownOption)  # TODO

    def test_save(self):
        self.assertEqual(self.packet, self.message.save())


class RelayedSolicit(unittest.TestCase):
    def setUp(self):
        self.packet = dhcpv6_packets.relayed_solicit_packet
        self.length, self.message = Message.parse(self.packet)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet))

    def test_class(self):
        self.assertIsInstance(self.message, RelayServerMessage)

    def test_type(self):
        self.assertEqual(self.message.message_type, MSG_RELAY_FORW)

    def test_link_address(self):
        self.assertEqual(self.message.link_address, IPv6Address('2001:db8:ffff:1::1'))

    def test_peer_address(self):
        self.assertEqual(self.message.peer_address, IPv6Address('fe80::3631:c4ff:fe3c:b2f1'))

    def test_options(self):
        self.assertIsInstance(self.message.options[0], RelayMessageOption)
        self.assertIsInstance(self.message.options[1], InterfaceIdOption)
        self.assertIsInstance(self.message.options[2], UnknownOption)  # TODO

    def test_save(self):
        self.assertEqual(self.packet, self.message.save())


class RelayedAdvertise(unittest.TestCase):
    def setUp(self):
        self.packet = dhcpv6_packets.relayed_advertise_message
        self.length, self.message = Message.parse(self.packet)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet))

    def test_class(self):
        self.assertIsInstance(self.message, RelayServerMessage)

    def test_type(self):
        self.assertEqual(self.message.message_type, MSG_RELAY_REPL)

    def test_link_address(self):
        self.assertEqual(self.message.link_address, IPv6Address('2001:db8:ffff:1::1'))

    def test_peer_address(self):
        self.assertEqual(self.message.peer_address, IPv6Address('fe80::3631:c4ff:fe3c:b2f1'))

    def test_options(self):
        self.assertIsInstance(self.message.options[0], InterfaceIdOption)
        self.assertIsInstance(self.message.options[1], RelayMessageOption)

    def test_save(self):
        self.assertEqual(self.packet, self.message.save())


if __name__ == '__main__':
    unittest.main()
