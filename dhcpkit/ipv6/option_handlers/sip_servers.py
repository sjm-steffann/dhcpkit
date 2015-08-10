"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.sip_servers
"""

import configparser
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.sip_servers import SIPServersDomainNameListOption, SIPServersAddressListOption
from dhcpkit.ipv6.option_handlers import SimpleOptionHandler, OptionHandler, register_option_handler


class SIPServersDomainNameListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting SIPServersDomainNameListOptions in responses
    """

    def __init__(self, domain_names: [str]):
        option = SIPServersDomainNameListOption(domain_names=domain_names)
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


class SIPServersAddressListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting SIPServersAddressListOptions in responses
    """

    def __init__(self, sip_servers: [IPv6Address]):
        option = SIPServersAddressListOption(sip_servers=sip_servers)
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


register_option_handler(SIPServersAddressListOptionHandler)
register_option_handler(SIPServersDomainNameListOptionHandler)
