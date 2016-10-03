"""
Test the StatusCodeOption implementation
"""
import unittest

from dhcpkit.ipv6.options import STATUS_NOT_ON_LINK, StatusCodeOption
from dhcpkit.tests.ipv6.options import test_option


class StatusCodeOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('000d001d00044fc3b920c3aa7465732d766f7573206d6f6e206d61c3ae7472653f')
        self.option_object = StatusCodeOption(STATUS_NOT_ON_LINK, 'Où êtes-vous mon maître?')
        self.parse_option()

    def test_status_code(self):
        self.check_unsigned_integer_property('status_code', size=16)

    def test_status_message(self):
        self.option.status_message = b'This is not a string'
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()


if __name__ == '__main__':
    unittest.main()
