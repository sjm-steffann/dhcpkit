"""
The NTP suboption registry
"""
from dhcpkit.registry import Registry


class NTPSuboptionRegistry(Registry):
    """
    Registry for NTP Suboptions
    """
    entry_point = 'dhcpkit.ipv6.options.ntp.suboptions'


# Instantiate the suboption registry
ntp_suboption_registry = NTPSuboptionRegistry()
