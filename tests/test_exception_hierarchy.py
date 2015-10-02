"""
There is not much to test with these simple exceptions. This test checks if the inheritance hierarchy is as expected.
"""
import unittest

from dhcpkit.ipv6.exceptions import HandlerException, CannotRespondError, UseMulticastError, ListeningSocketError, \
    InvalidPacketError


class ExceptionHierarchyTestCase(unittest.TestCase):
    def test_handler_exception(self):
        with self.assertRaises(Exception):
            raise HandlerException

        with self.assertRaises(HandlerException):
            raise HandlerException

    def test_cannot_respond_error(self):
        with self.assertRaises(Exception):
            raise CannotRespondError

        with self.assertRaises(HandlerException):
            raise CannotRespondError

        with self.assertRaises(CannotRespondError):
            raise CannotRespondError

    def test_use_multicast_error(self):
        with self.assertRaises(Exception):
            raise UseMulticastError

        with self.assertRaises(HandlerException):
            raise UseMulticastError

        with self.assertRaises(UseMulticastError):
            raise UseMulticastError

    def test_listening_socket_error(self):
        with self.assertRaises(Exception):
            raise ListeningSocketError

        with self.assertRaises(ListeningSocketError):
            raise ListeningSocketError

    def test_invalid_packet_error(self):
        with self.assertRaises(Exception):
            raise InvalidPacketError

        with self.assertRaisesRegex(InvalidPacketError, r"Invalid packet from \('2001:db8::1', 546, 0, 1\)"):
            raise InvalidPacketError(sender=('2001:db8::1', 546, 0, 1))


if __name__ == '__main__':
    unittest.main()
