"""
Test the RelayMessageOption implementation
"""
import unittest

from dhcpkit.ipv6.message_registry import message_registry
from dhcpkit.ipv6.messages import UnknownMessage, ClientServerMessage
from dhcpkit.ipv6.options import RelayMessageOption
from tests.ipv6.options import test_option


# A dummy option that may not be in a RelayMessageOption
class NonRelayableMessage(UnknownMessage):
    pass


# Add the constraint to disallow putting it in a RelayMessageOption
RelayMessageOption.add_may_contain(NonRelayableMessage, max_occurrence=0)


# A dummy message that has the wrong length
class WeirdLengthMessage(ClientServerMessage):
    message_type = 254

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None):
        return 4


class RelayMessageOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00090017ff') + b'ThisIsAnUnknownMessage'
        self.option_object = RelayMessageOption(relayed_message=UnknownMessage(255, b'ThisIsAnUnknownMessage'))
        self.parse_option()

    def test_validate_relayed_message(self):
        self.option.relayed_message = None
        with self.assertRaisesRegex(ValueError, 'IPv6 DHCP message'):
            self.option.validate()

        self.option.relayed_message = NonRelayableMessage(255, b'ThisIsAnUnknownMessage')
        with self.assertRaisesRegex(ValueError, 'cannot contain'):
            self.option.validate()

    def test_bad_message_length(self):
        # Add a fake message type to the registry
        message_registry[254] = WeirdLengthMessage

        with self.assertRaisesRegex(ValueError, 'different length'):
            RelayMessageOption.parse(bytes.fromhex('00090006fe1234567890'))

        # And clean it up again
        del message_registry[254]


if __name__ == '__main__':
    unittest.main()
