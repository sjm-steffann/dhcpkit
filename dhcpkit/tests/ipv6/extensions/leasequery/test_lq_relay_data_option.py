"""
Test the LQRelayDataOption implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.leasequery import LQRelayDataOption
from dhcpkit.ipv6.messages import RelayForwardMessage, SolicitMessage
from dhcpkit.ipv6.options import InterfaceIdOption
from dhcpkit.tests.ipv6.options import test_option


class ClientDataOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex(
            '002f'  # Option type: OPTION_LQ_RELAY_DATA
            '003b'  # Option length: 59
            '20010db8000000000000000000000002'  # Peer address: 2001:db8::2

            '0c'  # Message type: MSG_RELAY_FORW
            '00'  # Hop count: 0
            '20010db8000000000000000000000002'  # Link address: 2001:db8::2
            'fe800000000000000000000000000022'  # Peer address: fe80::22

            '0012'  # Option type: OPTION_INTERFACE_ID
            '0005'  # Option length: 5
            '4661322f33'  # Interface ID: 'Fa2/3'
        )
        self.option_object = LQRelayDataOption(
            peer_address=IPv6Address('2001:db8::2'),
            relay_message=RelayForwardMessage(
                hop_count=0,
                link_address=IPv6Address('2001:db8::2'),
                peer_address=IPv6Address('fe80::22'),
                options=[
                    InterfaceIdOption(interface_id=b'Fa2/3'),
                ]
            )
        )

        self.parse_option()

    def test_validate_peer_address(self):
        self.option.peer_address = IPv6Address('2001:db8::1')
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.peer_address = '2001:db8::1'
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.peer_address = bytes.fromhex('fe800000000000000000000000000001')
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.peer_address = IPv6Address('ff02::1')
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.peer_address = IPv6Address('::1')
            self.option.validate()

    def test_test_wrong_message(self):
        with self.assertRaisesRegex(ValueError, 'must be an IPv6 DHCP message'):
            LQRelayDataOption(
                peer_address=IPv6Address('2001:db8::2'),
                relay_message=None
            ).validate()

        with self.assertRaisesRegex(ValueError, 'cannot contain'):
            # noinspection PyTypeChecker
            LQRelayDataOption(
                peer_address=IPv6Address('2001:db8::2'),
                relay_message=SolicitMessage()
            ).validate()

    def test_parse_wrong_type(self):
        with self.assertRaisesRegex(ValueError, 'does not contain LQRelayDataOption data'):
            option = LQRelayDataOption()
            option.load_from(b'00020010ff12000000000000000000000000abcd')

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'embedded message has a different length'):
            LQRelayDataOption.parse(bytes.fromhex(
                '002f'  # Option type: OPTION_LQ_RELAY_DATA
                '003a'  # Option length: 58 (should be 59)
                '20010db8000000000000000000000002'  # Peer address: 2001:db8::2

                '0c'  # Message type: MSG_RELAY_FORW
                '00'  # Hop count: 0
                '20010db8000000000000000000000002'  # Link address: 2001:db8::2
                'fe800000000000000000000000000022'  # Peer address: fe80::22

                '0012'  # Option type: OPTION_INTERFACE_ID
                '0005'  # Option length: 5
                '4661322f33'  # Interface ID: 'Fa2/3'
            ))

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            LQRelayDataOption.parse(bytes.fromhex(
                '002f'  # Option type: OPTION_LQ_RELAY_DATA
                '003c'  # Option length: 60 (should be 59)
                '20010db8000000000000000000000002'  # Peer address: 2001:db8::2

                '0c'  # Message type: MSG_RELAY_FORW
                '00'  # Hop count: 0
                '20010db8000000000000000000000002'  # Link address: 2001:db8::2
                'fe800000000000000000000000000022'  # Peer address: fe80::22

                '0012'  # Option type: OPTION_INTERFACE_ID
                '0005'  # Option length: 5
                '4661322f33'  # Interface ID: 'Fa2/3'
            ))


if __name__ == '__main__':
    unittest.main()
