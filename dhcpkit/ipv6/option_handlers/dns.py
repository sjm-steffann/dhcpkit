"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.dns
"""

import configparser
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.dns import RecursiveNameServersOption, DomainSearchListOption
from dhcpkit.ipv6.option_handlers import SimpleOptionHandler, OptionHandler, register_option_handler


class RecursiveNameServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, dns_servers: [IPv6Address]):
        option = RecursiveNameServersOption(dns_servers=dns_servers)
        option.validate()

        super().__init__(option)

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        addresses = []
        for name, value in section.items():
            # Strip numbers from the end, this can be used to supply the same option multiple times
            name = name.rstrip('0123456789-')

            if name != 'server-address':
                continue

            addresses.append(IPv6Address(value))

        return cls(addresses)


class DomainSearchListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, search_list: [str]):
        option = DomainSearchListOption(search_list=search_list)
        option.validate()

        super().__init__(option)

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        domain_names = []
        for name, value in section.items():
            # Strip numbers from the end, this can be used to supply the same option multiple times
            name = name.rstrip('0123456789-')

            if name != 'domain-name':
                continue

            domain_names.append(value)

        return cls(domain_names)


register_option_handler(RecursiveNameServersOptionHandler)
register_option_handler(DomainSearchListOptionHandler)
