"""
The option registry
"""
from dhcpkit.registry import Registry


class OptionRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Options
    """
    entry_point = 'dhcpkit.ipv6.options'


# Instantiate the option registry
option_registry = OptionRegistry()
