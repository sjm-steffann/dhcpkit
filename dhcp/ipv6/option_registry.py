"""
The registry that keeps track of which class implements which option type
"""

__all__ = ['registry', 'register']

# Registry
# type: Dict[int, Option]
registry = {}


def register(option_code: int, subclass: type) -> None:
    """
    Register a new option type in the option registry.

    :param option_code: The code for this option
    :param subclass: A subclass of Option that implements the option
    """
    from dhcp.ipv6.options import Option

    if not issubclass(subclass, Option):
        raise TypeError('Only Options can be registered')

    registry[option_code] = subclass
