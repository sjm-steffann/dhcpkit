from ipaddress import IPv6Address

from dhcp.ipv6.messages import Message
from dhcp.ipv6.options import Option

__all__ = ['ClientServerMessage', 'RelayServerMessage',
           'MSG_SOLICIT', 'MSG_ADVERTISE', 'MSG_REQUEST', 'MSG_CONFIRM', 'MSG_RENEW', 'MSG_REBIND', 'MSG_REPLY',
           'MSG_RELEASE', 'MSG_DECLINE', 'MSG_RECONFIGURE', 'MSG_INFORMATION_REQUEST', 'MSG_RELAY_FORW',
           'MSG_RELAY_REPL']

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


class ClientServerMessage(Message):
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
