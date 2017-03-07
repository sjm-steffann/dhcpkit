"""
Test the DNS options implementations
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.dns import DomainSearchListOption, RecursiveNameServersOption
from dhcpkit.tests.ipv6.options import test_option


class RecursiveNameServersOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00170020'
                                          '20010db8000000000000000000000001'
                                          '20010db8000000000000000000000002')
        self.option_object = RecursiveNameServersOption(dns_servers=[IPv6Address('2001:db8::1'),
                                                                     IPv6Address('2001:db8::2')])
        self.parse_option()

    def test_validate_addresses(self):
        self.option.dns_servers = IPv6Address('2001:db8::1')
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.dns_servers = ['2001:db8::1', '2001:db8::2']
        with self.assertRaisesRegex(ValueError, 'IPv6 address'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length must be a multiple of 16'):
            RecursiveNameServersOption.parse(bytes.fromhex('0017000f20010db8000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            RecursiveNameServersOption.parse(bytes.fromhex('0017001120010db8000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'length must be a multiple of 16'):
            RecursiveNameServersOption.parse(bytes.fromhex('0017001120010db800000000000000000000000100'))


class DomainSearchListOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0018000d') + b'\x08steffann\x02nl\x00'
        self.option_object = DomainSearchListOption(search_list=['steffann.nl.'])
        self.parse_option()

    def test_validate_search_list(self):
        self.option.search_list = 'steffann.nl'
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.search_list = ['steffann.nl', None]
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.search_list = ['x' + '.x' * 127]
        self.option.validate()

        self.option.search_list = ['xx' + '.x' * 127]
        with self.assertRaisesRegex(ValueError, 'must be 255 characters or less'):
            self.option.validate()

        self.option.search_list = ['www.123456789012345678901234567890123456789012345678901234567890123.nl']
        self.option.validate()

        self.option.search_list = ['www.1234567890123456789012345678901234567890123456789012345678901234.nl']
        with self.assertRaisesRegex(ValueError, 'must be 1 to 63 characters long'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must end with a 0-length label'):
            DomainSearchListOption.parse(bytes.fromhex('0018000c') + b'\x08steffann\x02nl\x00')

        with self.assertRaisesRegex(ValueError, 'exceeds available buffer'):
            DomainSearchListOption.parse(bytes.fromhex('0018000e') + b'\x08steffann\x02nl\x00\x01')


if __name__ == '__main__':
    unittest.main()
