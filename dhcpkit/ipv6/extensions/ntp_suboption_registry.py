"""
The NTP suboption registry
"""
from dhcpkit.registry import Registry


class NTPSuboptionRegistry(Registry):
    """
    Registry for NTP Suboptions
    """
    entry_point = 'dhcpkit.ipv6.options.ntp.suboptions'

    def get_name(self, item: object) -> str:
        """
        Get the name for the by_name mapping.

        :param item: The item to determine the name of
        :return: The name to use as key in the mapping
        """
        name = super().get_name(item)

        # Remove prefixes and suffixes
        if name.startswith('ntp-'):
            name = name[4:]
        if name.endswith('-sub-option'):
            name = name[:-11]

        return name


# Instantiate the suboption registry
ntp_suboption_registry = NTPSuboptionRegistry()
