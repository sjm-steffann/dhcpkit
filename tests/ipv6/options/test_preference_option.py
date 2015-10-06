"""
Test the PreferenceOption implementation
"""
import unittest

from dhcpkit.ipv6.options import PreferenceOption
from tests.ipv6.options import test_option


class OptionRequestOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00070001ff')
        self.option_object = PreferenceOption(preference=255)
        self.parse_option()

    def test_validate_preference(self):
        self.option.preference = 0.1
        with self.assertRaisesRegex(ValueError, 'unsigned 8 bit integer'):
            self.option.validate()

        self.option.preference = 0
        self.option.validate()

        self.option.preference = -1
        with self.assertRaisesRegex(ValueError, 'unsigned 8 bit integer'):
            self.option.validate()

        self.option.preference = 255
        self.option.validate()

        self.option.preference = 256
        with self.assertRaisesRegex(ValueError, 'unsigned 8 bit integer'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 1'):
            PreferenceOption.parse(bytes.fromhex('00070002ffff'))


if __name__ == '__main__':
    unittest.main()
