"""
The registry that keeps track of which class implements which DUID type
"""

# Registry
# type: {int: Option}
registry = {}

# Name Registry
# type: {str: Option}
name_registry = {}


def register(subclass: type) -> None:
    """
    Register a new message type in the message registry.

    :param subclass: A subclass of Message that implements the message
    """
    from dhcp.ipv6.duids import DUID
    from dhcp.utils import camelcase_to_dash

    if not issubclass(subclass, DUID):
        raise TypeError('Only DUIDs can be registered')

    # Store based on number
    # noinspection PyUnresolvedReferences
    registry[subclass.duid_type] = subclass

    # Store based on name
    name = subclass.__name__
    if name.endswith('DUID'):
        name = name[:-4]
    name = camelcase_to_dash(name)
    name_registry[name] = subclass
