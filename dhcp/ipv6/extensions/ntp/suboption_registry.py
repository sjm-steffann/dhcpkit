"""
The registry that keeps track of which class implements which NTP suboption type
"""

__all__ = ['registry', 'register']

# Registry
# type: Dict[int, NTPSubOption]
registry = {}


def register(option_code: int, subclass: type) -> None:
    """
    Register a new option type in the option registry.

    :param option_code: The code for this option
    :param subclass: A subclass of Option that implements the option
    """
    from dhcp.ipv6.extensions.ntp.suboptions import NTPSubOption

    if not issubclass(subclass, NTPSubOption):
        raise TypeError('Only NTPSubOptions can be registered')

    registry[option_code] = subclass
