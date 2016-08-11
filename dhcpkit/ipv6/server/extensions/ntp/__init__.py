"""
Handlers for the options defined in dhcpkit.ipv6.extensions.ntp
"""
from dhcpkit.ipv6.extensions.ntp import NTPServersOption, NTPSubOption
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler
from typing import Iterable


class NTPServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting NTPServersOption in responses
    """

    def __init__(self, sub_options: Iterable[NTPSubOption], always_send: bool = False):
        option = NTPServersOption(options=sub_options)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, ', '.join([option.value for option in self.option.options]))

    def combine(self, existing_options: Iterable[NTPServersOption]) -> NTPServersOption:
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
