"""
Test the DS-Lite options implementations
"""
import unittest

from dhcpkit.ipv6.extensions.dslite import AFTRNameOption
from dhcpkit.ipv6.extensions.sip_servers import SIPServersDomainNameListOption
from dhcpkit.tests.ipv6.options import test_option


class AFTRNameOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00400012') + b'\x04aftr\x08steffann\x02nl\x00'
        self.option_object = AFTRNameOption(fqdn='aftr.steffann.nl.')
        self.parse_option()

    def test_validate_fqdn(self):
        self.option.fqdn = ['aftr.steffann.nl']
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.fqdn = None
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

        self.option.fqdn = 'x'
        with self.assertRaisesRegex(ValueError, 'too short'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must end with a 0-length label'):
            SIPServersDomainNameListOption.parse(bytes.fromhex('0040000c') + b'\x08steffann\x02nl\x00')

        with self.assertRaisesRegex(ValueError, 'does not match the length'):
            SIPServersDomainNameListOption.parse(bytes.fromhex('0040000e') + b'\x08steffann\x02nl\x00\x01')


if __name__ == '__main__':
    unittest.main()
