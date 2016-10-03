"""
Test the PreferenceOption implementation
"""
import unittest

from dhcpkit.ipv6.options import PreferenceOption
from dhcpkit.tests.ipv6.options import test_option


class PreferenceOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00070001ff')
        self.option_object = PreferenceOption(preference=255)
        self.parse_option()

    def test_validate_preference(self):
        self.check_unsigned_integer_property('preference', size=8)

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 1'):
            PreferenceOption.parse(bytes.fromhex('00070000ffff'))

        with self.assertRaisesRegex(ValueError, 'must have length 1'):
            PreferenceOption.parse(bytes.fromhex('00070002ffff'))


if __name__ == '__main__':
    unittest.main()
