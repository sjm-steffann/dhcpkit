"""
The registry that keeps track of which class implements which message type
"""

# Registry
# type: {int: Option}
registry = {}

# Name Registry
# type: {str: Option}
name_registry = {}


def register(subclass: type):
    """
    Register a new message type in the message registry.

    :param subclass: A subclass of Message that implements the message
    """
    from dhcpkit.ipv6.messages import Message
    from dhcpkit.utils import camelcase_to_dash

    if not issubclass(subclass, Message):
        raise TypeError('Only Messages can be registered')

    # Store based on number
    # noinspection PyUnresolvedReferences
    registry[subclass.message_type] = subclass

    # Store based on name
    name = subclass.__name__
    if name.endswith('Message'):
        name = name[:-7]
    name = camelcase_to_dash(name)
    name_registry[name] = subclass
