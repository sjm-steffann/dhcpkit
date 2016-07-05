"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.sntp
"""

from ipaddress import IPv6Address

from typing import Iterable

from dhcpkit.ipv6.extensions.sntp import SNTPServersOption
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler


class SNTPServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting SNTPServersOptions in responses
    """

    def __init__(self, sntp_servers: Iterable[IPv6Address]):
        option = SNTPServersOption(sntp_servers=sntp_servers)
        option.validate()

        super().__init__(option)
