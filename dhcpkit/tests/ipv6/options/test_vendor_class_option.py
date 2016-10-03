"""
Test the VendorClassOption implementation
"""
import unittest

from dhcpkit.ipv6.options import VendorClassOption
from dhcpkit.tests.ipv6.options import test_option


class VendorClassOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0010001a00009d10') + b'\x00\x05Class' + b'\x00\x0dAnother Class'
        self.option_object = VendorClassOption(40208, [b'Class', b'Another Class'])
        self.parse_option()

    def test_enterprise_number(self):
        self.check_unsigned_integer_property('enterprise_number', size=32)

    def test_vendor_classes(self):
        self.option.vendor_classes = b'Not a list'
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.vendor_classes = [b'In a list', b'X' * 2 ** 16]
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            VendorClassOption.parse(bytes.fromhex('0010000a00009d10') + b'\x00\x05Class')

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            VendorClassOption.parse(bytes.fromhex('0010000d00009d10') + b'\x00\x05Class\x00\x01X')


if __name__ == '__main__':
    unittest.main()
