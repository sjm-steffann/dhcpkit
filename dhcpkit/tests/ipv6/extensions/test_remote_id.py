"""
Test the RemoteIdOption implementation
"""
import unittest

from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.tests.ipv6.options import test_option


class RemoteIdOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0025000800009d100123abcd')
        self.option_object = RemoteIdOption(40208, bytes.fromhex('0123abcd'))
        self.parse_option()

    def test_enterprise_number(self):
        self.check_unsigned_integer_property('enterprise_number', size=32)

    def test_remote_id(self):
        self.option.remote_id = 'Not bytes'
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            RemoteIdOption.parse(bytes.fromhex('0025000a00009d10'))


if __name__ == '__main__':
    unittest.main()
