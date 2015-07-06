"""
The registry that keeps track of which class implements which NTP suboption type
"""

# Registry
# type: {int: Option}
registry = {}

# Name Registry
# type: {str: Option}
name_registry = {}


def register(subclass: type) -> None:
    """
    Register a new option type in the option registry.

    :param subclass: A subclass of Option that implements the option
    """
    from dhcp.ipv6.extensions.ntp.suboptions import NTPSubOption
    from dhcp.utils import camelcase_to_underscore

    if not issubclass(subclass, NTPSubOption):
        raise TypeError('Only NTPSubOptions can be registered')

    # Store based on number
    # noinspection PyUnresolvedReferences
    registry[subclass.suboption_type] = subclass

    # Store based on name
    name = subclass.__name__
    if name.endswith('Message'):
        name = name[:-6]
    name = camelcase_to_underscore(name)
    name_registry[name] = subclass
