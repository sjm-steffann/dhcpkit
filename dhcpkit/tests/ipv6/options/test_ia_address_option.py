"""
Test the IAAddressOption implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.options import IAAddressOption, STATUS_NOT_ON_LINK, StatusCodeOption
from dhcpkit.tests.ipv6.options import test_option


class IAAddressOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0005003520010db800010023045678900bc0cafe0001518000093a80'
                                          '000d0019000457686572652064696420796f752067657420746861743f')
        self.option_object = IAAddressOption(
            address=IPv6Address('2001:db8:1:23:456:7890:bc0:cafe'),
            preferred_lifetime=86400,
            valid_lifetime=7 * 86400,
            options=[
                StatusCodeOption(STATUS_NOT_ON_LINK, 'Where did you get that?')
            ]
        )
        self.parse_option()

    def test_validate_address(self):
        self.option.address = '2001:db8::1'
        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('::1')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('fe80::1')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('ff02::1')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            self.option.validate()

    def test_validate_preferred_lifetime(self):
        self.check_unsigned_integer_property('preferred_lifetime', size=32)

    def test_validate_valid_lifetime(self):
        self.check_unsigned_integer_property('valid_lifetime', size=32)

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            IAAddressOption.parse(bytes.fromhex('0005001720010db800010023045678900bc0cafe0001518000093a80'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            IAAddressOption.parse(bytes.fromhex('0005001920010db800010023045678900bc0cafe0001518000093a8000140000'))


if __name__ == '__main__':
    unittest.main()
