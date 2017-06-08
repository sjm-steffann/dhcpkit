"""
Implementation of MAP options as specified in :rfc:`7598`.
"""
import math
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from struct import pack, unpack
from typing import Iterable, List, Optional, Type, Union

from dhcpkit.ipv6.messages import AdvertiseMessage, ConfirmMessage, RebindMessage, ReleaseMessage, RenewMessage, \
    ReplyMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import Option, SomeOption

OPTION_S46_RULE = 89
OPTION_S46_BR = 90
OPTION_S46_DMR = 91
OPTION_S46_V4V6BIND = 92
OPTION_S46_PORTPARAMS = 93
OPTION_S46_CONT_MAPE = 94
OPTION_S46_CONT_MAPT = 95
OPTION_S46_CONT_LW = 96


class S46RuleOption(Option):
    """
    :rfc:`7598#section-4.1`

    Figure 1 shows the format of the S46 Rule option (OPTION_S46_RULE)
    used for conveying the Basic Mapping Rule (BMR) and Forwarding
    Mapping Rule (FMR).

    This option follows behavior described in Sections 17.1.1 and 18.1.1
    of [RFC3315]. Clients can send those options, encapsulated in their
    respective container options, with specific values as hints for the
    server. See Section 5 for details. Depending on the server
    configuration and policy, it may accept or ignore the hints. Clients
    MUST be able to process received values that are different than the
    hints it sent earlier.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_S46_RULE        |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |     flags     |     ea-len    |  prefix4-len  | ipv4-prefix   |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                  (continued)                  |  prefix6-len  |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                           ipv6-prefix                         |
      |                       (variable length)                       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .                        S46_RULE-options                       .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                          Figure 1: S46 Rule Option

    option-code
        OPTION_S46_RULE (89)

    option-length
        length of the option, excluding option-code and option-length
        fields, including length of all encapsulated options; expressed
        in octets.

    flags
        8 bits long; carries flags applicable to the rule. The meanings of
        the specific bits are explained in Figure 2.

    ea-len
        8 bits long; specifies the Embedded Address (EA) bit length.
        Allowed values range from 0 to 48.

    prefix4-len
        8 bits long; expresses the prefix length of the Rule IPv4 prefix
        specified in the ipv4-prefix field. Allowed values range from 0 to 32.

    ipv4-prefix
        a fixed-length 32-bit field that specifies the IPv4 prefix for the S46
        rule. The bits in the prefix after prefix4-len number of bits are
        reserved and MUST be initialized to zero by the sender and ignored by
        the receiver.

    prefix6-len
        8 bits long; expresses the length of the Rule IPv6 prefix specified in
        the ipv6-prefix field. Allowed values range from 0 to 128.

    ipv6-prefix
        a variable-length field that specifies the IPv6 domain prefix for the
        S46 rule. The field is padded on the right with zero bits up to the
        nearest octet boundary when prefix6-len is not evenly divisible by 8.

    S46_RULE-options
        a variable-length field that may contain zero or more options that
        specify additional parameters for this S46 rule. This document
        specifies one such option: OPTION_S46_PORTPARAMS.


   The format of the S46 Rule Flags field is:

    .. code-block:: none

           0 1 2 3 4 5 6 7
          +-+-+-+-+-+-+-+-+
          |Reserved     |F|
          +-+-+-+-+-+-+-+-+

      Figure 2: S46 Rule Flags

    Reserved
        7 bits; reserved for future use as flags.

    F-flag
        1-bit field that specifies whether the rule is to be used for
        forwarding (FMR). If set, this rule is used as an FMR; if not set,
        this rule is a BMR only and MUST NOT be used for forwarding.

        Note: A BMR can also be used as an FMR for forwarding if the F-flag is
        set. The BMR is determined by a longest-prefix match of the Rule IPv6
        prefix against the End-user IPv6 prefix(es).

    It is expected that in a typical mesh deployment scenario there will be a
    single BMR, which could also be designated as an FMR using the F-flag.
    """

    option_type = OPTION_S46_RULE

    def __init__(self, flags: int = 0, ea_len: int = 0, ipv4_prefix: IPv4Network = None,
                 ipv6_prefix: IPv6Network = None, options: Iterable[Option] = None):
        self.flags = flags
        self.ea_len = ea_len
        self.ipv4_prefix = ipv4_prefix or IPv4Network('0.0.0.0/0')
        self.ipv6_prefix = ipv6_prefix or IPv6Network('::/0')
        self.options = list(options or [])

    @property
    def fmr(self):
        """
        Extract the F flag

        :return: Whether the F flag is set
        """
        return bool(self.flags & 1)

    @fmr.setter
    def fmr(self, value: bool):
        """
        Set/unset the F flag

        :param value: The new value of the F flag
        """
        if value:
            self.flags |= 1
        else:
            self.flags &= ~1

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.flags, int) or not (0 <= self.flags < 2 ** 8):
            raise ValueError("Flags must be an unsigned 8 bit integer")

        if not isinstance(self.ea_len, int) or not (0 <= self.ea_len <= 48):
            raise ValueError("EA-len value must be an integer in range from 0 to 48")

        if not isinstance(self.ipv4_prefix, IPv4Network):
            raise ValueError("IPv4 prefix must be an IPv4Network")

        if not isinstance(self.ipv6_prefix, IPv6Network):
            raise ValueError("IPv6 prefix must be an IPv6Network")

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
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=8)
        header_offset = my_offset

        # Flags
        self.flags = buffer[offset + my_offset]
        my_offset += 1

        # EA-Len
        self.ea_len = buffer[offset + my_offset]
        my_offset += 1

        # IPv4 prefix
        ipv4_prefix_length = buffer[offset + my_offset]
        my_offset += 1

        if not (0 <= ipv4_prefix_length <= 32):
            raise ValueError("IPv4 prefix length must be in range from 0 to 32")

        ipv4_address = IPv4Address(buffer[offset + my_offset:offset + my_offset + 4])
        my_offset += 4

        # Combine address and prefix length into prefix
        self.ipv4_prefix = IPv4Network('{!s}/{:d}'.format(ipv4_address, ipv4_prefix_length), strict=False)

        # IPv6 prefix
        ipv6_prefix_length = buffer[offset + my_offset]
        my_offset += 1

        if not (0 <= ipv6_prefix_length <= 128):
            raise ValueError("IPv6 prefix length must be in range from 0 to 128")

        included_octets = math.ceil(ipv6_prefix_length / 8)
        ipv6_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + included_octets].ljust(16, b'\x00'))
        my_offset += included_octets

        self.ipv6_prefix = IPv6Network('{!s}/{:d}'.format(ipv6_address, ipv6_prefix_length), strict=False)

        # Parse the options
        self.options = []
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        # Store the minimal amount of octets for the IPv6 prefix
        included_octets = math.ceil(self.ipv6_prefix.prefixlen / 8)
        ipv6_address_bytes = self.ipv6_prefix.network_address.packed[:included_octets]

        # Store the options
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HHBBB', self.option_type, len(options_buffer) + included_octets + 8,
                           self.flags, self.ea_len, self.ipv4_prefix.prefixlen))
        buffer.extend(self.ipv4_prefix.network_address.packed)
        buffer.append(self.ipv6_prefix.prefixlen)
        buffer.extend(ipv6_address_bytes)
        buffer.extend(options_buffer)

        return buffer

    def get_options_of_type(self, *args: Type[SomeOption]) -> List[SomeOption]:
        """
        Get all options that are subclasses of the given class.

        :param args: The classes to look for
        :returns: The list of options
        """
        classes = tuple(args)

        # noinspection PyTypeChecker
        return [option for option in self.options if isinstance(option, classes)]

    def get_option_of_type(self, *args: Type[SomeOption]) -> Optional[SomeOption]:
        """
        Get the first option that is a subclass of the given class.

        :param args: The classes to look for
        :returns: The option or None
        """
        classes = tuple(args)
        for option in self.options:
            if isinstance(option, classes):
                # noinspection PyTypeChecker
                return option


