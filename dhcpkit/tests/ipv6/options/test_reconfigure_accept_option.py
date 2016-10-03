"""
Test the ReconfigureAcceptOption implementation
"""
import unittest

from dhcpkit.ipv6.options import ReconfigureAcceptOption
from dhcpkit.tests.ipv6.options import test_option


class ReconfigureAcceptOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00140000')
        self.option_object = ReconfigureAcceptOption()
        self.parse_option()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 0'):
            ReconfigureAcceptOption.parse(bytes.fromhex('00140001'))


if __name__ == '__main__':
    unittest.main()
