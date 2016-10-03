"""
Test the UserClassOption implementation
"""
import unittest

from dhcpkit.ipv6.options import UserClassOption
from dhcpkit.tests.ipv6.options import test_option


class UserClassOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('000f0016') + b'\x00\x05Class' + b'\x00\x0dAnother Class'
        self.option_object = UserClassOption([b'Class', b'Another Class'])
        self.parse_option()

    def test_user_classes(self):
        self.option.user_classes = b'Not a list'
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.user_classes = [b'In a list', b'X' * 2 ** 16]
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            UserClassOption.parse(bytes.fromhex('000f0006') + b'\x00\x05Class')

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            UserClassOption.parse(bytes.fromhex('000f0009') + b'\x00\x05Class\x00\x01X')


if __name__ == '__main__':
    unittest.main()