class S46BROption(Option):
    """
    :rfc:`7598#section-4.2`

    The S46 BR option (OPTION_S46_BR) is used to convey the IPv6 address
    of the Border Relay. Figure 3 shows the format of the OPTION_S46_BR
    option.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |         OPTION_S46_BR         |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                      br-ipv6-address                          |
      |                                                               |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                           Figure 3: S46 BR Option

    option-code
        OPTION_S46_BR (90)

    option-length
        16

    br-ipv6-address
        a fixed-length field of 16 octets that specifies the IPv6 address for the S46 BR.

    BR redundancy can be implemented by using an anycast address for the
    BR IPv6 address. Multiple OPTION_S46_BR options MAY be included in
    the container; this document does not further explore the use of
    multiple BR IPv6 addresses.
    """

    option_type = OPTION_S46_BR

    def __init__(self, br_address: IPv6Address = None):
        self.br_address = br_address

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.br_address, IPv6Address):
            raise ValueError("BR address must be an IPv6Address")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=16, max_length=16)

        self.br_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, 16))
        buffer.extend(self.br_address.packed)

        return buffer


class S46DMROption(Option):
    """
    :rfc:`7598#section-4.3`

    The S46 DMR option (OPTION_S46_DMR) is used to convey values for the
    Default Mapping Rule (DMR). Figure 4 shows the format of the
    OPTION_S46_DMR option used for conveying a DMR.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_S46_DMR         |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |dmr-prefix6-len|            dmr-ipv6-prefix                    |
      +-+-+-+-+-+-+-+-+           (variable length)                   |
      .                                                              .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                          Figure 4: S46 DMR Option

    option-code
        OPTION_S46_DMR (91)

    option-length
        1 + length of dmr-ipv6-prefix specified in octets.

    dmr-prefix6-len
        8 bits long; expresses the bitmask length of the IPv6 prefix specified
        in the dmr-ipv6-prefix field. Allowed values range from 0 to 128.

    dmr-ipv6-prefix
        a variable-length field specifying the IPv6 prefix or address for the
        BR. This field is right-padded with zeros to the nearest octet
        boundary when dmr-prefix6-len is not divisible by 8.
    """

    option_type = OPTION_S46_DMR

    def __init__(self, dmr_prefix: IPv6Network = None):
        self.dmr_prefix = dmr_prefix

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.dmr_prefix, IPv6Network):
            raise ValueError("DMR prefix must be an IPv6Network")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=1, max_length=17)
        header_offset = my_offset

        # IPv6 prefix
        ipv6_prefix_length = buffer[offset + my_offset]
        my_offset += 1

        if not (0 <= ipv6_prefix_length <= 128):
            raise ValueError("IPv6 prefix length must be in range from 0 to 128")

        included_octets = math.ceil(ipv6_prefix_length / 8)
        ipv6_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + included_octets].ljust(16, b'\x00'))
        my_offset += included_octets

        self.dmr_prefix = IPv6Network('{!s}/{:d}'.format(ipv6_address, ipv6_prefix_length), strict=False)

        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        # Store the minimal amount of octets for the IPv6 prefix
        included_octets = math.ceil(self.dmr_prefix.prefixlen / 8)
        ipv6_address_bytes = self.dmr_prefix.network_address.packed[:included_octets]

        buffer = bytearray()
        buffer.extend(pack('!HHB', self.option_type, 1 + included_octets, self.dmr_prefix.prefixlen))
        buffer.extend(ipv6_address_bytes)

        return buffer


