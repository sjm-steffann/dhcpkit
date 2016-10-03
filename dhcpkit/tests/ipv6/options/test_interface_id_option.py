"""
Test the InterfaceIdOption implementation
"""
import unittest

from dhcpkit.ipv6.options import InterfaceIdOption
from dhcpkit.tests.ipv6.options import test_option


class UnknownOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0012001030313233343536373839616263646566')
        self.option_object = InterfaceIdOption(b'0123456789abcdef')
        self.parse_option()

    def test_interface_id(self):
        self.option.interface_id = 'BlaBla'
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            self.option.validate()

        self.option.interface_id = 'X' * 2 ** 16
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            self.option.validate()


if __name__ == '__main__':
    unittest.main()
