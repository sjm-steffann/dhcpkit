"""
Test the NTP option implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.ntp import NTPMulticastAddressSubOption, NTPServerAddressSubOption, \
    NTPServerFQDNSubOption, NTPServersOption, NTPSubOption, UnknownNTPSubOption
from dhcpkit.tests.ipv6.options import test_option


class NTPServersOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0038004b'
                                          '0001001020010db8000000000000000000000001'
                                          '00020010ff12000000000000000000000000abcd'
                                          '00030011') + b'\x03ntp\x08steffann\x02nl\x00' + \
                            bytes.fromhex('ffff000a') + b'RandomData'
        self.option_object = NTPServersOption(options=[
            NTPServerAddressSubOption(IPv6Address('2001:db8::1')),
            NTPMulticastAddressSubOption(IPv6Address('ff12::abcd')),
            NTPServerFQDNSubOption('ntp.steffann.nl.'),
            UnknownNTPSubOption(65535, b'RandomData'),
        ])
        self.parse_option()

    def test_parse_wrong_type(self):
        with self.assertRaisesRegex(ValueError, 'does not contain NTPServerAddressSubOption data'):
            option = NTPServerAddressSubOption()
            option.load_from(b'00020010ff12000000000000000000000000abcd')

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'does not match the combined length'):
            NTPServersOption.parse(bytes.fromhex('003800130001001020010db8000000000000000000000001'))


class NTPSubOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('ffff000a') + b'RandomData'
        self.option_object = UnknownNTPSubOption(65535, b'RandomData')
        self.parse_option()

    def parse_option(self):
        self.length, self.option = NTPSubOption.parse(self.option_bytes)
        self.assertIsInstance(self.option, NTPSubOption)
        self.option_class = type(self.option)

    def test_load_from_wrong_buffer(self):
        if issubclass(self.option_class, UnknownNTPSubOption):
            # UnknownNTPSubOption accepts any parseable buffer, no point in testing that one
            return

        super().test_load_from_wrong_buffer()


class UnknownNTPSubOptionTestCase(NTPSubOptionTestCase):
    def test_validate_suboption_type(self):
        self.check_unsigned_integer_property('suboption_type', size=16)

    def test_validate_value(self):
        self.option.suboption_data = bytes.fromhex('00112233')
        self.assertEqual(self.option.value, '00112233')

    def test_validate_suboption_data(self):
        self.option.suboption_data = b'AB'
        self.option.validate()

        self.option.suboption_data = 'ABC'
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            self.option.validate()


class NTPServerAddressSubOptionTestCase(NTPSubOptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0001001020010db8000000000000000000000001')
        self.option_object = NTPServerAddressSubOption(IPv6Address('2001:db8::1'))
        self.parse_option()

    def test_config_datatype(self):
        value = NTPServerAddressSubOption.config_datatype('2001:db8::1')
        self.assertEqual(value, IPv6Address('2001:db8::1'))

        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            NTPServerAddressSubOption.config_datatype('::')

        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            NTPServerAddressSubOption.config_datatype('::1')

        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            NTPServerAddressSubOption.config_datatype('fe80::1')

        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            NTPServerAddressSubOption.config_datatype('ff02::1')

    def test_validate_value(self):
        self.option.address = IPv6Address('2001:0db8::0001')
        self.assertEqual(self.option.value, '2001:db8::1')

    def test_validate_address(self):
        self.option.address = bytes.fromhex('20010db8000000000000000000000001')
        with self.assertRaisesRegex(ValueError, 'routable IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('2001:db8::1')
        self.option.validate()

        self.option.address = IPv6Address('::')
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

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 16'):
            NTPServerAddressSubOption.parse(bytes.fromhex('0001000f'))

        with self.assertRaisesRegex(ValueError, 'must have length 16'):
            NTPServerAddressSubOption.parse(bytes.fromhex('00010011'))


class NTPMulticastAddressSubOptionTestCase(NTPSubOptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00020010ff12000000000000000000000000abcd')
        self.option_object = NTPMulticastAddressSubOption(IPv6Address('ff12::abcd'))
        self.parse_option()

    def test_config_datatype(self):
        value = NTPMulticastAddressSubOption.config_datatype('ff02::1')
        self.assertEqual(value, IPv6Address('ff02::1'))

        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            NTPMulticastAddressSubOption.config_datatype('::')

        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            NTPMulticastAddressSubOption.config_datatype('::1')

        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            NTPMulticastAddressSubOption.config_datatype('fe80::1')

        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            NTPMulticastAddressSubOption.config_datatype('2001:db8::1')

    def test_validate_value(self):
        self.option.address = IPv6Address('ff02:0db8::0001')
        self.assertEqual(self.option.value, 'ff02:db8::1')

    def test_validate_address(self):
        self.option.address = bytes.fromhex('20010db8000000000000000000000001')
        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('ff02::1')
        self.option.validate()

        self.option.address = IPv6Address('::')
        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('::1')
        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('fe80::1')
        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            self.option.validate()

        self.option.address = IPv6Address('2001:db8::1')
        with self.assertRaisesRegex(ValueError, 'multicast IPv6 address'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 16'):
            NTPMulticastAddressSubOption.parse(bytes.fromhex('0002000f'))

        with self.assertRaisesRegex(ValueError, 'must have length 16'):
            NTPMulticastAddressSubOption.parse(bytes.fromhex('00020011'))


class NTPServerFQDNSubOptionTestCase(NTPSubOptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00030011') + b'\x03ntp\x08steffann\x02nl\x00'
        self.option_object = NTPServerFQDNSubOption('ntp.steffann.nl.')
        self.parse_option()

    def test_config_datatype(self):
        value = NTPServerFQDNSubOption.config_datatype('ntp.steffann.nl')
        self.assertEqual(value, 'ntp.steffann.nl')

        with self.assertRaisesRegex(ValueError, 'letters, digits and hyphens'):
            NTPServerFQDNSubOption.config_datatype('something that is not a domain name')

        with self.assertRaisesRegex(ValueError, '1 to 63 characters long'):
            NTPServerFQDNSubOption.config_datatype('something..bad')

        with self.assertRaisesRegex(ValueError, '1 to 63 characters long'):
            NTPServerFQDNSubOption.config_datatype('steffann-steffann-steffann-steffann-'
                                                   'steffann-steffann-steffann-steffann.bad')

    def test_validate_value(self):
        self.option.fqdn = 'example.com'
        self.assertEqual(self.option.value, 'example.com')

    def test_validate_fqdn(self):
        self.option.fqdn = ['steffann.nl']
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.fqdn = 'x' + '.x' * 127
        self.option.validate()

        self.option.fqdn = 'xx' + '.x' * 127
        with self.assertRaisesRegex(ValueError, 'must be 255 characters or less'):
            self.option.validate()

        self.option.fqdn = 'www.123456789012345678901234567890123456789012345678901234567890123.nl'
        self.option.validate()

        self.option.fqdn = 'www.1234567890123456789012345678901234567890123456789012345678901234.nl'
        with self.assertRaisesRegex(ValueError, 'must be 1 to 63 characters long'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must end with a 0-length label'):
            NTPServerFQDNSubOption.parse(bytes.fromhex('0003000c') + b'\x08steffann\x02nl\x00')

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            NTPServerFQDNSubOption.parse(bytes.fromhex('0003000e') + b'\x08steffann\x02nl\x00\x01')


if __name__ == '__main__':
    unittest.main()
