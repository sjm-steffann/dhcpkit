"""
The option registry
"""
from dhcpkit.registry import Registry


class OptionRegistry(Registry):
    """
    Registry for DHCPKit IPv6 Options
    """
    entry_point = 'dhcpkit.ipv6.options'

    def get_name(self, item: object) -> str:
        """
        Get the name for the by_name mapping.

        :param item: The item to determine the name of
        :return: The name to use as key in the mapping
        """
        name = super().get_name(item)

        # Remove suffixes
        if name.endswith('-option'):
            name = name[:-7]

        return name


# Instantiate the option registry
option_registry = OptionRegistry()
