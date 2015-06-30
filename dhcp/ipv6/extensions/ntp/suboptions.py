from ipaddress import IPv6Address
from struct import unpack_from, pack

from dhcp.ipv6.extensions.ntp import suboption_registry
from dhcp.parsing import StructuredElement

NTP_SUBOPTION_SRV_ADDR = 1
NTP_SUBOPTION_MC_ADDR = 2
NTP_SUBOPTION_SRV_FQDN = 3


# This subclass remains abstract
# noinspection PyAbstractClass
class NTPSubOption(StructuredElement):
    """
    https://tools.ietf.org/html/rfc5908
    """

    # This needs to be overwritten in subclasses
    suboption_type = 0

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        """
        Return the appropriate subclass from the registry, or UnknownNTPSubOption if no subclass is registered.

        :param buffer: The buffer to read data from
        :return: The best known class for this suboption data
        """
        suboption_type = unpack_from('!H', buffer, offset=offset)[0]
        return suboption_registry.registry.get(suboption_type, UnknownNTPSubOption)

    def parse_suboption_header(self, buffer: bytes, offset: int=0, length: int=None) -> (int, int):
        """
        Parse the option code and length from the buffer and perform some basic validation.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer and the value of the suboption-len field
        """
        suboption_type, suboption_len = unpack_from('!HH', buffer, offset=offset)
        my_offset = 4

        if suboption_type != self.suboption_type:
            raise ValueError('The provided buffer does not contain {} data'.format(self.__class__.__name__))

        if length is not None and suboption_len + my_offset > length:
            raise ValueError('This suboption is longer than the available buffer')

        return my_offset, suboption_len


class UnknownNTPSubOption(NTPSubOption):
    def __init__(self, suboption_type: int=0, suboption_data: bytes=b''):
        self.suboption_type = suboption_type
        self.suboption_data = suboption_data

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        self.suboption_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This suboption is longer than the available buffer')

        self.suboption_data = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> bytes:
        return pack('!HH', self.suboption_type, len(self.suboption_data)) + self.suboption_data


class NTPServerAddressSubOption(NTPSubOption):
    """
    https://tools.ietf.org/html/rfc5908#section-4.1

    This suboption is intended to appear inside the OPTION_NTP_SERVER
    option.  It specifies the IPv6 unicast address of an NTP server or
    SNTP server available to the client.

    The format of the NTP Server Address Suboption is:

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |    NTP_SUBOPTION_SRV_ADDR     |        suboption-len = 16     |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |                                                               |
     |                                                               |
     |                   IPv6 address of NTP server                  |
     |                                                               |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

       IPv6 address of the NTP server: An IPv6 address,

       suboption-code: NTP_SUBOPTION_SRV_ADDR (1),

       suboption-len: 16.
    """

    suboption_type = NTP_SUBOPTION_SRV_ADDR

    def __init__(self, address: IPv6Address=None):
        self.address = address

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, suboption_len = self.parse_suboption_header(buffer, offset, length)

        if suboption_len != 16:
            raise ValueError('NTP Server Address SubOptions must have length 16')

        self.address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        return my_offset

    def save(self) -> bytes:
        buffer = bytearray()
        buffer.extend(pack('!HH', self.suboption_type, 16))
        buffer.extend(self.address.packed)
        return buffer


suboption_registry.register(NTP_SUBOPTION_SRV_ADDR, NTPServerAddressSubOption)


