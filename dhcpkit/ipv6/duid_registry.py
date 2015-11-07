"""
The DUID registry
"""
from dhcpkit.registry import Registry


class DUIDRegistry(Registry):
    """
    Registry for DHCPKit IPv6 DUIDs
    """
    entry_point = 'dhcpkit.ipv6.duids'


# Instantiate the DUID registry
duid_registry = DUIDRegistry()
