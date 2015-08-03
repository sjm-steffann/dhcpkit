import unittest

from dhcpkit.ipv6.messages import Message
from tests import fixtures
import dhcpkit.ipv6.extensions

dhcpkit.ipv6.extensions.load_all()


class TestSolicit(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = fixtures.solicit_packet
        self.message_fixture = fixtures.solicit_message
        self.length, self.message = Message.parse(self.packet_fixture)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet_fixture))

    def test_parse(self):
        self.assertEqual(self.message, self.message_fixture)

    def test_save_parsed(self):
        self.assertEqual(self.packet_fixture, self.message.save())

    def test_save_fixture(self):
        self.assertEqual(self.packet_fixture, self.message_fixture.save())


class TestAdvertise(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = fixtures.advertise_packet
        self.message_fixture = fixtures.advertise_message
        self.length, self.message = Message.parse(self.packet_fixture)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet_fixture))

    def test_parse(self):
        self.assertEqual(self.message, self.message_fixture)

    def test_save_parsed(self):
        self.assertEqual(self.packet_fixture, self.message.save())

    def test_save_fixture(self):
        self.assertEqual(self.packet_fixture, self.message_fixture.save())


class Request(unittest.TestCase):
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


class TestReply(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = fixtures.reply_packet
        self.message_fixture = fixtures.reply_message
        self.length, self.message = Message.parse(self.packet_fixture)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet_fixture))

    def test_parse(self):
        self.assertEqual(self.message, self.message_fixture)

    def test_save_parsed(self):
        self.assertEqual(self.packet_fixture, self.message.save())

    def test_save_fixture(self):
        self.assertEqual(self.packet_fixture, self.message_fixture.save())


class TestRelayedSolicit(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = fixtures.relayed_solicit_packet
        self.message_fixture = fixtures.relayed_solicit_message
        self.length, self.message = Message.parse(self.packet_fixture)

    def test_length(self):
        self.assertEqual(self.length, len(self.packet_fixture))

    def test_parse(self):
        self.assertEqual(self.message, self.message_fixture)

    def test_save_parsed(self):
        self.assertEqual(self.packet_fixture, self.message.save())

    def test_save_fixture(self):
        self.assertEqual(self.packet_fixture, self.message_fixture.save())


class TestRelayedAdvertise(unittest.TestCase):
    def setUp(self):
        self.packet_fixture = fixtures.relayed_advertise_packet
        self.message_fixture = fixtures.relayed_advertise_message
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
