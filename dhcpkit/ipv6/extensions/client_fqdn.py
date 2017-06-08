"""
Implementation of the Client FQDN option as specified in :rfc:`4704`.
"""
from struct import pack
from typing import Union

from dhcpkit.ipv6.messages import AdvertiseMessage, RebindMessage, RenewMessage, ReplyMessage, RequestMessage, \
    SolicitMessage
from dhcpkit.ipv6.options import Option
from dhcpkit.utils import encode_domain, parse_domain_bytes

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

    option-code
        OPTION_CLIENT_FQDN (39).

    option-len
        1 + length of domain name.

    flags
        flag bits used between client and server to negotiate who performs which updates.

    domain-name
        the partial or fully qualified domain name (with length option-len - 1).

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

    def __init__(self, flags: int = 0, domain_name: str = None):
        self.flags = flags
        self.domain_name = domain_name

    @property
    def server_aaaa_update(self):
        """
        Extract the S flag

        :return: Whether the S flag is set
        """
        return bool(self.flags & 1)

    @server_aaaa_update.setter
    def server_aaaa_update(self, value: bool):
        """
        Set/unset the S flag

        :param value: The new value of the S flag
        """
        if value:
            self.flags |= 1
        else:
            self.flags &= ~1

    @property
    def server_aaaa_override(self):
        """
        Extract the O flag

        :return: Whether the O flag is set
        """
        return bool(self.flags & 2)

    @server_aaaa_override.setter
    def server_aaaa_override(self, value: bool):
        """
        Set/unset the O flag

        :param value: The new value of the O flag
        """
        if value:
            self.flags |= 2
        else:
            self.flags &= ~2

    @property
    def no_server_dns_update(self):
        """
        Extract the N flag

        :return: Whether the N flag is set
        """
        return bool(self.flags & 4)

    @no_server_dns_update.setter
    def no_server_dns_update(self, value: bool):
        """
        Set/unset the N flag

        :param value: The new value of the N flag
        """
        if value:
            self.flags |= 4
        else:
            self.flags &= ~4

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if len(self.domain_name) > 255:
            raise ValueError("Domain name must be 255 characters or less")

        # Allow for empty domain name
        if self.domain_name:
            # Otherwise try to encode it
            encode_domain(self.domain_name, allow_relative=True)

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may
        contain more data after the structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        # Get the flags
        self.flags = buffer[offset + my_offset]
        my_offset += 1

        # Parse the domain name
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        domain_name_len, self.domain_name = parse_domain_bytes(buffer, offset=offset + my_offset, length=option_len - 1,
                                                               allow_relative=True)
        my_offset += domain_name_len

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the included domain name')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        domain_buffer = encode_domain(self.domain_name)

        buffer = bytearray()
        buffer.extend(pack('!HHB', self.option_type, 1 + len(domain_buffer), self.flags))
        buffer.extend(domain_buffer)
        return buffer


SolicitMessage.add_may_contain(ClientFQDNOption, 0, 1)
AdvertiseMessage.add_may_contain(ClientFQDNOption, 0, 1)
RequestMessage.add_may_contain(ClientFQDNOption, 0, 1)
RenewMessage.add_may_contain(ClientFQDNOption, 0, 1)
RebindMessage.add_may_contain(ClientFQDNOption, 0, 1)
ReplyMessage.add_may_contain(ClientFQDNOption, 0, 1)
