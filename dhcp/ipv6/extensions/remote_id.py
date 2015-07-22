"""
Classes and constants for the options defined in http://www.iana.org/go/rfc4649
"""

from struct import pack, unpack_from

from dhcp.ipv6 import option_registry
from dhcp.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcp.ipv6.options import Option

OPTION_REMOTE_ID = 37


class RemoteIdOption(Option):
    """
    http://tools.ietf.org/html/rfc4649#section-3

    This option may be added by DHCPv6 relay agents that terminate
    switched or permanent circuits and have mechanisms to identify the
    remote host end of the circuit.

    The format of the DHCPv6 Relay Agent Remote-ID option is shown below:

        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |       OPTION_REMOTE_ID        |         option-len            |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                       enterprise-number                       |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       .                                                               .
       .                           remote-id                           .
       .                                                               .
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

       option-code        OPTION_REMOTE_ID (37)

       option-len         4 + the length, in octets, of the remote-id
                          field.  The minimum option-len is 5 octets.

       enterprise-number  The vendor's registered Enterprise Number as
                          registered with IANA [5].

       remote-id          The opaque value for the remote-id.

    The definition of the remote-id carried in this option is vendor
    specific.  The vendor is indicated in the enterprise-number field.
    The remote-id field may be used to encode, for instance:

    o  a "caller ID" telephone number for dial-up connection
    o  a "user name" prompted for by a Remote Access Server
    o  a remote caller ATM address
    o  a "modem ID" of a cable data modem
    o  the remote IP address of a point-to-point link
    o  a remote X.25 address for X.25 connections
    o  an interface or port identifier

    Each vendor must ensure that the remote-id is unique for its
    enterprise-number, as the octet sequence of enterprise-number
    followed by remote-id must be globally unique.  One way to achieve
    uniqueness might be to include the relay agent's DHCP Unique
    Identifier (DUID) [1] in the remote-id.

    :type enterprise_number: int
    :type remote_id: bytes
    """

    option_type = OPTION_REMOTE_ID

    def __init__(self, enterprise_number: int=0, remote_id: bytes=b''):
        self.enterprise_number = enterprise_number
        self.remote_id = remote_id

    # noinspection PyDocstring
    def validate(self):
        if not isinstance(self.enterprise_number, int) or not (0 <= self.enterprise_number < 2 ** 32):
            raise ValueError("Enterprise number must be an unsigned 32 bit integer")

        if not isinstance(self.remote_id, bytes) or len(self.remote_id) >= 2 ** 16:
            raise ValueError("Remote-ID must be bytes")

    # noinspection PyDocstring
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        self.enterprise_number = unpack_from('!I', buffer, offset=offset + my_offset)[0]
        my_offset += 4

        remote_id_length = option_len - 4
        self.remote_id = buffer[offset + my_offset:offset + my_offset + remote_id_length]
        my_offset += remote_id_length

        self.validate()

        return my_offset

    # noinspection PyDocstring
    def save(self) -> bytes:
        self.validate()
        return pack('!HHI', self.option_type, len(self.remote_id) + 4, self.enterprise_number) + self.remote_id


option_registry.register(RemoteIdOption)

RelayForwardMessage.add_may_contain(RemoteIdOption)

# The RFC says there is no requirement for servers to include this option in replies, but it is not forbidden
RelayReplyMessage.add_may_contain(RemoteIdOption)
