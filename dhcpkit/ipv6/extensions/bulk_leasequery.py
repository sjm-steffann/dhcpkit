"""
Implementation of the Bulk Leasequery protocol extension as specified in :rfc:`5460`.
"""
from struct import pack
from typing import Union

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.messages import ClientServerMessage
from dhcpkit.ipv6.options import Option

MSG_LEASEQUERY_DONE = 16
MSG_LEASEQUERY_DATA = 17

OPTION_RELAY_ID = 53

QUERY_BY_RELAY_ID = 3
QUERY_BY_LINK_ADDRESS = 4
QUERY_BY_REMOTE_ID = 5

STATUS_QUERY_TERMINATED = 11


class LeasequeryDataMessage(ClientServerMessage):
    """
    The LEASEQUERY-DATA message carries data about a single DHCPv6
    client's leases and/or PD bindings on a single link.  The purpose of
    the message is to reduce redundant data when there are multiple
    bindings to be sent.  The LEASEQUERY-DATA message MUST be preceded by
    a LEASEQUERY-REPLY message.  The LEASEQUERY-REPLY carries the query's
    status, the Leasequery's Client-ID and Server-ID options, and the
    first client's binding data if the query was successful.

    LEASEQUERY-DATA MUST ONLY be sent in response to a successful
    LEASEQUERY, and only if more than one client's data is to be sent.
    The LEASEQUERY-DATA message's transaction-id field MUST match the
    transaction-id of the LEASEQUERY request message.  The Server-ID,
    Client-ID, and OPTION_STATUS_CODE options SHOULD NOT be included:
    that data should be constant for any one Bulk Leasequery reply, and
    should have been conveyed in the LEASEQUERY-REPLY message.
    """
    message_type = MSG_LEASEQUERY_DATA
    from_server_to_client = True


class LeasequeryDoneMessage(ClientServerMessage):
    """
    The LEASEQUERY-DONE message indicates the end of a group of related
    Leasequery replies.  The LEASEQUERY-DONE message's transaction-id
    field MUST match the transaction-id of the LEASEQUERY request
    message.  The presence of the message itself signals the end of a
    stream of reply messages.  A single LEASEQUERY-DONE MUST BE sent
    after all replies (a successful LEASEQUERY-REPLY and zero or more
    LEASEQUERY-DATA messages) to a successful Bulk Leasequery request
    that returned at least one binding.

    A server may encounter an error condition after it has sent the
    initial LEASEQUERY-REPLY.  In that case, it SHOULD attempt to send a
    LEASEQUERY-DONE with an OPTION_STATUS_CODE option indicating the
    error condition to the requestor.  Other DHCPv6 options SHOULD NOT be
    included in the LEASEQUERY-DONE message.
    """
    message_type = MSG_LEASEQUERY_DONE
    from_server_to_client = True


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

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        duid_buffer = self.duid.save()
        return pack('!HH', self.option_type, len(duid_buffer)) + duid_buffer