class S46V4V6BindingOption(Option):
    """
    :rfc:`7598#section-4.4`

    The S46 IPv4/IPv6 Address Binding option (OPTION_S46_V4V6BIND) MAY be
    used to specify the full or shared IPv4 address of the CE. The IPv6
    prefix field is used by the CE to identify the correct prefix to use
    for the tunnel source.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_S46_V4V6BIND      |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         ipv4-address                          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |bindprefix6-len|             bind-ipv6-prefix                  |
      +-+-+-+-+-+-+-+-+             (variable length)                 |
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .                      S46_V4V6BIND-options                     .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

               Figure 5: S46 IPv4/IPv6 Address Binding Option

    option-code
        OPTION_S46_V4V6BIND (92)

    option-length
        length of the option, excluding option-code and option-length fields,
        including length of all encapsulated options; expressed in octets.

    ipv4-address
        a fixed-length field of 4 octets specifying an IPv4 address.

    bindprefix6-len
        8 bits long; expresses the bitmask length of the IPv6 prefix specified
        in the bind-ipv6-prefix field. Allowed values range from 0 to 128.

    bind-ipv6-prefix
        a variable-length field specifying the IPv6 prefix or address for the
        S46 CE. This field is right-padded with zeros to the nearest octet
        boundary when bindprefix6-len is not divisible by 8.

    S46_V4V6BIND-options
        a variable-length field that may contain zero or more options that
        specify additional parameters. This document specifies one such
        option: OPTION_S46_PORTPARAMS.
    """

    option_type = OPTION_S46_V4V6BIND

    def __init__(self, ipv4_address: IPv4Address = None, ipv6_prefix: IPv6Network = None,
                 options: Iterable[Option] = None):
        self.ipv4_address = ipv4_address or IPv4Address('0.0.0.0')
        self.ipv6_prefix = ipv6_prefix or IPv6Network('::/0')
        self.options = list(options or [])

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.ipv4_address, IPv4Address):
            raise ValueError("IPv4 address must be an IPv4Address")

        if not isinstance(self.ipv6_prefix, IPv6Network):
            raise ValueError("IPv6 prefix must be an IPv6Network")

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
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=5)
        header_offset = my_offset

        # IPv4 address
        self.ipv4_address = IPv4Address(buffer[offset + my_offset:offset + my_offset + 4])
        my_offset += 4

        # IPv6 prefix
        ipv6_prefix_length = buffer[offset + my_offset]
        my_offset += 1

        if not (0 <= ipv6_prefix_length <= 128):
            raise ValueError("IPv6 prefix length must be in range from 0 to 128")

        included_octets = math.ceil(ipv6_prefix_length / 8)
        ipv6_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + included_octets].ljust(16, b'\x00'))
        my_offset += included_octets

        self.ipv6_prefix = IPv6Network('{!s}/{:d}'.format(ipv6_address, ipv6_prefix_length), strict=False)

        # Parse the options
        self.options = []
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        # Store the minimal amount of octets for the IPv6 prefix
        included_octets = math.ceil(self.ipv6_prefix.prefixlen / 8)
        ipv6_address_bytes = self.ipv6_prefix.network_address.packed[:included_octets]

        # Store the options
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(options_buffer) + included_octets + 5))
        buffer.extend(self.ipv4_address.packed)
        buffer.append(self.ipv6_prefix.prefixlen)
        buffer.extend(ipv6_address_bytes)
        buffer.extend(options_buffer)

        return buffer

    def get_options_of_type(self, *args: Type[SomeOption]) -> List[SomeOption]:
        """
        Get all options that are subclasses of the given class.

        :param args: The classes to look for
        :returns: The list of options
        """
        classes = tuple(args)

        # noinspection PyTypeChecker
        return [option for option in self.options if isinstance(option, classes)]

    def get_option_of_type(self, *args: Type[SomeOption]) -> Optional[SomeOption]:
        """
        Get the first option that is a subclass of the given class.

        :param args: The classes to look for
        :returns: The option or None
        """
        classes = tuple(args)
        for option in self.options:
            if isinstance(option, classes):
                # noinspection PyTypeChecker
                return option


