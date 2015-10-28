"""
Test the IAAddressOption implementation
"""
from ipaddress import IPv6Address
import unittest

from dhcpkit.ipv6.options import IAAddressOption, StatusCodeOption, STATUS_NOTONLINK
from tests.ipv6.options import test_option


class IAAddressOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0005003520010db800010023045678900bc0cafe0001518000093a80'
                                          '000d0019000457686572652064696420796f752067657420746861743f')
        self.option_object = IAAddressOption(
            address=IPv6Address('2001:db8:1:23:456:7890:bc0:cafe'),
            preferred_lifetime=86400,
            valid_lifetime=7 * 86400,
            options=[
                StatusCodeOption(STATUS_NOTONLINK, 'Where did you get that?')
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
        self.option.preferred_lifetime = 0.1
        with self.assertRaisesRegex(ValueError, 'Preferred lifetime .* unsigned 32 bit integer'):
            self.option.validate()

        self.option.preferred_lifetime = -1
        with self.assertRaisesRegex(ValueError, 'Preferred lifetime .* unsigned 32 bit integer'):
            self.option.validate()

        self.option.preferred_lifetime = 2 ** 32
        with self.assertRaisesRegex(ValueError, 'Preferred lifetime .* unsigned 32 bit integer'):
            self.option.validate()

    def test_validate_valid_lifetime(self):
        self.option.valid_lifetime = 0.1
        with self.assertRaisesRegex(ValueError, 'Valid lifetime .* unsigned 32 bit integer'):
            self.option.validate()

        self.option.valid_lifetime = -1
        with self.assertRaisesRegex(ValueError, 'Valid lifetime .* unsigned 32 bit integer'):
            self.option.validate()

        self.option.valid_lifetime = 2 ** 32
        with self.assertRaisesRegex(ValueError, 'Valid lifetime .* unsigned 32 bit integer'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            IAAddressOption.parse(bytes.fromhex('0005000020010db800010023045678900bc0cafe0001518000093a80'))


if __name__ == '__main__':
    unittest.main()
