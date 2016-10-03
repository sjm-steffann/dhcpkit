"""
Test the RapidCommitOption implementation
"""
import unittest

from dhcpkit.ipv6.options import RapidCommitOption
from dhcpkit.tests.ipv6.options import test_option


class RapidCommitOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('000e0000')
        self.option_object = RapidCommitOption()
        self.parse_option()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 0'):
            RapidCommitOption.parse(bytes.fromhex('000e0001'))


if __name__ == '__main__':
    unittest.main()
