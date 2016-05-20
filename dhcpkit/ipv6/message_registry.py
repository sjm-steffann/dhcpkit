"""
The message type registry
"""
from dhcpkit.registry import Registry


class MessageRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Message types
    """
    entry_point = 'dhcpkit.ipv6.messages'


# Instantiate the message type registry
message_registry = MessageRegistry()
