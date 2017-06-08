"""
Implementation of Subscriber-ID option as specified in :rfc:`4580`.
"""

from struct import pack
from typing import Union

from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.options import Option

OPTION_SUBSCRIBER_ID = 38


class SubscriberIdOption(Option):
    """
    :rfc:`4580#section-2`

    The subscriber-id information allows the service provider to assign/
    activate subscriber-specific actions; e.g., assignment of specific IP
    addresses, prefixes, DNS configuration, trigger accounting, etc.
    This option is de-coupled from the access network's physical
    structure, so a subscriber that moves from one access-point to
    another, for example, would not require reconfiguration at the
    service provider's DHCPv6 servers.

    The subscriber-id information is only intended for use within a
    single administrative domain and is only exchanged between the relay
    agents and DHCPv6 servers within that domain.  Therefore, the format
    and encoding of the data in the option is not standardized, and this
    specification does not establish any semantic requirements on the
    data.  This specification only defines the option for conveying this
    information from relay agents to DHCPv6 servers.

    However, as the DHCPv4 Subscriber-ID suboption [3] specifies Network
    Virtual Terminal (NVT) American Standard Code for Information
    Interchange (ASCII) [4] encoded data, in environments where both
    DHCPv4 [5] and DHCPv6 are being used, it may be beneficial to use
    that encoding.

    The format of the DHCPv6 Relay Agent Subscriber-ID option is shown
    below:

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |     OPTION_SUBSCRIBER_ID      |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                         subscriber-id                         .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_SUBSCRIBER_ID (38)

    option-len
        length, in octets, of the subscriber-id field.
        The minimum length is 1 octet.

    subscriber-id
        The subscriber's identity.

    """

    option_type = OPTION_SUBSCRIBER_ID

    def __init__(self, subscriber_id: bytes = b''):
        self.subscriber_id = subscriber_id
        """The subscriber-id as bytes"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.subscriber_id, bytes):
            raise ValueError("Subscriber-ID must be sequence of bytes")

        if len(self.subscriber_id) > (2 ** 16 - 1):
            raise ValueError("Subscriber-ID cannot be longer than {} bytes".format(2 ** 16 - 1))

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        self.subscriber_id = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HH', self.option_type, len(self.subscriber_id)) + self.subscriber_id


RelayForwardMessage.add_may_contain(SubscriberIdOption)

# The RFC says there is no requirement for servers to include this option in replies, but it is not forbidden
RelayReplyMessage.add_may_contain(SubscriberIdOption)
