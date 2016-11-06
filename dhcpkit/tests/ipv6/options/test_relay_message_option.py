"""
Test the RelayMessageOption implementation
"""
import unittest

from dhcpkit.ipv6.message_registry import message_registry
from dhcpkit.ipv6.messages import ClientServerMessage, UnknownMessage
from dhcpkit.ipv6.options import RelayMessageOption
from dhcpkit.tests.ipv6.options import test_option


# A dummy option that may not be in a RelayMessageOption
class NonRelayableMessage(UnknownMessage):
    """
    A message that can not be relayed
    """
    pass


# Add the constraint to disallow putting it in a RelayMessageOption
RelayMessageOption.add_may_contain(NonRelayableMessage, max_occurrence=0)


# A dummy message that has the wrong length
class WeirdLengthMessage(ClientServerMessage):
    """
    An option that returns an incorrect length, to test error handling
    """
    message_type = 254

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None):
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
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
