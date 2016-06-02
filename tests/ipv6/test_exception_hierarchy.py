"""
There is not much to test with these simple exceptions. This test checks if the inheritance hierarchy is as expected.
"""
import unittest

from dhcpkit.ipv6.exceptions import InvalidPacketError


class ExceptionHierarchyTestCase(unittest.TestCase):
    def test_invalid_packet_error(self):
        with self.assertRaises(Exception):
            raise InvalidPacketError

        with self.assertRaisesRegex(InvalidPacketError, r"Invalid packet from \('2001:db8::1', 546, 0, 1\)"):
            raise InvalidPacketError(sender=('2001:db8::1', 546, 0, 1))


if __name__ == '__main__':
    unittest.main()
