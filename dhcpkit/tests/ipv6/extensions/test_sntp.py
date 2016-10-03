"""
Test the SNTP options implementations
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.sntp import SNTPServersOption
from dhcpkit.tests.ipv6.options import test_option


class SNTPServersOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('001f0020'
                                          '20010db8000000000000000000000001'
                                          '20010db8000000000000000000000002')
        self.option_object = SNTPServersOption(sntp_servers=[IPv6Address('2001:db8::1'),
                                                             IPv6Address('2001:db8::2')])
        self.parse_option()

    def test_validate_sntp_servers(self):
        self.option.sntp_servers = IPv6Address('2001:db8::1')
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.sntp_servers = ['2001:db8::1', '2001:db8::2']
        with self.assertRaisesRegex(ValueError, 'IPv6 address'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length must be a multiple of 16'):
            SNTPServersOption.parse(bytes.fromhex('001f000f20010db8000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            SNTPServersOption.parse(bytes.fromhex('001f001120010db8000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'length must be a multiple of 16'):
            SNTPServersOption.parse(bytes.fromhex('001f001120010db800000000000000000000000100'))


if __name__ == '__main__':
    unittest.main()
