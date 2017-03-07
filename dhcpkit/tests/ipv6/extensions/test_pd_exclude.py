"""
Test the PDExcludeOption implementation
"""
import unittest

from dhcpkit.ipv6.extensions.pd_exclude import PDExcludeOption
from dhcpkit.tests.ipv6.options import test_option


class PDExcludeOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('004300024078')
        self.option_object = PDExcludeOption(64, bytes.fromhex('78'))
        self.parse_option()

    def test_prefix_length(self):
        self.check_integer_property_range('prefix_length', 1, 128)

    def test_subnet_id(self):
        self.option.subnet_id = 'Not bytes'
        with self.assertRaisesRegex(ValueError, 'sequence of .* bytes'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            PDExcludeOption.parse(bytes.fromhex('004300034078'))


if __name__ == '__main__':
    unittest.main()
