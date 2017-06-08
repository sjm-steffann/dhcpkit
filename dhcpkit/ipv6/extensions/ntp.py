"""
Implementation of NTP options as specified in :rfc:`5908`.
"""
import codecs
from ipaddress import IPv6Address
from struct import pack, unpack_from
from typing import Iterable, Tuple, Union

from dhcpkit.ipv6.messages import AdvertiseMessage, InformationRequestMessage, RebindMessage, RenewMessage, \
    ReplyMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import Option
from dhcpkit.protocol_element import ProtocolElement
from dhcpkit.utils import encode_domain, parse_domain_bytes

OPTION_NTP_SERVER = 56

NTP_SUBOPTION_SRV_ADDR = 1
NTP_SUBOPTION_MC_ADDR = 2
NTP_SUBOPTION_SRV_FQDN = 3


# This subclass remains abstract
# noinspection PyAbstractClass
class NTPSubOption(ProtocolElement):
    """
    :rfc:`5908`

    :type suboption_type: int
    """

    # This needs to be overwritten in subclasses
    suboption_type = 0

    # This is used to convert a string representation of the value in configuration to a real value
    config_datatype = None

    @property
    def value(self) -> str:
        """
        Return a simple string representation of the value of this sub-option.

        :return: The value of this option as a string
        """
        return ''

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int = 0) -> type:
        """
        Return the appropriate subclass from the registry, or UnknownNTPSubOption if no subclass is registered.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :return: The best known class for this suboption data
        """
        from .ntp_suboption_registry import ntp_suboption_registry
        suboption_type = unpack_from('!H', buffer, offset=offset)[0]
        return ntp_suboption_registry.get(suboption_type, UnknownNTPSubOption)

    def parse_suboption_header(self, buffer: bytes, offset: int = 0, length: int = None) -> Tuple[int, int]:
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
    """
    Container for raw NTP sub-option content for cases where we don't know how to decode it.

    :type suboption_data: bytes
    """

    def __init__(self, suboption_type: int = 0, suboption_data: bytes = b''):
        self.suboption_type = suboption_type
        """Type code for this sub-option"""

        self.suboption_data = suboption_data
        """Data for this sub-option"""

    @property
    def value(self) -> str:
        """
        Return a simple string representation of the value of this sub-option.

        :return: The value of this option as a string
        """
        return codecs.encode(self.suboption_data, 'hex').decode('ascii')

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.suboption_type, int) or not (0 <= self.suboption_type < 2 ** 16):
            raise ValueError("Sub-option type must be an unsigned 16 bit integer")

        if not isinstance(self.suboption_data, bytes):
            raise ValueError("Sub-option data must be sequence of bytes")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset = 0

        self.suboption_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This suboption is longer than the available buffer')

        self.suboption_data = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HH', self.suboption_type, len(self.suboption_data)) + self.suboption_data


class NTPServerAddressSubOption(NTPSubOption):
    """
    :rfc:`5908#section-4.1`

    This suboption is intended to appear inside the OPTION_NTP_SERVER
    option.  It specifies the IPv6 unicast address of an NTP server or
    SNTP server available to the client.

    The format of the NTP Server Address Suboption is:

    .. code-block:: none

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

    IPv6 address of the NTP server
        An IPv6 address.

    suboption-code
        NTP_SUBOPTION_SRV_ADDR (1).

    suboption-len
        16.

    :type address: IPv6Address
    """

    suboption_type = NTP_SUBOPTION_SRV_ADDR

    def __init__(self, address: IPv6Address = None):
        self.address = address
        """IPv6 address of an NTP server"""

    @staticmethod
    def config_datatype(value: str) -> IPv6Address:
        """
        Convert string data from the configuration to an IPv6address.

        :param value: String from config file
        :return: Parsed IPv6 address
        """
        value = IPv6Address(value)
        if value.is_link_local or value.is_loopback or value.is_multicast or value.is_unspecified:
            raise ValueError("NTP server address must be a routable IPv6 address")
        return value

    @property
    def value(self) -> str:
        """
        Return a simple string representation of the value of this sub-option.

        :return: The value of this option as a string
        """
        return str(self.address)

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.address, IPv6Address) or self.address.is_link_local or self.address.is_loopback \
                or self.address.is_multicast or self.address.is_unspecified:
            raise ValueError("NTP server address must be a routable IPv6 address")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, suboption_len = self.parse_suboption_header(buffer, offset, length)

        if suboption_len != 16:
            raise ValueError('NTP Server Address SubOptions must have length 16')

        self.address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.suboption_type, 16))
        buffer.extend(self.address.packed)
        return buffer


class NTPMulticastAddressSubOption(NTPSubOption):
    """
    :rfc:`5908#section-4.2`

    This suboption is intended to appear inside the OPTION_NTP_SERVER
    option.  It specifies the IPv6 address of the IPv6 multicast group
    address used by NTP on the local network.

    The format of the NTP Multicast Address Suboption is:

    .. code-block:: none

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

    Multicast IPv6 address
        An IPv6 address.

    suboption-code
        NTP_SUBOPTION_MC_ADDR (2).

    suboption-len
        16.

    :type address: IPv6Address
    """

    suboption_type = NTP_SUBOPTION_MC_ADDR

    def __init__(self, address: IPv6Address = None):
        self.address = address
        """IPv6 multicast group address"""

    @staticmethod
    def config_datatype(value: str) -> IPv6Address:
        """
        Convert string data from the configuration to an IPv6address.

        :param value: String from config file
        :return: Parsed IPv6 address
        """
        value = IPv6Address(value)
        if not value.is_multicast:
            raise ValueError("NTP multicast address must be a multicast IPv6 address")
        return value

    @property
    def value(self) -> str:
        """
        Return a simple string representation of the value of this sub-option.

        :return: The value of this option as a string
        """
        return str(self.address)

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.address, IPv6Address) or not self.address.is_multicast:
            raise ValueError("NTP multicast address must be a multicast IPv6 address")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, suboption_len = self.parse_suboption_header(buffer, offset, length)

        if suboption_len != 16:
            raise ValueError('NTP Multicast Address SubOptions must have length 16')

        self.address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.suboption_type, 16))
        buffer.extend(self.address.packed)
        return buffer


