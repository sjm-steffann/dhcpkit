from ipaddress import IPv6Address

from dhcp.parsing import StructuredElement

MSG_SOLICIT = 1
MSG_ADVERTISE = 2
MSG_REQUEST = 3
MSG_CONFIRM = 4
MSG_RENEW = 5
MSG_REBIND = 6
MSG_REPLY = 7
MSG_RELEASE = 8
MSG_DECLINE = 9
MSG_RECONFIGURE = 10
MSG_INFORMATION_REQUEST = 11
MSG_RELAY_FORW = 12
MSG_RELAY_REPL = 13


# This subclass remains abstract
# noinspection PyAbstractClass
class Message(StructuredElement):
    def __init__(self):
        # The DHCP message type
        self.message_type = 0  # type: int

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        # Look at the first byte of the buffer: it should be the message type
        message_type = buffer[offset]

        if message_type in (MSG_RELAY_FORW, MSG_RELAY_REPL):
            # These two are special and have a different format
            subclass = RelayServerMessage
        else:
            # All other types have a standard structure
            subclass = ClientServerMessage

        # Prevent loops if subclasses don't implement their own version of this method
        if cls == subclass:
            return subclass

        # Otherwise delegate
        return subclass.determine_class(buffer, offset=offset)


class ClientServerMessage(Message):
    """
    https://tools.ietf.org/html/rfc3315#section-6

    All DHCP messages sent between clients and servers share an identical
    fixed format header and a variable format area for options.

    All values in the message header and in options are in network byte
    order.

    Options are stored serially in the options field, with no padding
    between the options.  Options are byte-aligned but are not aligned in
    any other way such as on 2 or 4 byte boundaries.

    The following diagram illustrates the format of DHCP messages sent
    between clients and servers:

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    msg-type   |               transaction-id                  |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .                            options                            .
      .                           (variable)                          .
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      msg-type             Identifies the DHCP message type; the
                           available message types are listed in
                           section 5.3.

      transaction-id       The transaction ID for this message exchange.

      options              Options carried in this message; options are
                           described in section 22.
    """

    def __init__(self, message_type: int=0, transaction_id: bytes=b'\x00\x00\x00', options: []=None):
        super().__init__()
        self.message_type = message_type
        self.transaction_id = transaction_id
        self.options = options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        # These message types always begin with a message type and a transaction id
        self.message_type = buffer[offset + my_offset]
        my_offset += 1

        self.transaction_id = buffer[offset + my_offset:offset + my_offset + 3]
        my_offset += 3

        # Parse the options
        from dhcp.ipv6.options import Option

        max_length = length or (len(buffer) - offset)
        while max_length > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        return my_offset

    def save(self) -> bytes:
        buffer = bytearray()
        buffer.append(self.message_type)
        buffer.extend(self.transaction_id)
        for option in self.options:
            buffer.extend(option.save())
        return buffer


class RelayServerMessage(Message):
    """
    https://tools.ietf.org/html/rfc3315#section-7

    Relay agents exchange messages with servers to relay messages between
    clients and servers that are not connected to the same link.

    All values in the message header and in options are in network byte
    order.

    Options are stored serially in the options field, with no padding
    between the options.  Options are byte-aligned but are not aligned in
    any other way such as on 2 or 4 byte boundaries.

    There are two relay agent messages, which share the following format:

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    msg-type   |   hop-count   |                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
      |                                                               |
      |                         link-address                          |
      |                                                               |
      |                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-|
      |                               |                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
      |                                                               |
      |                         peer-address                          |
      |                                                               |
      |                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-|
      |                               |                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
      .                                                               .
      .            options (variable number and length)   ....        .
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    The following sections describe the use of the Relay Agent message
    header.
    """

    def __init__(self, message_type: int=0, hop_count: int=0,
                 link_address: IPv6Address=None, peer_address: IPv6Address=None, options: []=None):
        super().__init__()
        self.message_type = message_type
        self.hop_count = hop_count
        self.link_address = link_address
        self.peer_address = peer_address
        self.options = options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        # These message types always begin with a message type, a hop count, the link address and the peer address
        self.message_type = buffer[offset + my_offset]
        my_offset += 1

        self.hop_count = buffer[offset + my_offset]
        my_offset += 1

        self.link_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        self.peer_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        # Parse the options
        from dhcp.ipv6.options import Option

        max_length = length or (len(buffer) - offset)
        while max_length > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        return my_offset

    def save(self) -> bytes:
        buffer = bytearray()
        buffer.append(self.message_type)
        buffer.append(self.hop_count)
        buffer.extend(self.link_address.packed)
        buffer.extend(self.peer_address.packed)
        for option in self.options:
            buffer.extend(option.save())
        return buffer
