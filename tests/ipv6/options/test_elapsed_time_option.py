"""
Test the ElapsedTimeOption implementation
"""
import unittest

from dhcpkit.ipv6.options import ElapsedTimeOption
from tests.ipv6.options import test_option


class OptionRequestOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0008000204d2')
        self.option_object = ElapsedTimeOption(elapsed_time=1234)
        self.parse_option()

    def test_validate_elapsed_time(self):
        self.option.elapsed_time = 0.1
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

        self.option.elapsed_time = 0
        self.option.validate()

        self.option.elapsed_time = -1
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

        self.option.elapsed_time = 65535
        self.option.validate()

        self.option.elapsed_time = 65536
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 2'):
            ElapsedTimeOption.parse(bytes.fromhex('000800000000ffff'))


if __name__ == '__main__':
    unittest.main()
