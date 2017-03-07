"""
Test the Client FQDN option implementations
"""
import unittest

from dhcpkit.ipv6.extensions.client_fqdn import ClientFQDNOption
from dhcpkit.tests.ipv6.options import test_option


class ClientFQDNOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0027000e01') + b'\x08steffann\x02nl\x00'
        self.option_object = ClientFQDNOption(flags=1, domain_name='steffann.nl.')
        self.parse_option()

    def test_s_flag(self):
        self.option.flags = 0
        self.assertFalse(self.option.server_aaaa_update)
        self.assertFalse(self.option.server_aaaa_override)
        self.assertFalse(self.option.no_server_dns_update)

        self.option.flags = 1
        self.assertTrue(self.option.server_aaaa_update)
        self.assertFalse(self.option.server_aaaa_override)
        self.assertFalse(self.option.no_server_dns_update)

        self.option.server_aaaa_update = False
        self.assertEqual(self.option.flags, 0)

        self.option.server_aaaa_update = True
        self.assertEqual(self.option.flags, 1)

    def test_o_flag(self):
        self.option.flags = 0
        self.assertFalse(self.option.server_aaaa_update)
        self.assertFalse(self.option.server_aaaa_override)
        self.assertFalse(self.option.no_server_dns_update)

        self.option.flags = 2
        self.assertFalse(self.option.server_aaaa_update)
        self.assertTrue(self.option.server_aaaa_override)
        self.assertFalse(self.option.no_server_dns_update)

        self.option.server_aaaa_override = False
        self.assertEqual(self.option.flags, 0)

        self.option.server_aaaa_override = True
        self.assertEqual(self.option.flags, 2)

    def test_n_flag(self):
        self.option.flags = 0
        self.assertFalse(self.option.server_aaaa_update)
        self.assertFalse(self.option.server_aaaa_override)
        self.assertFalse(self.option.no_server_dns_update)

        self.option.flags = 4
        self.assertFalse(self.option.server_aaaa_update)
        self.assertFalse(self.option.server_aaaa_override)
        self.assertTrue(self.option.no_server_dns_update)

        self.option.no_server_dns_update = False
        self.assertEqual(self.option.flags, 0)

        self.option.no_server_dns_update = True
        self.assertEqual(self.option.flags, 4)

    def test_validate_domain_name(self):
        self.option.domain_name = b'steffann.nl'
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.domain_name = 'x' + '.x' * 127
        self.option.validate()

        self.option.domain_name = 'xx' + '.x' * 127
        with self.assertRaisesRegex(ValueError, 'must be 255 characters or less'):
            self.option.validate()

        self.option.domain_name = 'www.123456789012345678901234567890123456789012345678901234567890123.nl'
        self.option.validate()

        self.option.domain_name = 'www.1234567890123456789012345678901234567890123456789012345678901234.nl'
        with self.assertRaisesRegex(ValueError, 'must be 1 to 63 characters long'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'Invalid encoded domain name'):
            ClientFQDNOption.parse(bytes.fromhex('0027000c01') + b'\x08steffann\x02nl\x00')

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            ClientFQDNOption.parse(bytes.fromhex('0027000f01') + b'\x08steffann\x02nl\x00\x01')

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            ClientFQDNOption.parse(bytes.fromhex('0027000f01') + b'\x08steffann\x02nl\x00')


if __name__ == '__main__':
    unittest.main()
