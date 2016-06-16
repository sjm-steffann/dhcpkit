"""
The server extension registry
"""
from dhcpkit.registry import Registry


class ServerExtensionRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Server Extensions
    """
    entry_point = 'dhcpkit.ipv6.server.extensions'


# Instantiate the extension registry
server_extension_registry = ServerExtensionRegistry()
