"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.dns
"""

from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.dns.options import RecursiveNameServersOption, DomainSearchListOption
from dhcpkit.ipv6.option_handlers import SimpleOptionHandler


class RecursiveNameServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, dns_servers: [IPv6Address]):
        option = RecursiveNameServersOption(dns_servers=dns_servers)
        option.validate()

        super().__init__(option)


class DomainSearchListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, search_list: [str]):
        option = DomainSearchListOption(search_list=search_list)
        option.validate()

        super().__init__(option)
