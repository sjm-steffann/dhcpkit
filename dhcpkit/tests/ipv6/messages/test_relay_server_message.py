"""
Test the RelayServerMessage implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.messages import Message, RelayForwardMessage, RelayServerMessage, UnknownMessage
from dhcpkit.ipv6.options import RelayMessageOption
from dhcpkit.tests.ipv6.messages import test_message


class RelayServerMessageTestCase(test_message.MessageTestCase):
    def setUp(self):
        # The following attributes must be overruled by child classes
        # The basics are tested with nested RelayForwardMessages
        self.packet_fixture = bytes.fromhex('0c'  # message_type: MSG_RELAY_FORW
                                            '02'  # hop_count
                                            '20010db8000000000000000000020001'  # link_address
                                            '20010db8000000000000000000020002'  # peer_address
                                            '0009'  # option_type: OPTION_RELAY_MSG
                                            '0051'  # option_length
                                            '0c'  # message_type: MSG_RELAY_FORW
                                            '01'  # hop_count
                                            '20010db8000000000000000000010001'  # link_address
                                            '20010db8000000000000000000010002'  # peer_address
                                            '0009'  # option_type: OPTION_RELAY_MSG
                                            '002b'  # option_length
                                            '0c'  # message_type: MSG_RELAY_FORW
                                            '00'  # hop_count
                                            '20010db8000000000000000000000001'  # link_address
                                            '20010db8000000000000000000000002'  # peer_address
                                            '0009'  # option_type: OPTION_RELAY_MSG
                                            '0005'  # option_length
                                            'ff'  # some unknown  message_type: 255
                                            '41424344')  # some random message_data: 'ABCD'

        self.message_fixture = RelayForwardMessage(
            hop_count=2,
            link_address=IPv6Address('2001:db8::2:1'),
            peer_address=IPv6Address('2001:db8::2:2'),
            options=[
                RelayMessageOption(
                    relayed_message=RelayForwardMessage(
                        hop_count=1,
                        link_address=IPv6Address('2001:db8::1:1'),
                        peer_address=IPv6Address('2001:db8::1:2'),
                        options=[
                            RelayMessageOption(
                                relayed_message=RelayForwardMessage(
                                    hop_count=0,
                                    link_address=IPv6Address('2001:db8::1'),
                                    peer_address=IPv6Address('2001:db8::2'),
                                    options=[
                                        RelayMessageOption(relayed_message=UnknownMessage(255, b'ABCD'))
                                    ]))
                        ]))
            ])

        self.parse_packet()

    def parse_packet(self):
        super().parse_packet()
        self.assertIsInstance(self.message, RelayServerMessage)

    def test_validate_hop_count(self):
        self.check_unsigned_integer_property('hop_count', size=8)

    def test_validate_link_address(self):
        self.message.link_address = bytes.fromhex('20010db8000000000000000000000001')
        with self.assertRaisesRegex(ValueError, 'Link-address .* IPv6 address'):
            self.message.validate()

        self.message.link_address = IPv6Address('ff02::1')
        with self.assertRaisesRegex(ValueError, 'Link-address .* non-multicast IPv6 address'):
            self.message.validate()

    def test_validate_peer_address(self):
        self.message.peer_address = bytes.fromhex('20010db8000000000000000000000001')
        with self.assertRaisesRegex(ValueError, 'Peer-address .* IPv6 address'):
            self.message.validate()

        self.message.peer_address = IPv6Address('ff02::1')
        with self.assertRaisesRegex(ValueError, 'Peer-address .* non-multicast IPv6 address'):
            self.message.validate()

    def test_get_relayed_message(self):
        self.assertEqual(self.message.relayed_message,
                         self.message_fixture.get_option_of_type(RelayMessageOption).relayed_message)

    def test_set_relayed_message(self):
        # Start with empty options
        self.message.options = []
        self.assertEqual(len(self.message.get_options_of_type(RelayMessageOption)), 0)

        self.message.relayed_message = UnknownMessage(255, b'ThisIsAnUnknownMessage')
        self.assertEqual(len(self.message.get_options_of_type(RelayMessageOption)), 1)
        self.assertEqual(self.message.relayed_message.message_data, b'ThisIsAnUnknownMessage')

        self.message.relayed_message = UnknownMessage(255, b'ThisIsADifferentUnknownMessage')
        self.assertEqual(len(self.message.get_options_of_type(RelayMessageOption)), 1)
        self.assertEqual(self.message.relayed_message.message_data, b'ThisIsADifferentUnknownMessage')

    def test_inner_message(self):
        # Make sure the inner message is a message that is not a RelayServerMessage
        self.assertIsInstance(self.message.inner_message, Message)
        self.assertNotIsInstance(self.message.inner_message, RelayServerMessage)

    def test_inner_relay_message(self):
        # Make sure the inner relay message is a RelayServerMessage
        self.assertIsInstance(self.message.inner_relay_message, RelayServerMessage)

        # that contains a message that is not a RelayServerMessage
        self.assertIsInstance(self.message.inner_relay_message.relayed_message, Message)
        self.assertNotIsInstance(self.message.inner_relay_message.relayed_message, RelayServerMessage)

    def test_missing_inner_message(self):
        # Remove the final message and check that it's being handled correctly
        self.message.inner_relay_message.options = []
        self.assertIsNone(self.message.inner_message)
        self.assertIsInstance(self.message.inner_relay_message, RelayServerMessage)

    def test_empty_relayed_message(self):
        # This uses a getter/setter, so test that code

        # Make sure we have a message to start with
        self.assertIsNotNone(self.message.relayed_message)

        # This sets the message in the RelayMessageOption
        self.message.relayed_message = None
        self.assertIsNone(self.message.relayed_message)
        with self.assertRaisesRegex(ValueError, 'must be an IPv6 DHCP message'):
            # Validation will complain about the missing message
            self.message.validate()

        # This removes the RelayMessageOption altogether
        option = self.message.get_option_of_type(RelayMessageOption)
        self.message.options.remove(option)

        # This still returns None
        self.assertIsNone(self.message.relayed_message)


if __name__ == '__main__':
    unittest.main()
