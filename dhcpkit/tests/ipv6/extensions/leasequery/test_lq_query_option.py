"""
Test the LQQueryOption implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.leasequery import LQQueryOption, OPTION_LQ_RELAY_DATA, QUERY_BY_ADDRESS
from dhcpkit.ipv6.options import OptionRequestOption, UnknownOption
from dhcpkit.tests.ipv6.options import test_option


class LQQueryOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex(
            '002c'  # Option type 44: OPTION_LQ_QUERY
            '0017'  # Option length: 23
            '01'  # Query type: QUERY_BY_ADDRESS
            'fe800000000000000000000000000001'  # Link address: fe80::1

            '0006'  # Option type: OPTION_ORO
            '0002'  # Option length: 2
            '002f'  # Requested option: OPTION_LQ_RELAY_DATA
        )
        self.option_object = LQQueryOption(
            query_type=QUERY_BY_ADDRESS,
            link_address=IPv6Address('fe80::1'),
            options=[
                OptionRequestOption(requested_options=[OPTION_LQ_RELAY_DATA]),
            ]
        )

        self.parse_option()

    def test_parse_wrong_type(self):
        with self.assertRaisesRegex(ValueError, 'does not contain LQQueryOption data'):
            option = LQQueryOption()
            option.load_from(b'00020010ff12000000000000000000000000abcd')

    def test_validate_query_type(self):
        self.check_unsigned_integer_property('query_type', 8)

    def test_validate_link_address(self):
        self.option.link_address = IPv6Address('2001:db8::1')
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_address = '2001:db8::1'
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_address = bytes.fromhex('fe800000000000000000000000000001')
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_address = IPv6Address('ff02::1')
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'valid IPv6 address'):
            self.option.link_address = IPv6Address('::1')
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            LQQueryOption.parse(bytes.fromhex('002c001001fe800000000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            LQQueryOption.parse(bytes.fromhex('002c001201fe800000000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            LQQueryOption.parse(bytes.fromhex('002c001601fe80000000000000000000000000000100060002002f'))

    def test_get_options_of_type(self):
        # Our test-cases have one OptionRequestOption
        found_options = self.option.get_options_of_type(OptionRequestOption)
        self.assertEqual(len(found_options), 1)
        self.assertIsInstance(found_options[0], OptionRequestOption)

        # But our test-cases don't have an UnknownOption in them
        found_options = self.option.get_options_of_type(UnknownOption)
        self.assertEqual(len(found_options), 0)

    def test_get_option_of_type(self):
        # Our test-cases have one OptionRequestOption
        found_option = self.option.get_option_of_type(OptionRequestOption)
        self.assertIsInstance(found_option, OptionRequestOption)

        # But our test-cases don't have an UnknownOption in them
        found_option = self.option.get_option_of_type(UnknownOption)
        self.assertIsNone(found_option)


if __name__ == '__main__':
    unittest.main()
