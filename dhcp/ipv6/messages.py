from ipaddress import IPv6Address

from dhcp.ipv6 import message_registry
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
    # These needs to be overwritten in subclasses
    message_type = 0
    from_client_to_server = False
    from_server_to_client = False

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        """
        Return the appropriate subclass from the registry, or UnknownClientServerMessage if no subclass is registered.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :return: The best known class for this message data
        """
        message_type = buffer[offset]
        return message_registry.registry.get(message_type, UnknownClientServerMessage)


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

    def __init__(self, transaction_id: bytes=b'\x00\x00\x00', options: []=None):
        super().__init__()
        self.transaction_id = transaction_id
        self.options = options or []

    def validate(self):
        # Check if all options are allowed
        self.validate_contains(self.options)

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        # These message types always begin with a message type and a transaction id
        message_type = buffer[offset + my_offset]
        my_offset += 1

        if message_type != self.message_type:
            raise ValueError('The provided buffer does not contain {} data'.format(self.__class__.__name__))

        self.transaction_id = buffer[offset + my_offset:offset + my_offset + 3]
        my_offset += 3

        # Parse the options
        from dhcp.ipv6.options import Option

        max_length = length or (len(buffer) - offset)
        while max_length > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)

            self.options.append(option)
            my_offset += used_buffer

        self.validate()

        return my_offset

    def save(self) -> bytes:
        self.validate()

        buffer = bytearray()
        buffer.append(self.message_type)
        buffer.extend(self.transaction_id)
        for option in self.options:
            buffer.extend(option.save())
        return buffer


class UnknownClientServerMessage(ClientServerMessage):
    may_contain_anything = True

    def __init__(self, message_type: int=0, transaction_id: bytes=b'\x00\x00\x00', options: []=None):
        self.message_type = message_type
        super().__init__(transaction_id, options)

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        # Set our own message type by peeking at the next byte, and then parse
        self.message_type = buffer[offset]
        return super().load_from(buffer, offset, length)


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

    def __init__(self, hop_count: int=0, link_address: IPv6Address=None, peer_address: IPv6Address=None,
                 options: []=None):
        super().__init__()
        self.hop_count = hop_count
        self.link_address = link_address
        self.peer_address = peer_address
        self.options = options or []

    def validate(self):
        # Check if all options are allowed
        self.validate_contains(self.options)

    @property
    def relayed_message(self) -> Message or None:
        from dhcp.ipv6.options import RelayMessageOption

        for option in self.options:
            if isinstance(option, RelayMessageOption):
                return option.relayed_message

        # No embedded message found
        return None

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

        self.validate()

        return my_offset

    def save(self) -> bytes:
        self.validate()

        buffer = bytearray()
        buffer.append(self.message_type)
        buffer.append(self.hop_count)
        buffer.extend(self.link_address.packed)
        buffer.extend(self.peer_address.packed)
        for option in self.options:
            buffer.extend(option.save())
        return buffer


class SolicitMessage(ClientServerMessage):
    message_type = MSG_SOLICIT
    from_client_to_server = True


class AdvertiseMessage(ClientServerMessage):
    message_type = MSG_ADVERTISE
    from_server_to_client = True


class RequestMessage(ClientServerMessage):
    message_type = MSG_REQUEST
    from_client_to_server = True


class ConfirmMessage(ClientServerMessage):
    message_type = MSG_CONFIRM
    from_client_to_server = True


class RenewMessage(ClientServerMessage):
    message_type = MSG_RENEW
    from_client_to_server = True


class RebindMessage(ClientServerMessage):
    message_type = MSG_REBIND
    from_client_to_server = True


class ReplyMessage(ClientServerMessage):
    message_type = MSG_REPLY
    from_server_to_client = True


class ReleaseMessage(ClientServerMessage):
    message_type = MSG_RELEASE
    from_client_to_server = True


class DeclineMessage(ClientServerMessage):
    message_type = MSG_DECLINE
    from_client_to_server = True


class ReconfigureMessage(ClientServerMessage):
    message_type = MSG_RECONFIGURE
    from_server_to_client = True


class InformationRequestMessage(ClientServerMessage):
    message_type = MSG_INFORMATION_REQUEST
    from_client_to_server = True


class RelayForwardMessage(RelayServerMessage):
    message_type = MSG_RELAY_FORW
    from_client_to_server = True

    def wrap_response(self, message: Message) -> Message:
        response = RelayReplyMessage(self.hop_count, self.link_address, self.peer_address)
        for option in self.options:
            # Let each option create its own reply, if any
            reply_option = option.create_option_for_reply(self, message)
            if reply_option:
                response.options.append(reply_option)

        return response


class RelayReplyMessage(RelayServerMessage):
    message_type = MSG_RELAY_REPL
    from_server_to_client = True

# Register the classes in this file
message_registry.register(MSG_SOLICIT, SolicitMessage)
message_registry.register(MSG_ADVERTISE, AdvertiseMessage)
message_registry.register(MSG_REQUEST, RequestMessage)
message_registry.register(MSG_CONFIRM, ConfirmMessage)
message_registry.register(MSG_RENEW, RenewMessage)
message_registry.register(MSG_REBIND, RebindMessage)
message_registry.register(MSG_REPLY, ReplyMessage)
message_registry.register(MSG_RELEASE, ReleaseMessage)
message_registry.register(MSG_DECLINE, DeclineMessage)
message_registry.register(MSG_RECONFIGURE, ReconfigureMessage)
message_registry.register(MSG_INFORMATION_REQUEST, InformationRequestMessage)
message_registry.register(MSG_RELAY_FORW, RelayForwardMessage)
message_registry.register(MSG_RELAY_REPL, RelayReplyMessage)
