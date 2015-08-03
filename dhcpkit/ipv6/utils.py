"""
Utility functions for IPv6 DHCP
"""
from ipaddress import IPv6Address, IPv6Network


def address_in_prefixes(address: IPv6Address, prefixes: [IPv6Network]) -> bool:
    """
    Check whether the given address is part of one of the given prefixes

    :param address: The IPv6 address to check
    :param prefixes: The list of IPv6 prefixes
    :type prefixes: list[IPv6Network]
    :return: Whether the address is part of one of the prefixes
    """
    for prefix in prefixes:
        if address in prefix:
            return True

    return False


def prefix_overlaps_prefixes(prefix: IPv6Network, prefixes: [IPv6Network]) -> bool:
    """
    Check whether the given address is part of one of the given prefixes

    :param prefix: The IPv6 prefix to check
    :param prefixes: The list of IPv6 prefixes
    :type prefixes: list[IPv6Network]
    :return: Whether the address is part of one of the prefixes
    """
    for other_prefix in prefixes:
        if prefix.overlaps(other_prefix):
            return True

    return False
