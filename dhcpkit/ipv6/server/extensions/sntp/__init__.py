"""
Handlers for the options defined in dhcpkit.ipv6.extensions.sntp
"""

from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.sntp import SNTPServersOption
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler
from typing import Iterable


class SNTPServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting SNTPServersOptions in responses
    """

    def __init__(self, sntp_servers: Iterable[IPv6Address], always_send: bool = False):
        option = SNTPServersOption(sntp_servers=sntp_servers)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, ', '.join(map(str, self.option.sntp_servers)))

    def combine(self, existing_options: Iterable[SNTPServersOption]) -> SNTPServersOption:
        """
        Combine multiple options into one.

        :param existing_options: The existing options to include NTP servers from
        :return: The combined option
        """
        sntp_servers = []

        # Add from existing options first
        for option in existing_options:
            for sntp_server in option.sntp_servers:
                if sntp_server not in sntp_servers:
                    sntp_servers.append(sntp_server)

        # Then add our own
        for sntp_server in self.option.sntp_servers:
            if sntp_server not in sntp_servers:
                sntp_servers.append(sntp_server)

        # And return a new option with the combined addresses
        return SNTPServersOption(sntp_servers=sntp_servers)
