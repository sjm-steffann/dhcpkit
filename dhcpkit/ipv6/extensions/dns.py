"""
Implementation of DNS options as specified in :rfc:`3646`.
"""

import configparser
from ipaddress import IPv6Address
import re
from struct import pack

from dhcpkit.ipv6.option_handlers import SimpleOptionHandler, OptionHandler
from dhcpkit.utils import parse_domain_list_bytes, encode_domain_list
from dhcpkit.ipv6 import option_registry, option_handler_registry
from dhcpkit.ipv6.messages import SolicitMessage, AdvertiseMessage, RequestMessage, RenewMessage, RebindMessage, \
    InformationRequestMessage, ReplyMessage
from dhcpkit.ipv6.options import Option

OPTION_DNS_SERVERS = 23
OPTION_DOMAIN_LIST = 24


class RecursiveNameServersOption(Option):
    """
    :rfc:`3646#section-3`

    The DNS Recursive Name Server option provides a list of one or more
    IPv6 addresses of DNS recursive name servers to which a client's DNS
    resolver MAY send DNS queries [1].  The DNS servers are listed in the
    order of preference for use by the client resolver.

    The format of the DNS Recursive Name Server option is::

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_DNS_SERVERS       |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |            DNS-recursive-name-server (IPv6 address)           |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |            DNS-recursive-name-server (IPv6 address)           |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_DNS_SERVERS (23).

    option-len
        Length of the list of DNS recursive name servers in octets; must be a multiple of 16.

    DNS-recursive-name-server
        IPv6 address of DNS recursive name server.

    :type dns_servers: list[IPv6Address]
    """

    option_type = OPTION_DNS_SERVERS

    def __init__(self, dns_servers: [IPv6Address]=None):
        self.dns_servers = dns_servers or []

    # noinspection PyDocstring
    def validate(self):
        if not isinstance(self.dns_servers, list) \
                or not all([isinstance(address, IPv6Address) and not (address.is_link_local or address.is_loopback
                                                                      or address.is_multicast or address.is_unspecified)
                            for address in self.dns_servers]):
            raise ValueError("DNS servers must be a list of routable IPv6 addresses")

    # noinspection PyDocstring
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        if option_len % 16 != 0:
            raise ValueError('DNS Servers Option length must be a multiple of 16')

        # Parse the addresses
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
            self.dns_servers.append(address)
            my_offset += 16

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the included addresses')

        self.validate()

        return my_offset

    # noinspection PyDocstring
    def save(self) -> bytes:
        self.validate()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.dns_servers) * 16))
        for address in self.dns_servers:
            buffer.extend(address.packed)

        return buffer


class RecursiveNameServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, dns_servers: [IPv6Address]):
        option = RecursiveNameServersOption(dns_servers=dns_servers)
        option.validate()

        super().__init__(option)

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        dns_servers = section.get('dns-servers')
        if dns_servers is None:
            raise configparser.NoOptionError('dns-servers', section.name)

        addresses = []
        for addr_str in re.split('[,\t ]+', dns_servers):
            if not addr_str:
                raise configparser.ParsingError("dns_servers option has no value")

            addresses.append(IPv6Address(addr_str))

        return cls(addresses)


class DomainSearchListOption(Option):
    """
    :rfc:`3646#section-4`

    The Domain Search List option specifies the domain search list the
    client is to use when resolving hostnames with DNS.  This option does
    not apply to other name resolution mechanisms.

    The format of the Domain Search List option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_DOMAIN_LIST       |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                          searchlist                           |
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_DOMAIN_LIST (24).

    option-len
        Length of the 'searchlist' field in octets.

    searchlist
        The specification of the list of domain names in the Domain Search List.

    The list of domain names in the 'searchlist' MUST be encoded as
    specified in section "Representation and use of domain names" of
    :rfc:`3315`.

    :type search_list: list[str]
    """

    option_type = OPTION_DOMAIN_LIST

    def __init__(self, search_list: [str]=None):
        self.search_list = search_list or []

    # noinspection PyDocstring
    def validate(self):
        for domain_name in self.search_list:
            if len(domain_name) > 255:
                raise ValueError("Domain names must be 255 characters or less")

            if any([0 >= len(label) > 63 for label in domain_name.split('.')]):
                raise ValueError("Domain labels must be 1 to 63 characters long")

    # noinspection PyDocstring
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        # Parse the domain labels
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        domain_names_len, self.search_list = parse_domain_list_bytes(buffer,
                                                                     offset=offset + my_offset, length=option_len)
        my_offset += domain_names_len

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the included search domains')

        self.validate()

        return my_offset

    # noinspection PyDocstring
    def save(self) -> bytes:
        self.validate()

        domain_buffer = encode_domain_list(self.search_list)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(domain_buffer)))
        buffer.extend(domain_buffer)
        return buffer


class DomainSearchListOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, search_list: [str]):
        option = DomainSearchListOption(search_list=search_list)
        option.validate()

        super().__init__(option)

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        domain_names = section.get('domain-names')
        if domain_names is None:
            raise configparser.NoOptionError('domain-names', section.name)
        domain_names = re.split('[,\t ]+', domain_names)

        return cls(domain_names)


option_registry.register(RecursiveNameServersOption)
option_registry.register(DomainSearchListOption)

option_handler_registry.register(RecursiveNameServersOptionHandler)
option_handler_registry.register(DomainSearchListOptionHandler)

SolicitMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
AdvertiseMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
RequestMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
RenewMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
RebindMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
InformationRequestMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
ReplyMessage.add_may_contain(RecursiveNameServersOption, 0, 1)

SolicitMessage.add_may_contain(DomainSearchListOption, 0, 1)
AdvertiseMessage.add_may_contain(DomainSearchListOption, 0, 1)
RequestMessage.add_may_contain(DomainSearchListOption, 0, 1)
RenewMessage.add_may_contain(DomainSearchListOption, 0, 1)
RebindMessage.add_may_contain(DomainSearchListOption, 0, 1)
InformationRequestMessage.add_may_contain(DomainSearchListOption, 0, 1)
ReplyMessage.add_may_contain(DomainSearchListOption, 0, 1)
