"""
Test the CLTTimeOption implementation
"""
import unittest

from dhcpkit.ipv6.extensions.leasequery import CLTTimeOption
from dhcpkit.tests.ipv6.options import test_option


class CLTTimeOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex(
            '002e'  # Option type: OPTION_CLT_TIME
            '0004'  # Option length: 4
            '00000384'  # Client-Last-Transaction time: 900
        )
        self.option_object = CLTTimeOption(clt_time=900)

        self.parse_option()

    def test_validate_clt_time(self):
        self.check_unsigned_integer_property('clt_time', 32)

    def test_parse_wrong_type(self):
        with self.assertRaisesRegex(ValueError, 'does not contain CLTTimeOption data'):
            option = CLTTimeOption()
            option.load_from(b'00020010ff12000000000000000000000000abcd')

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 4'):
            CLTTimeOption.parse(bytes.fromhex(
                '002e'  # Option type: OPTION_CLT_TIME
                '0003'  # Option length: 3 (must be 4)
                '00000384'  # Client-Last-Transaction time: 900
            ))

        with self.assertRaisesRegex(ValueError, 'must have length 4'):
            CLTTimeOption.parse(bytes.fromhex(
                '002e'  # Option type: OPTION_CLT_TIME
                '0005'  # Option length: 5 (must be 4)
                '00000384'  # Client-Last-Transaction time: 900
            ))


if __name__ == '__main__':
    unittest.main()
