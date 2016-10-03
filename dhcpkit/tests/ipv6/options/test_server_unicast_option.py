"""
Test the ServerUnicastOption implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.options import ServerUnicastOption
from dhcpkit.tests.ipv6.options import test_option


class ServerUnicastOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('000c001020010db8000000000000000000000001')
        self.option_object = ServerUnicastOption(IPv6Address('2001:db8::1'))
        self.parse_option()

    def test_server_address(self):
        self.option.server_address = bytes.fromhex('20010db8000000000000000000000001')
        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.validate()

        self.option.server_address = IPv6Address('2001:db8::1')
        self.option.validate()

        self.option.server_address = IPv6Address('::')
        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.validate()

        self.option.server_address = IPv6Address('::1')
        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.validate()

        self.option.server_address = IPv6Address('ff02::1')
        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 16'):
            ServerUnicastOption.parse(bytes.fromhex('000c000f'))

        with self.assertRaisesRegex(ValueError, 'must have length 16'):
            ServerUnicastOption.parse(bytes.fromhex('000c0011'))


if __name__ == '__main__':
    unittest.main()
