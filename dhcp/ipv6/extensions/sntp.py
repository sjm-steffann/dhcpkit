"""
Classes and constants for the options defined in http://www.iana.org/go/rfc4075
"""

import configparser
from ipaddress import IPv6Address
import re
from struct import pack

from dhcp.ipv6 import option_registry
from dhcp.ipv6.options import Option, SimpleOptionHandler, OptionHandler

OPTION_SNTP_SERVERS = 31


class SNTPServersOption(Option):
    """
    http://tools.ietf.org/html/rfc4075#section-4

    The Simple Network Time Protocol servers option provides a list of
    one or more IPv6 addresses of SNTP [3] servers available to the
    client for synchronization.  The clients use these SNTP servers to
    synchronize their system time to that of the standard time servers.
    Clients MUST treat the list of SNTP servers as an ordered list.  The
    server MAY list the SNTP servers in decreasing order of preference.

    The option defined in this document can only be used to configure
    information about SNTP servers that can be reached using IPv6.  The
    DHCP option to configure information about IPv4 SNTP servers can be
    found in RFC 2132 [4].  Mechanisms for configuring IPv4/IPv6 dual-
    stack applications are being considered, but are not specified in
    this document.

    The format of the Simple Network Time Protocol servers option is as
    shown below:

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_SNTP_SERVERS       |        option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                  SNTP server (IPv6 address)                   |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                  SNTP server (IPv6 address)                   |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


      option-code: OPTION_SNTP_SERVERS (31)

      option-len:  Length of the 'SNTP server' fields, in octets;
                   it must be a multiple of 16

      SNTP server: IPv6 address of SNTP server


    """

    option_type = OPTION_SNTP_SERVERS

    def __init__(self, sntp_servers: [IPv6Address]=None):
        self.sntp_servers = sntp_servers or []

    # noinspection PyDocstring
    def validate(self):
        if not isinstance(self.sntp_servers, list) \
                or not all([isinstance(address, IPv6Address) and not (address.is_link_local or address.is_loopback
                                                                      or address.is_multicast or address.is_unspecified)
                            for address in self.sntp_servers]):
            raise ValueError("SNTP servers must be a list of routable IPv6 addresses")

    # noinspection PyDocstring
    @classmethod
    def handler_from_config(cls, section: configparser.SectionProxy) -> OptionHandler:
        sntp_servers = section.get('sntp-servers')
        if sntp_servers is None:
            raise configparser.NoOptionError('sntp-servers', section.name)

        addresses = []
        for addr_str in re.split('[,\t ]+', sntp_servers):
            if not addr_str:
                raise configparser.ParsingError("sntp_servers option has no value")

            addresses.append(IPv6Address(addr_str))

        option = cls(sntp_servers=addresses)
        option.validate()

        return SimpleOptionHandler(option)

    # noinspection PyDocstring
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        if option_len % 16 != 0:
            raise ValueError('SNTP Servers Option length must be a multiple of 16')

        # Parse the addresses
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
            self.sntp_servers.append(address)
            my_offset += 16

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the included addresses')

        self.validate()

        return my_offset

    # noinspection PyDocstring
    def save(self) -> bytes:
        self.validate()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.sntp_servers) * 16))
        for address in self.sntp_servers:
            buffer.extend(address.packed)

        return buffer


option_registry.register(SNTPServersOption)
