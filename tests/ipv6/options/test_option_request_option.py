"""
Test the OptionRequestOption implementation
"""
import unittest

from dhcpkit.ipv6.options import OptionRequestOption, OPTION_IA_NA, OPTION_IA_TA
from tests.ipv6.options import test_option


class OptionRequestOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0006000400030004')
        self.option_object = OptionRequestOption(requested_options=[OPTION_IA_NA, OPTION_IA_TA])
        self.parse_option()

    def test_validate_requested_options(self):
        self.option.requested_options = [OPTION_IA_NA, 0, OPTION_IA_TA]
        self.option.validate()

        self.option.requested_options = [OPTION_IA_NA, -1, OPTION_IA_TA]
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

        self.option.requested_options = [OPTION_IA_NA, 65535, OPTION_IA_TA]
        self.option.validate()

        self.option.requested_options = [OPTION_IA_NA, 65536, OPTION_IA_TA]
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'Invalid option length'):
            OptionRequestOption.parse(bytes.fromhex('0006000300030004'))


if __name__ == '__main__':
    unittest.main()