class S46PortParametersOption(Option):
    """
    :rfc:`7598#section-4.5`

    The S46 Port Parameters option (OPTION_S46_PORTPARAMS) specifies
    optional port set information that MAY be provided to CEs.

    See Section 5.1 of [RFC7597] for a description of the MAP algorithm
    and detailed explanation of all of the parameters.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |     OPTION_S46_PORTPARAMS     |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    offset     |   PSID-len    |             PSID              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                    Figure 6: S46 Port Parameters Option

    option-code
        OPTION_S46_PORTPARAMS (93)

    option-length
        4

    offset
        Port Set Identifier (PSID) offset. 8 bits long; specifies the numeric
        value for the S46 algorithm's excluded port range/offset bits
        (a-bits), as per Section 5.1 of [RFC7597]. Allowed values are between
        0 and 15. Default values for this field are specific to the softwire
        mechanism being implemented and are defined in the relevant
        specification document.

    PSID-len
        8 bits long; specifies the number of significant bits in the PSID
        field (also known as 'k'). When set to 0, the PSID field is to be
        ignored. After the first 'a' bits, there are k bits in the port
        number representing the value of the PSID. Consequently, the
        address-sharing ratio would be 2^k.

    PSID
        16 bits long. The PSID value algorithmically identifies a set of
        ports assigned to a CE. The first k bits on the left of this field
        contain the PSID binary value. The remaining (16 - k) bits on the
        right are padding zeros.

    When receiving the OPTION_S46_PORTPARAMS option with an explicit
    PSID, the client MUST use this explicit PSID when configuring its
    softwire interface. The OPTION_S46_PORTPARAMS option with an
    explicit PSID MUST be discarded if the S46 CE isn't configured with a
    full IPv4 address (e.g., IPv4 prefix).

    The OPTION_S46_PORTPARAMS option is contained within an
    OPTION_S46_RULE option or an OPTION_S46_V4V6BIND option.
    """

    option_type = OPTION_S46_PORTPARAMS

    def __init__(self, offset: int = 0, psid_len: int = 0, psid: int = 0):
        self.offset = offset
        self.psid_len = psid_len
        self.psid = psid

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.offset, int) or not (0 <= self.offset <= 15):
            raise ValueError("Offset must be an unsigned 4 bit integer")

        if not isinstance(self.psid_len, int) or not (0 <= self.psid_len <= 16):
            raise ValueError("PSID length must be an integer in range from 0 to 16")

        if self.offset + self.psid_len > 16:
            raise ValueError("Offset and PSID length together must be 16 or less")

        if not isinstance(self.psid, int) or not (0 <= self.psid < 2 ** self.psid_len):
            raise ValueError("PSID must be an unsigned {} bit integer".format(self.psid_len))

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=4, max_length=4)

        self.offset, self.psid_len, raw_psid = unpack('!BBH', buffer[offset + my_offset:offset + my_offset + 4])
        my_offset += 4

        # Convert left-aligned bits to an integer
        self.psid = raw_psid >> (16 - self.psid_len)

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        # Convert integer to left-aligned bits
        raw_psid = self.psid << (16 - self.psid_len)

        buffer = bytearray()
        buffer.extend(pack('!HHBBH', self.option_type, 4, self.offset, self.psid_len, raw_psid))

        return buffer