class NTPServerFQDNSubOption(NTPSubOption):
    """
    :rfc:`5908#section-4.3`

    This suboption is intended to appear inside the OPTION_NTP_SERVER
    option.  It specifies the FQDN of an NTP server or SNTP server
    available to the client.

    The format of the NTP Server FQDN Suboption is:

    .. code-block:: none

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    NTP_SUBOPTION_SRV_FQDN     |         suboption-len         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                      FQDN of NTP server                       |
      :                                                               :
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    suboption-code
        NTP_SUBOPTION_SRV_FQDN (3).

    suboption-len
        Length of the included FQDN field.

    FQDN
        Fully-Qualified Domain Name of the NTP server or SNTP server. This field MUST be encoded as described in
        :rfc:`3315`, Section 8.  Internationalized domain names are not allowed in this field.

    :type fqdn: str
    """

    suboption_type = NTP_SUBOPTION_SRV_FQDN

    def __init__(self, fqdn: str = ''):
        self.fqdn = fqdn
        """Domain name of an NTP server"""

    @staticmethod
    def config_datatype(value: str) -> str:
        """
        Convert string data from the configuration to, well, a string. But a validated string!

        :param value: String from config file
        :return: Parsed fqdn
        """
        # Let the domain encoder check for errors
        encode_domain(value)
        return value

    @property
    def value(self) -> str:
        """
        Return a simple string representation of the value of this sub-option.

        :return: The value of this option as a string
        """
        return self.fqdn

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.fqdn, str):
            raise ValueError("FQDN must be a string")

        # Let the domain encoder check for errors
        encode_domain(self.fqdn)

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, suboption_len = self.parse_suboption_header(buffer, offset, length)
        header_offset = my_offset

        # Parse the domain labels
        max_offset = suboption_len + header_offset  # The option_len field counts bytes *after* the header fields
        domain_name_len, self.fqdn = parse_domain_bytes(buffer, offset=offset + my_offset, length=suboption_len)
        my_offset += domain_name_len

        if my_offset != max_offset:
            raise ValueError('Option length does not match the length of the included fqdn')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        fqdn_buffer = encode_domain(self.fqdn)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.suboption_type, len(fqdn_buffer)))
        buffer.extend(fqdn_buffer)
        return buffer


class NTPServersOption(Option):
    """
    :rfc:`5908#section-4`

    This option serves as a container for server location information
    related to one NTP server or Simple Network Time Protocol (SNTP)
    :rfc:`4330` server.  This option can appear multiple times in a DHCPv6
    message.  Each instance of this option is to be considered by the NTP
    client or SNTP client as a server to include in its configuration.

    The option itself does not contain any value.  Instead, it contains
    one or several suboptions that carry NTP server or SNTP server
    location.  This option MUST include one, and only one, time source
    suboption.  The currently defined time source suboptions are
    NTP_OPTION_SRV_ADDR, NTP_OPTION_SRV_MC_ADDR, and NTP_OPTION_SRV_FQDN.
    It carries the NTP server or SNTP server location as a unicast or
    multicast IPv6 address or as an NTP server or SNTP server FQDN.  More
    time source suboptions may be defined in the future.  While the FQDN
    option offers the most deployment flexibility, resiliency as well as
    security, the IP address options are defined to cover cases where a
    DNS dependency is not desirable.

    If the NTP server or SNTP server location is an IPv6 multicast
    address, the client SHOULD use this address as an NTP multicast group
    address and listen to messages sent to this group in order to
    synchronize its clock.

    The format of the NTP Server Option is:

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_NTP_SERVER        |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         suboption-1                           |
      :                                                               :
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         suboption-2                           |
      :                                                               :
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      :                                                               :
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         suboption-n                           |
      :                                                               :
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_NTP_SERVER (56).

    option-len
        Total length of the included suboptions.

    This document does not define any priority relationship between the
    client's embedded configuration (if any) and the NTP or SNTP servers
    discovered via this option.  In particular, the client is allowed to
    simultaneously use its own configured NTP servers or SNTP servers and
    the servers discovered via DHCP.

    :type options: list[NTPSubOption]
    """

    option_type = OPTION_NTP_SERVER

    def __init__(self, options: Iterable[NTPSubOption] = None):
        self.options = list(options or [])
        """List of NTP server sub-options"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        # Check if all options are allowed
        self.validate_contains(self.options)
        for option in self.options:
            option.validate()

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

        # Parse the options
        self.options = []
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            used_buffer, option = NTPSubOption.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed suboptions')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(options_buffer)))
        buffer.extend(options_buffer)
        return buffer


# Register where these options may occur
SolicitMessage.add_may_contain(NTPServersOption)
AdvertiseMessage.add_may_contain(NTPServersOption)
RequestMessage.add_may_contain(NTPServersOption)
RenewMessage.add_may_contain(NTPServersOption)
RebindMessage.add_may_contain(NTPServersOption)
InformationRequestMessage.add_may_contain(NTPServersOption)
ReplyMessage.add_may_contain(NTPServersOption)

NTPServersOption.add_may_contain(NTPSubOption, 1)
