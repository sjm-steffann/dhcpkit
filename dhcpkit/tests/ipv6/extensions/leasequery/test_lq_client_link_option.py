"""
Test the LQClientLink implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.leasequery import LQClientLink, LQRelayDataOption
from dhcpkit.tests.ipv6.options import test_option


class ClientDataOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex(
            '0030'  # Option type: OPTION_LQ_CLIENT_LINK
            '0030'  # Option length: 48
            '20010db8000000000000000000000001'  # Link address: 2001:db8::2
            '20010db8000000000000000000000002'  # Link address: 2001:db8::2
            '20010db8000000000000000000000004'  # Link address: 2001:db8::2
        )
        self.option_object = LQClientLink(link_addresses=[
            IPv6Address('2001:db8::1'),
            IPv6Address('2001:db8::2'),
            IPv6Address('2001:db8::4'),
        ])

        self.parse_option()

    def test_validate_link_addresses(self):
        self.option.link_addresses = [IPv6Address('2001:db8::1')]
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.link_addresses = IPv6Address('2001:db8::1')
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_addresses = [IPv6Address('2001:db8::1'),
                                          '2001:db8::1']
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_addresses = [bytes.fromhex('fe800000000000000000000000000001'),
                                          IPv6Address('2001:db8::1')]
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_addresses = [IPv6Address('2001:db8::1'),
                                          IPv6Address('ff02::1')]
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_addresses = [IPv6Address('::1'),
                                          IPv6Address('2001:db8::1')]
            self.option.validate()

    def test_parse_wrong_type(self):
        with self.assertRaisesRegex(ValueError, 'does not contain LQClientLink data'):
            option = LQClientLink()
            option.load_from(b'00020010ff12000000000000000000000000abcd')

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match the combined length'):
            LQRelayDataOption.parse(bytes.fromhex(
                '0030'  # Option type: OPTION_LQ_CLIENT_LINK
                '002f'  # Option length: 47 (should be 48)
                '20010db8000000000000000000000001'  # Link address: 2001:db8::2
                '20010db8000000000000000000000002'  # Link address: 2001:db8::2
                '20010db8000000000000000000000004'  # Link address: 2001:db8::2
            ))

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            LQRelayDataOption.parse(bytes.fromhex(
                '0030'  # Option type: OPTION_LQ_CLIENT_LINK
                '0031'  # Option length: 49 (should be 48)
                '20010db8000000000000000000000001'  # Link address: 2001:db8::2
                '20010db8000000000000000000000002'  # Link address: 2001:db8::2
                '20010db8000000000000000000000004'  # Link address: 2001:db8::2
            ))


if __name__ == '__main__':
    unittest.main()
