"""
The registry that keeps track of which class implements which message type
"""

__all__ = ['registry', 'register']

# Registry
# type: Dict[int, Message]
registry = {}


def register(message_type: int, subclass: type) -> None:
    """
    Register a new message type in the message registry.

    :param message_type: The type code for this message
    :param subclass: A subclass of Message that implements the message
    """
    from dhcp.ipv6.messages import Message

    if not issubclass(subclass, Message):
        raise TypeError('Only Messages can be registered')

    registry[message_type] = subclass
