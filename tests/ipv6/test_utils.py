"""
Test the IPv6 utility functions
"""
import unittest
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.utils import address_in_prefixes, is_global_unicast, prefix_overlaps_prefixes


class IPv6UtilsTestCase(unittest.TestCase):
    def test_address_in_prefixes(self):
        prefixes = [IPv6Network('2001:db8::/48'), IPv6Network('2001:db8:1:2::/64')]
        good_address = IPv6Address('2001:db8::1')
        bad_address = IPv6Address('2001:db8:1::1')

        self.assertTrue(address_in_prefixes(good_address, prefixes))
        self.assertFalse(address_in_prefixes(bad_address, prefixes))

    def test_prefix_overlaps_prefixes(self):
        prefixes = [IPv6Network('2001:db8::/48'), IPv6Network('2001:db8:1:2::/64')]
        good_prefix = IPv6Network('2001:db8::/64')
        bad_prefix = IPv6Network('2001:db8:1::/64')

        self.assertTrue(prefix_overlaps_prefixes(good_prefix, prefixes))
        self.assertFalse(prefix_overlaps_prefixes(bad_prefix, prefixes))

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
