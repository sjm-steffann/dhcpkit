"""
The option registry
"""
from dhcpkit.registry import Registry


class MessageRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Options
    """
    entry_point = 'dhcpkit.ipv6.messages'

    def get_name(self, item: object) -> str:
        """
        Get the name for the by_name mapping.

        :param item: The item to determine the name of
        :return: The name to use as key in the mapping
        """
        name = super().get_name(item)

        # Remove suffixes
        if name.endswith('-message'):
            name = name[:-8]

        return name


# Instantiate the option registry
message_registry = MessageRegistry()