class S46ContainerOption(Option):
    """
    Common code for MAP-E, MAP-T and LW4over6 containers
    """

    option_type = 0

    def __init__(self, options: Iterable[Option] = None):
        self.options = list(options or [])

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
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=5)

        # Parse the options
        self.options = []
        max_offset = option_len + my_offset
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        # Store the options
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(options_buffer)))
        buffer.extend(options_buffer)

        return buffer

    def get_options_of_type(self, *args: Type[SomeOption]) -> List[SomeOption]:
        """
        Get all options that are subclasses of the given class.

        :param args: The classes to look for
        :returns: The list of options
        """
        classes = tuple(args)

        # noinspection PyTypeChecker
        return [option for option in self.options if isinstance(option, classes)]

    def get_option_of_type(self, *args: Type[SomeOption]) -> Optional[SomeOption]:
        """
        Get the first option that is a subclass of the given class.

        :param args: The classes to look for
        :returns: The option or None
        """
        classes = tuple(args)
        for option in self.options:
            if isinstance(option, classes):
                # noinspection PyTypeChecker
                return option


class S46MapEContainerOption(S46ContainerOption):
    """
    :rfc:`7598#section-5.1`

    The S46 MAP-E Container option (OPTION_S46_CONT_MAPE) specifies the
    container used to group all rules and optional port parameters for a
    specified domain.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_S46_CONT_MAPE   |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .            encapsulated-options (variable length)             .
      .                                                               .
      +---------------------------------------------------------------+

                    Figure 7: S46 MAP-E Container Option

    option-code
        OPTION_S46_CONT_MAPE (94)

    option-length
        length of encapsulated options, expressed in octets.

    encapsulated-options
        options associated with this Softwire46 MAP-E domain.

    The encapsulated-options field conveys options specific to the
    OPTION_S46_CONT_MAPE option. Currently, there are two encapsulated
    options specified: OPTION_S46_RULE and OPTION_S46_BR. There MUST be
    at least one OPTION_S46_RULE option and at least one OPTION_S46_BR
    option.

    Other options applicable to a domain may be defined in the future. A
    DHCPv6 message MAY include multiple OPTION_S46_CONT_MAPE options
    (representing multiple domains).
    """

    option_type = OPTION_S46_CONT_MAPE


