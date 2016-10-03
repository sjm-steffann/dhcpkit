"""
Test the IANAOption implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.options import IAAddressOption, IANAOption, STATUS_SUCCESS, StatusCodeOption, UnknownOption
from dhcpkit.tests.ipv6.options import test_option


class IANAOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0003'  # option_type: OPTION_IA_NA
                                          '0044'  # option_length
                                          '41424344'  # iaid: ABCD
                                          '00000029'  # t1: 41
                                          '0000002a'  # t2: 42
                                          '0005'  # option_type: OPTION_IAADDR
                                          '0018'  # option_length
                                          '20010db8000000000000000000000001'  # address: 2001:db8::1
                                          '00000000'  # preferred_lifetime
                                          '00000000'  # valid_lifetime
                                          '000d'  # option_type: OPTION_STATUS_CODE
                                          '0018'  # option_length
                                          '0000'  # status_code
                                          '45766572797468696e6720697320617765736f6d6521')  # status_message
        self.option_object = IANAOption(iaid=b'ABCD', t1=41, t2=42, options=[
            IAAddressOption(address=IPv6Address('2001:db8::1')),
            StatusCodeOption(status_code=STATUS_SUCCESS, status_message='Everything is awesome!')
        ])
        self.parse_option()

    def test_validate_iaid(self):
        self.option.iaid = b'ABC'
        with self.assertRaisesRegex(ValueError, 'must be four bytes'):
            self.option.validate()

        self.option.iaid = b'ABCDE'
        with self.assertRaisesRegex(ValueError, 'must be four bytes'):
            self.option.validate()

        self.option.iaid = 'ABCD'
        with self.assertRaisesRegex(ValueError, 'must be four bytes'):
            self.option.validate()

    def test_validate_t1(self):
        self.check_unsigned_integer_property('t1', size=32)

    def test_validate_t2(self):
        self.check_unsigned_integer_property('t2', size=32)

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            IANAOption.parse(bytes.fromhex('0003000041424344000000290000002a'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            IANAOption.parse(bytes.fromhex('0003000d41424344000000290000002a00140000'))

    def test_sort(self):
        self.assertFalse(self.option > self.option)
        self.assertTrue(self.option <= self.option)

        with self.assertRaises(TypeError):
            self.assertFalse(self.option > 0)

    def test_get_options_of_type(self):
        found_options = self.option.get_options_of_type(StatusCodeOption)
        self.assertEqual(len(found_options), 1)
        self.assertIsInstance(found_options[0], StatusCodeOption)

        # But our test-cases don't have an UnknownOption in them
        found_options = self.option.get_options_of_type(UnknownOption)
        self.assertEqual(len(found_options), 0)

    def test_get_option_of_type(self):
        found_option = self.option.get_option_of_type(StatusCodeOption)
        self.assertIsInstance(found_option, StatusCodeOption)

        # But our test-cases don't have an UnknownOption in them
        found_option = self.option.get_option_of_type(UnknownOption)
        self.assertIsNone(found_option)

    def test_get_addresses(self):
        addresses = self.option.get_addresses()
        self.assertListEqual(addresses, [IPv6Address('2001:db8::1')])


if __name__ == '__main__':
    unittest.main()
