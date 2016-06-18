"""
Utility functions for IPv6 DHCP
"""
from ipaddress import IPv6Address, IPv6Network


def is_global_unicast(address: IPv6Address) -> bool:
    """
    Check if an address is a global unicast address according to :rfc:`4291`.

    :param address: The address to check
    :return: Whether it is a global unicast address
    """
    return not (address == IPv6Address('::') or
                address == IPv6Address('::1') or
                address in IPv6Network('ff00::/8') or
                address in IPv6Network('fe80::/10'))
