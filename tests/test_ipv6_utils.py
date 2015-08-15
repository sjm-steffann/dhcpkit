"""
Test the IPv6 utility functions
"""
from ipaddress import IPv6Network, IPv6Address
import unittest

from dhcpkit.ipv6.utils import address_in_prefixes, prefix_overlaps_prefixes


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


if __name__ == '__main__':
    unittest.main()
