"""
Test the UnknownMessage implementation
"""
import unittest

from dhcpkit.ipv6.messages import UnknownMessage
from tests.ipv6.messages import test_message

unknown_message = UnknownMessage(255, b'ThisIsAnUnknownMessage')
unknown_packet = bytes.fromhex('ff') + b'ThisIsAnUnknownMessage'


class UnknownMessageTestCase(test_message.MessageTestCase):
    def setUp(self):
        self.packet_fixture = unknown_packet
        self.message_fixture = unknown_message
        self.parse_packet()

    def parse_packet(self):
        super().parse_packet()
        self.assertIsInstance(self.message, UnknownMessage)

    def test_validate_message_type(self):
        # This should be ok
        self.message.message_type = 0
        self.message.validate()

        # This shouldn't
        self.message.message_type = -1
        with self.assertRaisesRegex(ValueError, 'unsigned 8 bit integer'):
            self.message.validate()

        # This should be ok
        self.message.message_type = 255
        self.message.validate()

        # This shouldn't
        self.message.message_type = 256
        with self.assertRaisesRegex(ValueError, 'unsigned 8 bit integer'):
            self.message.validate()

    def test_validate_data(self):
        # This should be ok
        self.message.message_data = b''
        self.message.validate()

        # This shouldn't
        self.message.message_data = ''
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            self.message.validate()


if __name__ == '__main__':
    unittest.main()
