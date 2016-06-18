"""
Test the IPv6 utility functions
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.utils import is_global_unicast


class IPv6UtilsTestCase(unittest.TestCase):
    def test_is_global_unicast(self):
        self.assertTrue(is_global_unicast(IPv6Address('2001:db8::1')))
        self.assertTrue(is_global_unicast(IPv6Address('fc00::1')))
        self.assertTrue(is_global_unicast(IPv6Address('fd00::1')))
        self.assertTrue(is_global_unicast(IPv6Address('dead::beef')))
        self.assertFalse(is_global_unicast(IPv6Address('::')))
        self.assertFalse(is_global_unicast(IPv6Address('::1')))
        self.assertFalse(is_global_unicast(IPv6Address('fe80::1')))
        self.assertFalse(is_global_unicast(IPv6Address('ff02::1')))


if __name__ == '__main__':
    unittest.main()
