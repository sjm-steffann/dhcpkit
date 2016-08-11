"""
Handlers for the options defined in dhcpkit.ipv6.extensions.sip_serves
"""

from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.sip_servers import SIPServersAddressListOption, SIPServersDomainNameListOption
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler
from typing import Iterable


class SIPServersDomainNameListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting SIPServersDomainNameListOptions in responses
    """

    def __init__(self, domain_names: Iterable[str], always_send: bool = False):
        option = SIPServersDomainNameListOption(domain_names=domain_names)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, ', '.join(map(str, self.option.domain_names)))

    def combine(self, existing_options: Iterable[SIPServersDomainNameListOption]) -> SIPServersDomainNameListOption:
        """
        Combine multiple options into one.

        :param existing_options: The existing options to include NTP servers from
        :return: The combined option
        """
        domain_names = []

        # Add from existing options first
        for option in existing_options:
            for domain_name in option.domain_names:
                if domain_name not in domain_names:
                    domain_names.append(domain_name)

        # Then add our own
        for domain_name in self.option.domain_names:
            if domain_name not in domain_names:
                domain_names.append(domain_name)

        # And return a new option with the combined addresses
        return SIPServersDomainNameListOption(domain_names=domain_names)


class SIPServersAddressListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting SIPServersAddressListOptions in responses
    """

    def __init__(self, sip_servers: Iterable[IPv6Address], always_send: bool = False):
        option = SIPServersAddressListOption(sip_servers=sip_servers)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, ', '.join(map(str, self.option.sip_servers)))

    def combine(self, existing_options: Iterable[SIPServersAddressListOption]) -> SIPServersAddressListOption:
        """
        Combine multiple options into one.

        :param existing_options: The existing options to include NTP servers from
        :return: The combined option
        """
        sip_servers = []

        # Add from existing options first
        for option in existing_options:
            for sip_server in option.sip_servers:
                if sip_server not in sip_servers:
                    sip_servers.append(sip_server)

        # Then add our own
        for sip_server in self.option.sip_servers:
            if sip_server not in sip_servers:
                sip_servers.append(sip_server)

        # And return a new option with the combined addresses
        return SIPServersAddressListOption(sip_servers=sip_servers)
