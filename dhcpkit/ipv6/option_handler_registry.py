"""
The option handler registry
"""
from dhcpkit.registry import Registry


class OptionHandlerRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Option Handlers
    """
    entry_point = 'dhcpkit.ipv6.option_handlers'


# Instantiate the option handler registry
option_handler_registry = OptionHandlerRegistry()
