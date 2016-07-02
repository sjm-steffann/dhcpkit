"""
The DUID registry
"""
from dhcpkit.registry import Registry


class DUIDRegistry(Registry):
    """
    Registry for DHCPKit IPv6 DUIDs
    """
    entry_point = 'dhcpkit.ipv6.duids'

    def get_name(self, item: object) -> str:
        """
        Get the name for the by_name mapping.

        :param item: The item to determine the name of
        :return: The name to use as key in the mapping
        """
        name = super().get_name(item)

        # Remove suffixes
        if name.endswith('-duid'):
            name = name[:-5]

        return name


# Instantiate the DUID registry
duid_registry = DUIDRegistry()
