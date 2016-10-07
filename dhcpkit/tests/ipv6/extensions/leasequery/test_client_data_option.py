"""
Test the ClientDataOption implementation
"""
import unittest
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.duids import EnterpriseDUID
from dhcpkit.ipv6.extensions.leasequery import CLTTimeOption, ClientDataOption, LQRelayDataOption
from dhcpkit.ipv6.extensions.prefix_delegation import IAPrefixOption
from dhcpkit.ipv6.messages import RelayForwardMessage
from dhcpkit.ipv6.options import ClientIdOption, IAAddressOption, InterfaceIdOption, UnknownOption
from dhcpkit.tests.ipv6.options import test_option


class ClientDataOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex(
            '002d'  # Option type 45: OPTION_CLIENT_DATA
            '0099'  # Option length: 153

            '0001'  # Option type 1: OPTION_CLIENT_ID
            '0015'  # Option length: 21
            '0002'  # DUID type: DUID_EN
            '00009d10'  # Enterprise ID: 40208
            '303132333435363738396162636465'  # Identifier: '0123456789abcde'

            '0005'  # Option type: OPTION_IAADDR
            '0018'  # Option length: 24
            '20010db800000000000000000000cafe'  # IPv6 address: 2001:db8::cafe
            '00000708'  # Preferred lifetime: 1800
            '00000e10'  # Valid lifetime: 3600

            '001a'  # Option type: OPTION_IAPREFIX
            '0019'  # Option length: 25
            '00000708'  # Preferred lifetime: 1800
            '00000e10'  # Valid lifetime: 3600
            '30'  # Prefix length: 48
            '20010db8000100000000000000000000'

            '002e'  # Option type: OPTION_CLT_TIME
            '0004'  # Option length: 4
            '00000384'  # Client-Last-Transaction time: 900

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
        self.option_object = ClientDataOption(options=[
            ClientIdOption(EnterpriseDUID(40208, b'0123456789abcde')),
            IAAddressOption(address=IPv6Address('2001:db8::cafe'), preferred_lifetime=1800, valid_lifetime=3600),
            IAPrefixOption(prefix=IPv6Network('2001:db8:1::/48'), preferred_lifetime=1800, valid_lifetime=3600),
            CLTTimeOption(clt_time=900),
            LQRelayDataOption(peer_address=IPv6Address('2001:db8::2'), relay_message=RelayForwardMessage(
                hop_count=0,
                link_address=IPv6Address('2001:db8::2'),
                peer_address=IPv6Address('fe80::22'),
                options=[
                    InterfaceIdOption(interface_id=b'Fa2/3'),
                ]
            ))
        ])

        self.parse_option()

    def test_parse_wrong_type(self):
        with self.assertRaisesRegex(ValueError, 'does not contain ClientDataOption data'):
            option = ClientDataOption()
            option.load_from(b'00020010ff12000000000000000000000000abcd')

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            ClientDataOption.parse(bytes.fromhex(
                '002d'  # Option type 45: OPTION_CLIENT_DATA
                '0018'  # Option length: 24 (should be 25)

                '0001'  # Option type 1: OPTION_CLIENT_ID
                '0015'  # Option length: 21
                '0002'  # DUID type: DUID_EN
                '00009d10'  # Enterprise ID: 40208
                '303132333435363738396162636465'  # Identifier: '0123456789abcde'
            ))

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            ClientDataOption.parse(bytes.fromhex(
                '002d'  # Option type 45: OPTION_CLIENT_DATA
                '001a'  # Option length: 26 (should be 25)

                '0001'  # Option type 1: OPTION_CLIENT_ID
                '0015'  # Option length: 21
                '0002'  # DUID type: DUID_EN
                '00009d10'  # Enterprise ID: 40208
                '303132333435363738396162636465'  # Identifier: '0123456789abcde'
            ))

    def test_get_options_of_type(self):
        # Our test-cases have one ClientIdOption
        found_options = self.option.get_options_of_type(ClientIdOption)
        self.assertEqual(len(found_options), 1)
        self.assertIsInstance(found_options[0], ClientIdOption)

        # But our test-cases don't have an UnknownOption in them
        found_options = self.option.get_options_of_type(UnknownOption)
        self.assertEqual(len(found_options), 0)

    def test_get_option_of_type(self):
        # Our test-cases have one OptionRequestOption
        found_option = self.option.get_option_of_type(ClientIdOption)
        self.assertIsInstance(found_option, ClientIdOption)

        # But our test-cases don't have an UnknownOption in them
        found_option = self.option.get_option_of_type(UnknownOption)
        self.assertIsNone(found_option)


if __name__ == '__main__':
    unittest.main()
