"""
The option registry
"""
from dhcpkit.registry import Registry


class MessageRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Options
    """
    entry_point = 'dhcpkit.ipv6.messages'


# Instantiate the option registry
message_registry = MessageRegistry()
