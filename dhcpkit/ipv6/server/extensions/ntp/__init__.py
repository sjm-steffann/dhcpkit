"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.ntp
"""
from typing import List

from dhcpkit.ipv6.extensions.ntp import NTPSubOption, NTPServersOption
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler


class NTPServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, sub_options: [NTPSubOption]):
        option = NTPServersOption(options=sub_options)
        option.validate()

        super().__init__(option)

    def combine(self, existing_options: List[NTPServersOption]) -> NTPServersOption:
        """
        Combine multiple options into one.

        :param existing_options: The existing options to include NTP servers from
        :return: The combined option
        """
        sub_options = []

        # Add from existing options first
        for option in existing_options:
            for sub_option in option.options:
                if sub_option not in sub_options:
                    sub_options.append(sub_option)

        # Then add our own
        for sub_option in self.option.dns_servers:
            if sub_option not in sub_options:
                sub_options.append(sub_option)

        # And return a new option with the combined addresses
        return NTPServersOption(options=sub_options)