class S46MapTContainerOption(S46ContainerOption):
    """
    :rfc:`7598#section-5.2`

    The S46 MAP-T Container option (OPTION_S46_CONT_MAPT) specifies the
    container used to group all rules and optional port parameters for a
    specified domain.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |     OPTION_S46_CONT_MAPT      |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .            encapsulated-options (variable length)             .
      .                                                               .
      +---------------------------------------------------------------+

                    Figure 8: S46 MAP-T Container Option

    option-code
        OPTION_S46_CONT_MAPT (95)

    option-length
        length of encapsulated options, expressed in octets.

    encapsulated-options
        options associated with this Softwire46 MAP-T domain.

    The encapsulated-options field conveys options specific to the
    OPTION_S46_CONT_MAPT option. Currently, there are two options
    specified: the OPTION_S46_RULE and OPTION_S46_DMR options. There
    MUST be at least one OPTION_S46_RULE option and exactly one
    OPTION_S46_DMR option.
    """

    option_type = OPTION_S46_CONT_MAPT


class S46LWContainerOption(S46ContainerOption):
    """
    :rfc:`7598#section-5.3`

    The S46 Lightweight 4over6 Container option (OPTION_S46_CONT_LW)
    specifies the container used to group all rules and optional port
    parameters for a specified domain.

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_S46_CONT_LW       |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      +            encapsulated-options (variable length)             .
      .                                                               .
      +---------------------------------------------------------------+

              Figure 9: S46 Lightweight 4over6 Container Option

    option-code
        OPTION_S46_CONT_LW (96)

    option-length
        length of encapsulated options, expressed in octets.

    encapsulated-options
        options associated with this Softwire46 Lightweight 4over6 domain.

    The encapsulated-options field conveys options specific to the
    OPTION_S46_CONT_LW option. Currently, there are two options
    specified: OPTION_S46_V4V6BIND and OPTION_S46_BR. There MUST be at
    most one OPTION_S46_V4V6BIND option and at least one OPTION_S46_BR
    option.
    """

    option_type = OPTION_S46_CONT_LW


# Register where these options may occur
SolicitMessage.add_may_contain(S46ContainerOption)
AdvertiseMessage.add_may_contain(S46ContainerOption)
RequestMessage.add_may_contain(S46ContainerOption)
ConfirmMessage.add_may_contain(S46ContainerOption)
RenewMessage.add_may_contain(S46ContainerOption)
RebindMessage.add_may_contain(S46ContainerOption)
ReleaseMessage.add_may_contain(S46ContainerOption)
ReplyMessage.add_may_contain(S46ContainerOption)

S46RuleOption.add_may_contain(S46PortParametersOption)

S46V4V6BindingOption.add_may_contain(S46PortParametersOption)

S46MapEContainerOption.add_may_contain(S46RuleOption, min_occurrence=1)
S46MapEContainerOption.add_may_contain(S46BROption, min_occurrence=1)
S46MapEContainerOption.add_may_contain(S46PortParametersOption)

S46MapTContainerOption.add_may_contain(S46RuleOption, min_occurrence=1)
S46MapTContainerOption.add_may_contain(S46DMROption, min_occurrence=1, max_occurrence=1)
S46MapTContainerOption.add_may_contain(S46PortParametersOption)

S46LWContainerOption.add_may_contain(S46V4V6BindingOption, min_occurrence=0, max_occurrence=1)
S46LWContainerOption.add_may_contain(S46BROption, min_occurrence=1)
S46LWContainerOption.add_may_contain(S46PortParametersOption)
