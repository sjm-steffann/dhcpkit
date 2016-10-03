"""
Test the VendorSpecificInformationOption implementation
"""
import unittest

from dhcpkit.ipv6.options import VendorSpecificInformationOption
from dhcpkit.tests.ipv6.options import test_option


class VendorSpecificInformationOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0011002000009d10') \
                            + b'\x00\x01\x00\x06Option' \
                            + b'\x00\x02\x00\x0eAnother Option'
        self.option_object = VendorSpecificInformationOption(40208, [(1, b'Option'), (2, b'Another Option')])
        self.parse_option()

    def test_enterprise_number(self):
        self.check_unsigned_integer_property('enterprise_number', size=32)

    def test_vendor_options(self):
        self.option.vendor_options = b'Not a list'
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.vendor_options = [b'In a list', b'X' * 2 ** 16]
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            VendorSpecificInformationOption.parse(bytes.fromhex('0011000d00009d10') + b'\x00\x01\x00\x06Option')

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            VendorSpecificInformationOption.parse(bytes.fromhex('0011000f00009d10') +
                                                  b'\x00\x01\x00\x06Option\x00\x00\x00\x00')


if __name__ == '__main__':
    unittest.main()
