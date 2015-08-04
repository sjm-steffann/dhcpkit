# http://www.iana.org/go/rfc4704
import configparser
import re
from struct import pack
from dhcpkit.ipv6 import option_registry
from dhcpkit.ipv6.options import Option
from dhcpkit.utils import parse_domain_list_bytes, encode_domain_list

OPTION_CLIENT_FQDN = 39


class ClientFQDNOption(Option):
    """
    To update the IPv6-address-to-FQDN mapping, a DHCPv6 server needs to
    know the FQDN of the client for the addresses for the client's IA_NA
    bindings.  To allow the client to convey its FQDN to the server, this
    document defines a new DHCPv6 option called "Client FQDN".  The
    Client FQDN option also contains Flags that DHCPv6 clients and
    servers use to negotiate who does which updates.

    The code for this option is 39.  Its minimum length is 1 octet.

    The format of the DHCPv6 Client FQDN option is shown below::

        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |          OPTION_FQDN          |         option-len            |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |   flags       |                                               |
       +-+-+-+-+-+-+-+-+                                               |
       .                                                               .
       .                          domain-name                          .
       .                                                               .
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

         option-code      OPTION_CLIENT_FQDN (39)

         option-len       1 + length of domain name

         flags            flag bits used between client and server to
                          negotiate who performs which updates

         domain-name      the partial or fully qualified domain name
                          (with length option-len - 1)

    The Client FQDN option MUST only appear in a message's options field
    and applies to all addresses for all IA_NA bindings in the
    transaction.

    4.1.  The Flags Field

    The format of the Flags field is::

        0 1 2 3 4 5 6 7
       +-+-+-+-+-+-+-+-+
       |  MBZ    |N|O|S|
       +-+-+-+-+-+-+-+-+

    The "S" bit indicates whether the server SHOULD or SHOULD NOT perform
    the AAAA RR (FQDN-to-address) DNS updates.  A client sets the bit to
    0 to indicate that the server SHOULD NOT perform the updates and 1 to
    indicate that the server SHOULD perform the updates.  The state of
    the bit in the reply from the server indicates the action to be taken
    by the server; if it is 1, the server has taken responsibility for
    AAAA RR updates for the FQDN.

    The "O" bit indicates whether the server has overridden the client's
    preference for the "S" bit.  A client MUST set this bit to 0.  A
    server MUST set this bit to 1 if the "S" bit in its reply to the
    client does not match the "S" bit received from the client.

    The "N" bit indicates whether the server SHOULD NOT perform any DNS
    updates.  A client sets this bit to 0 to request that the server
    SHOULD perform updates (the PTR RR and possibly the AAAA RR based on
    the "S" bit) or to 1 to request that the server SHOULD NOT perform
    any DNS updates.  A server sets the "N" bit to indicate whether the
    server SHALL (0) or SHALL NOT (1) perform DNS updates.  If the "N"
    bit is 1, the "S" bit MUST be 0.

    The remaining bits in the Flags field are reserved for future
    assignment.  DHCPv6 clients and servers that send the Client FQDN
    option MUST clear the MBZ bits, and they MUST ignore these bits.

    4.2.  The Domain Name Field

    The Domain Name part of the option carries all or part of the FQDN of
    a DHCPv6 client.  The data in the Domain Name field MUST be encoded
    as described in Section 8 of [5].  In order to determine whether the
    FQDN has changed between message exchanges, the client and server
    MUST NOT alter the Domain Name field contents unless the FQDN has
    actually changed.

    A client MAY be configured with a fully qualified domain name or with
    a partial name that is not fully qualified.  If a client knows only
    part of its name, it MAY send a name that is not fully qualified,
    indicating that it knows part of the name but does not necessarily
    know the zone in which the name is to be embedded.

    To send a fully qualified domain name, the Domain Name field is set
    to the DNS-encoded domain name including the terminating zero-length
    label.  To send a partial name, the Domain Name field is set to the
    DNS-encoded domain name without the terminating zero-length label.

    A client MAY also leave the Domain Name field empty if it desires the
    server to provide a name.

    Servers SHOULD send the complete fully qualified domain name in
    Client FQDN options.
    """

    option_type = OPTION_CLIENT_FQDN

    def __init__(self, search_list: [str]=None):
        self.search_list = search_list or []

    def validate(self):
        for domain_name in self.search_list:
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

        option = cls(search_list=domain_names)
        option.validate()
        return option

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

    def save(self) -> bytes:
        self.validate()

        domain_buffer = encode_domain_list(self.search_list)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(domain_buffer)))
        buffer.extend(domain_buffer)
        return buffer


option_registry.register(DomainSearchListOption)

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
