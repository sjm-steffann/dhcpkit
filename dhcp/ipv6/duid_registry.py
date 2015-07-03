"""
The registry that keeps track of which class implements which DUID type
"""

__all__ = ['registry', 'register']

# Registry
# type: Dict[int, DUID]
registry = {}


def register(duid_type: int, subclass: type) -> None:
    """
    Register a new option type in the option registry.

    :param duid_type: The code for this option
    :param subclass: A subclass of Option that implements the option
    """
    from dhcp.ipv6.duids import DUID

    if not issubclass(subclass, DUID):
        raise TypeError('Only DUIDs can be registered')

    registry[duid_type] = subclass
