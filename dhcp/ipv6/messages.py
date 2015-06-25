from ipaddress import IPv6Address

from dhcp.parsing import StructuredElement


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

        from dhcp.ipv6.rfc3315.messages import MSG_RELAY_FORW, MSG_RELAY_REPL, RelayServerMessage, ClientServerMessage

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
