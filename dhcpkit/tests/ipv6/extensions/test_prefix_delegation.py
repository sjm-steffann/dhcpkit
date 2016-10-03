"""
Test the Prefix Delegation option implementation
"""
import unittest
from ipaddress import IPv6Network

from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.options import STATUS_NOT_ON_LINK, STATUS_SUCCESS, StatusCodeOption, UnknownOption
from dhcpkit.tests.ipv6.options import test_option


class IAPDOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0019'  # option_type: OPTION_IA_PD
                                          '0045'  # option_length
                                          '41424344'  # iaid: ABCD
                                          '00000029'  # t1: 41
                                          '0000002a'  # t2: 42
                                          '001a'  # option_type: OPTION_IAPREFIX
                                          '0019'  # option_length
                                          '00000000'  # preferred_lifetime
                                          '00000000'  # valid_lifetime
                                          '30'  # prefix_length: 48
                                          '20010db8000000000000000000000000'  # prefix: 2001:db8::
                                          '000d'  # option_type: OPTION_STATUS_CODE
                                          '0018'  # option_length
                                          '0000'  # status_code
                                          '45766572797468696e6720697320617765736f6d6521')  # status_message
        self.option_object = IAPDOption(iaid=b'ABCD', t1=41, t2=42, options=[
            IAPrefixOption(prefix=IPv6Network('2001:db8::/48')),
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
            IAPDOption.parse(bytes.fromhex('0019000041424344000000290000002a'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            IAPDOption.parse(bytes.fromhex('0019000d41424344000000290000002a00140000'))

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

    def test_get_prefixes(self):
        prefixes = self.option.get_prefixes()
        self.assertListEqual(prefixes, [IPv6Network('2001:db8::/48')])


class IAPrefixOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('001a0036'
                                          '00015180'
                                          '00093a80'
                                          '30'
                                          '20010db8000100000000000000000000'
                                          '000d0019000457686572652064696420796f752067657420746861743f')
        self.option_object = IAPrefixOption(
            preferred_lifetime=86400,
            valid_lifetime=7 * 86400,
            prefix=IPv6Network('2001:db8:1::/48'),
            options=[
                StatusCodeOption(STATUS_NOT_ON_LINK, 'Where did you get that?')
            ]
        )
        self.parse_option()

    def test_validate_address(self):
        self.option.prefix = '2001:db8::/32'
        with self.assertRaisesRegex(ValueError, 'routable IPv6 prefix'):
            self.option.validate()

        self.option.prefix = IPv6Network('::1/128')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 prefix'):
            self.option.validate()

        self.option.prefix = IPv6Network('fe80::/64')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 prefix'):
            self.option.validate()

        self.option.prefix = IPv6Network('ff02::1/128')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 prefix'):
            self.option.validate()

    def test_validate_preferred_lifetime(self):
        self.check_unsigned_integer_property('preferred_lifetime', size=32)

    def test_validate_valid_lifetime(self):
        self.check_unsigned_integer_property('valid_lifetime', size=32)

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            IAPrefixOption.parse(bytes.fromhex('001a00090001518000093a8030'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            IAPrefixOption.parse(bytes.fromhex('001a0035'
                                               '00015180'
                                               '00093a80'
                                               '30'
                                               '20010db8000100000000000000000000'
                                               '000d0019000457686572652064696420796f752067657420746861743f'))


if __name__ == '__main__':
    unittest.main()
