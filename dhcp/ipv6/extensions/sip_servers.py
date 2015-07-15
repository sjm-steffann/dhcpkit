# http://www.iana.org/go/rfc3319
import configparser
from ipaddress import IPv6Address
import re
from struct import pack

from dhcp.utils import parse_domain_list_bytes, encode_domain_list
from dhcp.ipv6 import option_registry
from dhcp.ipv6.options import Option

OPTION_SIP_SERVER_D = 21
OPTION_SIP_SERVER_A = 22


class SIPServersDomainNameList(Option):
    """
    http://tools.ietf.org/html/rfc3319#section-3.1

    The option length is followed by a sequence of labels, encoded
    according to Section 3.1 of RFC 1035 [5], quoted below:

      "Domain names in messages are expressed in terms of a sequence of
      labels.  Each label is represented as a one octet length field
      followed by that number of octets.  Since every domain name ends

      with the null label of the root, a domain name is terminated by a
      length byte of zero.  The high order two bits of every length
      octet must be zero, and the remaining six bits of the length field
      limit the label to 63 octets or less.  To simplify
      implementations, the total length of a domain name (i.e., label
      octets and label length octets) is restricted to 255 octets or
      less."

      RFC 1035 encoding was chosen to accommodate future
      internationalized domain name mechanisms.

    The option MAY contain multiple domain names, but these SHOULD refer
    to different NAPTR records, rather than different A records.  The
    client MUST try the records in the order listed, applying the
    mechanism described in Section 4.1 of RFC 3263 [3] for each.  The
    client only resolves the subsequent domain names if attempts to
    contact the first one failed or yielded no common transport protocols
    between client and server or denote a domain administratively
    prohibited by client policy.  Domain names MUST be listed in order of
    preference.

      Use of multiple domain names is not meant to replace NAPTR or SRV
      records, but rather to allow a single DHCP server to indicate
      outbound proxy servers operated by multiple providers.

    The DHCPv6 option has the format shown in Fig. 1.

      option-code: OPTION_SIP_SERVER_D (21)

      option-length: Length of the 'SIP Server Domain Name List' field
      in octets; variable.

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |      OPTION_SIP_SERVER_D      |         option-length         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                 SIP Server Domain Name List                   |
    |                              ...                              |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

          Figure 1: DHCPv6 option for SIP Server Domain Name List

      SIP Server Domain Name List: The domain names of the SIP outbound
      proxy servers for the client to use.  The domain names are encoded
      as specified in Section 8 ("Representation and use of domain
      names") of the DHCPv6 specification [1].
    """

    option_type = OPTION_SIP_SERVER_D

    def __init__(self, domain_names: [str]=None):
        self.domain_names = domain_names or []

    def validate(self):
        for domain_name in self.domain_names:
            if len(domain_name) > 255:
                raise ValueError("Domain names must be 255 characters or less")

            if any([0 >= len(label) > 63 for label in domain_name.split('.')]):
                raise ValueError("Domain labels must be 1 to 63 characters long")

    @classmethod
    def from_config_section(cls, section: configparser.SectionProxy):
        domain_names = section.get('domain-names')
        if domain_names is None:
            raise configparser.NoOptionError('domain-names', section.name)
        domain_names = re.split('[,\t ]+', domain_names)

        option = cls(domain_names=domain_names)
        option.validate()
        return option

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        # Parse the domain labels
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        domain_names_len, self.domain_names = parse_domain_list_bytes(buffer,
                                                                      offset=offset + my_offset, length=option_len)
        my_offset += domain_names_len

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the included domain names')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        self.validate()

        domain_buffer = encode_domain_list(self.domain_names)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(domain_buffer)))
        buffer.extend(domain_buffer)
        return buffer


class SIPServersAddressListOption(Option):
    """
    http://tools.ietf.org/html/rfc3319#section-3.2

    This option specifies a list of IPv6 addresses indicating SIP
    outbound proxy servers available to the client.  Servers MUST be
    listed in order of preference.

    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |      OPTION_SIP_SERVER_A      |           option-len          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    |                   SIP server (IP address)                     |
    |                                                               |
    |                                                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    |                   SIP server (IP address)                     |
    |                                                               |
    |                                                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                              ...                              |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      option-code: OPTION_SIP_SERVER_A (22)

      option-length: Length of the 'options' field in octets; must be a
      multiple of 16.

      SIP server: IPv6 address of a SIP server for the client to use.
                  The servers are listed in the order of preference for
                  use by the client.
    """

    option_type = OPTION_SIP_SERVER_A

    def __init__(self, sip_servers: [IPv6Address]=None):
        self.sip_servers = sip_servers or []

    def validate(self):
        if not isinstance(self.sip_servers, list) \
                or not all([isinstance(address, IPv6Address) and not (address.is_link_local or address.is_loopback
                                                                      or address.is_multicast or address.is_unspecified)
                            for address in self.sip_servers]):
            raise ValueError("SIP servers must be a list of routable IPv6 addresses")

    @classmethod
    def from_config_section(cls, section: configparser.SectionProxy):
        sip_servers = section.get('sip-servers')
        if sip_servers is None:
            raise configparser.NoOptionError('sip-servers', section.name)

        addresses = []
        for addr_str in re.split('[,\t ]+', sip_servers):
            if not addr_str:
                raise configparser.ParsingError("sip_servers option has no value")

            addresses.append(IPv6Address(addr_str))

        option = cls(sip_servers=addresses)
        option.validate()
        return option

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        if option_len % 16 != 0:
            raise ValueError('SIP Servers Option length must be a multiple of 16')

        # Parse the addresses
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
            self.sip_servers.append(address)
            my_offset += 16

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the included addresses')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        self.validate()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.sip_servers) * 16))
        for address in self.sip_servers:
            buffer.extend(address.packed)

        return buffer


option_registry.register(SIPServersDomainNameList)
option_registry.register(SIPServersAddressListOption)
