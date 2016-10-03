"""
Test the SolMaxRTOption and InfMaxRTOption option implementations
"""
import unittest

from dhcpkit.ipv6.extensions.sol_max_rt import InfMaxRTOption, SolMaxRTOption
from dhcpkit.tests.ipv6.options import test_option


class SolMaxRTOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('005200041a2b3c4d')
        self.option_object = SolMaxRTOption(sol_max_rt=439041101)
        self.parse_option()

    def test_validate_sol_max_rt(self):
        self.check_unsigned_integer_property('sol_max_rt', 32)

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 4'):
            SolMaxRTOption.parse(bytes.fromhex('005200031a2b3c4d'))

        with self.assertRaisesRegex(ValueError, 'must have length 4'):
            SolMaxRTOption.parse(bytes.fromhex('005200051a2b3c4d00'))


class InfMaxRTOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('005300041a2b3c4d')
        self.option_object = InfMaxRTOption(inf_max_rt=439041101)
        self.parse_option()

    def test_validate_inf_max_rt(self):
        self.check_unsigned_integer_property('inf_max_rt', 32)

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 4'):
            InfMaxRTOption.parse(bytes.fromhex('005300031a2b3c4d'))

        with self.assertRaisesRegex(ValueError, 'must have length 4'):
            InfMaxRTOption.parse(bytes.fromhex('005300051a2b3c4d00'))


if __name__ == '__main__':
    unittest.main()
