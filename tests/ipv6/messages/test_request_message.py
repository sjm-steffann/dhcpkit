"""
Test the RequestMessage implementation
"""
import unittest

from dhcpkit.ipv6.messages import Message
import dhcpkit.ipv6.extensions
from tests.ipv6 import fixtures

dhcpkit.ipv6.extensions.load_all()


class RequestTestCase(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = fixtures.request_packet
        self.message_fixture = fixtures.request_message
        self.length, self.message = Message.parse(self.packet_fixture)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet_fixture))

    def test_parse(self):
        self.assertEqual(self.message, self.message_fixture)

    def test_save_parsed(self):
        self.assertEqual(self.packet_fixture, self.message.save())

    def test_save_fixture(self):
        self.assertEqual(self.packet_fixture, self.message_fixture.save())


if __name__ == '__main__':
    unittest.main()
