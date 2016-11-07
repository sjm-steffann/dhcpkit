"""
Implementation of the Bulk Leasequery protocol extension as specified in :rfc:`5460`.
"""
from struct import pack

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.options import Option

OPTION_RELAY_ID = 53

QUERY_BY_RELAY_ID = 3
QUERY_BY_LINK_ADDRESS = 4
QUERY_BY_REMOTE_ID = 5

STATUS_QUERY_TERMINATED = 11


class RelayIdOption(Option):
    """
    :rfc:`5460#section-5.4.1`

    The Relay-ID option carries a DUID [RFC3315].  A relay agent MAY
    include the option in Relay-Forward messages it sends.  Obviously, it
    will not be possible for a server to respond to QUERY_BY_RELAY_ID
    queries unless the relay agent has included this option.  A relay
    SHOULD be able to generate a DUID for this purpose, and capture the
    result in stable storage.  A relay SHOULD also allow the DUID value
    to be configurable: doing so allows an administrator to replace a
    relay agent while retaining the association between the relay and
    existing DHCPv6 bindings.

    A DHCPv6 server MAY associate Relay-ID options from Relay-Forward
    messages it processes with prefix delegations and/or lease bindings
    that result.  Doing so allows it to respond to QUERY_BY_RELAY_ID
    Leasequeries.

    The format of the Relay-ID option is shown below:

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |       OPTION_RELAY_ID         |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                              DUID                             .
      .                        (variable length)                      .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_RELAY_ID (53).

    option-len
        Length of DUID in octets.

    DUID
        The DUID for the relay agent.

    :type duid: DUID
    """

    option_type = OPTION_RELAY_ID

    def __init__(self, duid: DUID = None):
        self.duid = duid
        """The DUID of the relay agent"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.duid, DUID):
            raise ValueError("DUID is not a DUID object")

        self.duid.validate()

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=2)

        duid_len, self.duid = DUID.parse(buffer, offset=offset + my_offset, length=option_len)
        my_offset += duid_len

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        duid_buffer = self.duid.save()
        return pack('!HH', self.option_type, len(duid_buffer)) + duid_buffer