class NTPMulticastAddressSubOption(NTPSubOption):
    """
    https://tools.ietf.org/html/rfc5908#section-4.2

    This suboption is intended to appear inside the OPTION_NTP_SERVER
    option.  It specifies the IPv6 address of the IPv6 multicast group
    address used by NTP on the local network.

    The format of the NTP Multicast Address Suboption is:

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |    NTP_SUBOPTION_MC_ADDR      |        suboption-len = 16     |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |                                                               |
     |                                                               |
     |                   Multicast IPv6 address                      |
     |                                                               |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

       Multicast IPv6 address: An IPv6 address,

       suboption-code: NTP_SUBOPTION_MC_ADDR (2),

       suboption-len: 16.
    """

    suboption_type = NTP_SUBOPTION_MC_ADDR

    def __init__(self, address: IPv6Address=None):
        self.address = address

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, suboption_len = self.parse_suboption_header(buffer, offset, length)

        if suboption_len != 16:
            raise ValueError('NTP Multicast Address SubOptions must have length 16')

        self.address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        return my_offset

    def save(self) -> bytes:
        buffer = bytearray()
        buffer.extend(pack('!HH', self.suboption_type, 16))
        buffer.extend(self.address.packed)
        return buffer


suboption_registry.register(NTP_SUBOPTION_MC_ADDR, NTPMulticastAddressSubOption)


class NTPServerFQDNSubOption(NTPSubOption):
    """
    https://tools.ietf.org/html/rfc5908#section-4.3

    This suboption is intended to appear inside the OPTION_NTP_SERVER
    option.  It specifies the FQDN of an NTP server or SNTP server
    available to the client.

    The format of the NTP Server FQDN Suboption is:

    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |    NTP_SUBOPTION_SRV_FQDN     |         suboption-len         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                                                               |
    |                      FQDN of NTP server                       |
    :                                                               :
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

     suboption-code: NTP_SUBOPTION_SRV_FQDN (3),

     suboption-len: Length of the included FQDN field,

     FQDN: Fully-Qualified Domain Name of the NTP server or SNTP server.
           This field MUST be encoded as described in [RFC3315],
           Section 8.  Internationalized domain names are not allowed
           in this field.
    """

    suboption_type = NTP_SUBOPTION_SRV_FQDN

    def __init__(self, fqdn: str=''):
        self.fqdn = fqdn

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, suboption_len = self.parse_suboption_header(buffer, offset, length)
        header_offset = my_offset

        # Parse the domain labels
        max_offset = suboption_len + header_offset  # The option_len field counts bytes *after* the header fields
        current_labels = []
        while max_offset > my_offset:
            label_length = buffer[offset + my_offset]
            my_offset += 1

            # End of a sequence of labels
            if label_length == 0:
                domain_name = '.'.join(current_labels)
                current_labels = []

                self.fqdn = domain_name
                break

            if label_length > 63:
                raise ValueError('FQDN contains label with invalid length')

            # Check if we stay below the max offset
            if my_offset + label_length > max_offset:
                raise ValueError('Invalid encoded domain name, exceeds available space')

            # New label
            current_label_bytes = buffer[offset + my_offset:offset + my_offset + label_length]
            my_offset += label_length

            if not current_label_bytes.isalnum():
                raise ValueError('Domain labels must be alphanumerical')
            current_label = current_label_bytes.decode('ascii')
            current_labels.append(current_label)

        if my_offset != max_offset:
            raise ValueError('Option length does not match the length of the included fqdn')

        return my_offset

    def save(self) -> bytes:
        fqdn_buffer = bytearray()

        # Be nice: strip trailing dots
        domain_name = self.fqdn.rstrip('.')

        domain_name_parts = domain_name.split('.')
        for label in domain_name_parts:
            if not label.isalnum():
                raise ValueError('Domain labels must be alphanumerical')

            label_length = len(label)
            if label_length < 1 or label_length > 63:
                raise ValueError('Domain Search List contains label with invalid length')

            fqdn_buffer.append(label_length)
            fqdn_buffer.extend(label.encode('ascii'))

        # End the domain name with a 0-length label
        fqdn_buffer.append(0)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.suboption_type, len(fqdn_buffer)))
        buffer.extend(fqdn_buffer)
        return buffer


suboption_registry.register(NTP_SUBOPTION_SRV_FQDN, NTPServerFQDNSubOption)
