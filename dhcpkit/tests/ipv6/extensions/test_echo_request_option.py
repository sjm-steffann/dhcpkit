"""
Test the EchoRequestOption implementation
"""
import unittest

from dhcpkit.ipv6.extensions.linklayer_id import OPTION_CLIENT_LINKLAYER_ADDR
from dhcpkit.ipv6.extensions.relay_echo_request import EchoRequestOption
from dhcpkit.ipv6.extensions.remote_id import OPTION_REMOTE_ID
from dhcpkit.ipv6.extensions.subscriber_id import OPTION_SUBSCRIBER_ID
from dhcpkit.protocol_element import ElementDataRepresentation
from dhcpkit.tests.ipv6.options import test_option


class EchoRequestOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('002b0006004f0026ffff')
        self.option_object = EchoRequestOption(requested_options=[OPTION_CLIENT_LINKLAYER_ADDR,
                                                                  OPTION_SUBSCRIBER_ID,
                                                                  65535])
        self.parse_option()

    def test_validate_requested_options(self):
        self.option.requested_options = 65535
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            self.option.validate()

        self.option.requested_options = [OPTION_SUBSCRIBER_ID, 0, OPTION_REMOTE_ID]
        self.option.validate()

        self.option.requested_options = [OPTION_SUBSCRIBER_ID, -1, OPTION_REMOTE_ID]
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

        self.option.requested_options = [OPTION_SUBSCRIBER_ID, 65535, OPTION_REMOTE_ID]
        self.option.validate()

        self.option.requested_options = [OPTION_SUBSCRIBER_ID, 65536, OPTION_REMOTE_ID]
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            self.option.validate()

    def test_display_requested_options(self):
        elements = self.option.display_requested_options()
        self.assertIsInstance(elements, list)

        for element in elements:
            self.assertIsInstance(element, ElementDataRepresentation)

        representation = [str(element) for element in elements]
        self.assertRegex(representation[0], r' \(79\)$')
        self.assertRegex(representation[1], r' \(38\)$')
        self.assertRegex(representation[2], r' \(65535\)$')

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'Invalid option length'):
            EchoRequestOption.parse(bytes.fromhex('002b000300030004'))


if __name__ == '__main__':
    unittest.main()
