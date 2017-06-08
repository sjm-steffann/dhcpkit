"""
Implementation of SIP options as specified in :rfc:`3319`.
"""

from ipaddress import IPv6Address
from struct import pack
from typing import Iterable, Union

from dhcpkit.ipv6.messages import AdvertiseMessage, InformationRequestMessage, RebindMessage, RenewMessage, \
    ReplyMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import Option
from dhcpkit.utils import encode_domain, encode_domain_list, parse_domain_list_bytes

OPTION_SIP_SERVER_D = 21
OPTION_SIP_SERVER_A = 22


class SIPServersDomainNameListOption(Option):
    """
    :rfc:`3319#section-3.1`

    The option length is followed by a sequence of labels, encoded
    according to Section 3.1 of :rfc:`1035` [5], quoted below:

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

      :rfc:`1035` encoding was chosen to accommodate future
      internationalized domain name mechanisms.

    The option MAY contain multiple domain names, but these SHOULD refer
    to different NAPTR records, rather than different A records.  The
    client MUST try the records in the order listed, applying the
    mechanism described in Section 4.1 of :rfc:`3263` [3] for each.  The
    client only resolves the subsequent domain names if attempts to
    contact the first one failed or yielded no common transport protocols
    between client and server or denote a domain administratively
    prohibited by client policy.  Domain names MUST be listed in order of
    preference.

      Use of multiple domain names is not meant to replace NAPTR or SRV
      records, but rather to allow a single DHCP server to indicate
      outbound proxy servers operated by multiple providers.

    The DHCPv6 option has the format shown here:

    .. code-block:: none

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_SIP_SERVER_D      |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                 SIP Server Domain Name List                   |
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_SIP_SERVER_D (21).

    option-length
        Length of the 'SIP Server Domain Name List' field in octets; variable.

    SIP Server Domain Name List
        The domain names of the SIP outbound proxy servers for the client to use.  The domain names are encoded as
        specified in Section 8 ("Representation and use of domain names") of the DHCPv6 specification [1].

    :type domain_names: list[str]
    """

    option_type = OPTION_SIP_SERVER_D

    def __init__(self, domain_names: Iterable[str] = None):
        self.domain_names = list(domain_names or [])
        """List of domain names of SIP servers"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.domain_names, list):
            raise ValueError("Domain names must be a list of strings")

        for domain_name in self.domain_names:
            # Just encode to validate
            encode_domain(domain_name)

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        # Parse the domain labels
        parsed_len, self.domain_names = parse_domain_list_bytes(buffer, offset=offset + my_offset, length=option_len)
        my_offset += parsed_len

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        domain_buffer = encode_domain_list(self.domain_names)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(domain_buffer)))
        buffer.extend(domain_buffer)
        return buffer


class SIPServersAddressListOption(Option):
    """
    :rfc:`3319#section-3.2`

    This option specifies a list of IPv6 addresses indicating SIP
    outbound proxy servers available to the client.  Servers MUST be
    listed in order of preference.

    .. code-block:: none

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

    option-code
        OPTION_SIP_SERVER_A (22).

    option-length
        Length of the 'options' field in octets; must be a multiple of 16.

    SIP server
        IPv6 address of a SIP server for the client to use. The servers are listed in the order of preference for use
        by the client.
    """

    option_type = OPTION_SIP_SERVER_A

    def __init__(self, sip_servers: Iterable[IPv6Address] = None):
        self.sip_servers = list(sip_servers or [])
        """List of IPv6 addresses of SIP servers"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.sip_servers, list):
            raise ValueError("SIP servers must be a list")

        for address in self.sip_servers:
            if not isinstance(address, IPv6Address) or \
                    address.is_link_local or \
                    address.is_loopback or \
                    address.is_multicast or \
                    address.is_unspecified:
                raise ValueError("SIP servers must be a list of routable IPv6 addresses")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        if option_len % 16 != 0:
            raise ValueError('SIP Servers Option length must be a multiple of 16')

        # Parse the addresses
        self.sip_servers = []
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
            self.sip_servers.append(address)
            my_offset += 16

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.sip_servers) * 16))
        for address in self.sip_servers:
            buffer.extend(address.packed)

        return buffer


# Register where these options may occur
SolicitMessage.add_may_contain(SIPServersDomainNameListOption)
AdvertiseMessage.add_may_contain(SIPServersDomainNameListOption)
RequestMessage.add_may_contain(SIPServersDomainNameListOption)
RenewMessage.add_may_contain(SIPServersDomainNameListOption)
RebindMessage.add_may_contain(SIPServersDomainNameListOption)
InformationRequestMessage.add_may_contain(SIPServersDomainNameListOption)
ReplyMessage.add_may_contain(SIPServersDomainNameListOption)

SolicitMessage.add_may_contain(SIPServersAddressListOption)
AdvertiseMessage.add_may_contain(SIPServersAddressListOption)
RequestMessage.add_may_contain(SIPServersAddressListOption)
RenewMessage.add_may_contain(SIPServersAddressListOption)
RebindMessage.add_may_contain(SIPServersAddressListOption)
InformationRequestMessage.add_may_contain(SIPServersAddressListOption)
ReplyMessage.add_may_contain(SIPServersAddressListOption)
