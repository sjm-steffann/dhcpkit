"""
Test the ServerIdOption implementation
"""
import unittest

from dhcpkit.ipv6.duids import EnterpriseDUID
from dhcpkit.ipv6.options import ServerIdOption
from tests.ipv6.options import test_option


class ServerIdOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = b'\x00\x02\x00\x15\x00\x02\x00\x00\x9d\x100123456789abcde'
        self.option_object = ServerIdOption(EnterpriseDUID(40208, b'0123456789abcde'))
        self.parse_option()

    def test_validate_duid(self):
        self.option.duid = b'0123456789abcdef'
        with self.assertRaisesRegex(ValueError, 'DUID object'):
            self.option.validate()


if __name__ == '__main__':
    unittest.main()
