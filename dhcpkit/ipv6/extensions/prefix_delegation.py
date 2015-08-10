"""
Implementation of Prefix Delegation options as specified in :rfc:`3633`.
"""

from ipaddress import IPv6Address, IPv6Network
from struct import unpack_from, pack

from dhcpkit.ipv6.options import register_option
from dhcpkit.ipv6.messages import SolicitMessage, AdvertiseMessage, RequestMessage, RenewMessage, \
    RebindMessage, ReleaseMessage, ReplyMessage
from dhcpkit.ipv6.options import Option, StatusCodeOption

OPTION_IA_PD = 25
OPTION_IAPREFIX = 26

STATUS_NOPREFIXAVAIL = 6


class IAPDOption(Option):
    """
    :rfc:`3633#section-9`

    The IA_PD option is used to carry a prefix delegation identity
    association, the parameters associated with the IA_PD and the
    prefixes associated with it.

    The format of the IA_PD option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |         OPTION_IA_PD          |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                         IAID (4 octets)                       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              T1                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              T2                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                          IA_PD-options                        .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_IA_PD (25).

    option-length
        12 + length of IA_PD-options field.

    IAID
        The unique identifier for this IA_PD; the IAID must be unique among the identifiers for all of this requesting
        router's IA_PDs.

    T1
        The time at which the requesting router should contact the delegating router from which the prefixes in the
        IA_PD were obtained to extend the lifetimes of the prefixes delegated to the IA_PD; T1 is a time duration
        relative to the current time expressed in units of seconds.

    T2
        The time at which the requesting router should contact any available delegating router to extend the lifetimes
        of the prefixes assigned to the IA_PD; T2 is a time duration relative to the current time expressed in units of
        seconds.

    IA_PD-options
        Options associated with this IA_PD.

    The IA_PD-options field encapsulates those options that are specific
    to this IA_PD.  For example, all of the IA_PD Prefix Options carrying
    the prefixes associated with this IA_PD are in the IA_PD-options
    field.

    An IA_PD option may only appear in the options area of a DHCP
    message.  A DHCP message may contain multiple IA_PD options.

    The status of any operations involving this IA_PD is indicated in a
    Status Code option in the IA_PD-options field.

    Note that an IA_PD has no explicit "lifetime" or "lease length" of
    its own.  When the valid lifetimes of all of the prefixes in a IA_PD
    have expired, the IA_PD can be considered as having expired.  T1 and
    T2 are included to give delegating routers explicit control over when
    a requesting router should contact the delegating router about a
    specific IA_PD.

    In a message sent by a requesting router to a delegating router,
    values in the T1 and T2 fields indicate the requesting router's
    preference for those parameters.  The requesting router sets T1 and
    T2 to zero if it has no preference for those values.  In a message
    sent by a delegating router to a requesting router, the requesting
    router MUST use the values in the T1 and T2 fields for the T1 and T2
    parameters.  The values in the T1 and T2 fields are the number of
    seconds until T1 and T2.

    The delegating router selects the T1 and T2 times to allow the
    requesting router to extend the lifetimes of any prefixes in the
    IA_PD before the lifetimes expire, even if the delegating router is
    unavailable for some short period of time.  Recommended values for T1
    and T2 are .5 and .8 times the shortest preferred lifetime of the
    prefixes in the IA_PD that the delegating router is willing to
    extend, respectively.  If the time at which the prefixes in an IA_PD
    are to be renewed is to be left to the discretion of the requesting
    router, the delegating router sets T1 and T2 to 0.

    If a delegating router receives an IA_PD with T1 greater than T2, and
    both T1 and T2 are greater than 0, the delegating router ignores the
    invalid values of T1 and T2 and processes the IA_PD as though the
    delegating router had set T1 and T2 to 0.

    If a requesting router receives an IA_PD with T1 greater than T2, and
    both T1 and T2 are greater than 0, the client discards the IA_PD
    option and processes the remainder of the message as though the
    delegating router had not included the IA_PD option.

    :type iaid: bytes
    :type t1: int
    :type t2: int
    :type options: list[Option]
    """

    option_type = OPTION_IA_PD

    def __init__(self, iaid: bytes=b'\x00\x00\x00\x00', t1: int=0, t2: int=0, options: [Option]=None):
        self.iaid = iaid
        """The unique identifier for this IA_PD"""

        self.t1 = t1
        """The time at which the client contacts the server to renew its prefixes"""

        self.t2 = t2
        """The time at which the client contacts any available server to rebind its prefixes"""

        self.options = options or []
        """The list of options contained in this IAPDOption"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.iaid, bytes) or len(self.iaid) != 4:
            raise ValueError("IAID must be four bytes")

        if not isinstance(self.t1, int) or not (0 <= self.t1 < 2 ** 32):
            raise ValueError("T1 must be an unsigned 32 bit integer")

        if not isinstance(self.t2, int) or not (0 <= self.t2 < 2 ** 32):
            raise ValueError("T2 must be an unsigned 32 bit integer")

        # Check if all options are allowed
        self.validate_contains(self.options)
        for option in self.options:
            option.validate()

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
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

        self.iaid = buffer[offset + my_offset:offset + my_offset + 4]
        my_offset += 4

        self.t1, self.t2 = unpack_from('!II', buffer, offset + my_offset)
        my_offset += 8

        # Parse the options
        self.options = []
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH4sII', self.option_type, len(options_buffer) + 12, self.iaid, self.t1, self.t2))
        buffer.extend(options_buffer)
        return buffer

    def get_options_of_type(self, klass: type) -> list:
        """
        Get all options that are subclasses of the given class.

        :param klass: The class to look for
        :returns: The list of options

        :type klass: T
        :rtype: list[T()]
        """
        return [option for option in self.options if isinstance(option, klass)]

    def get_option_of_type(self, klass: type) -> object or None:
        """
        Get the first option that is a subclass of the given class.

        :param klass: The class to look for
        :returns: The option or None

        :type klass: T
        :rtype: T()
        """
        for option in self.options:
            if isinstance(option, klass):
                return option

    def get_prefixes(self) -> [IPv6Network]:
        """
        Get all prefixes from IAPrefixOptions

        :returns: list if prefixes
        """
        return [suboption.prefix for suboption in self.get_options_of_type(IAPrefixOption)]


class IAPrefixOption(Option):
    """
    :rfc:`3633#section-10`

    The IA_PD Prefix option is used to specify IPv6 address prefixes
    associated with an IA_PD.  The IA_PD Prefix option must be
    encapsulated in the IA_PD-options field of an IA_PD option.

    The format of the IA_PD Prefix option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_IAPREFIX        |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                      preferred-lifetime                       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                        valid-lifetime                         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      | prefix-length |                                               |
      +-+-+-+-+-+-+-+-+          IPv6 prefix                          |
      |                           (16 octets)                         |
      |                                                               |
      |                                                               |
      |                                                               |
      |               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |               |                                               .
      +-+-+-+-+-+-+-+-+                                               .
      .                       IAprefix-options                        .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_IAPREFIX (26).

    option-length
        25 + length of IAprefix-options field.

    preferred-lifetime
     The recommended preferred lifetime for the IPv6 prefix in the option, expressed in units of seconds. A value of
     0xFFFFFFFF represents infinity.

    valid-lifetime
       The valid lifetime for the IPv6 prefix in the option, expressed in units of seconds.  A value of 0xFFFFFFFF
       represents infinity.

    prefix-length
        Length for this prefix in bits.

    IPv6-prefix
        An IPv6 prefix.

    IAprefix-options
        Options associated with this prefix.

    In a message sent by a requesting router to a delegating router, the
    values in the fields can be used to indicate the requesting router's
    preference for those values.  The requesting router may send a value
    of zero to indicate no preference.  A requesting router may set the
    IPv6 prefix field to zero and a given value in the prefix-length
    field to indicate a preference for the size of the prefix to be
    delegated.

    In a message sent by a delegating router the preferred and valid
    lifetimes should be set to the values of AdvPreferredLifetime and
    AdvValidLifetime as specified in section 6.2.1, "Router Configuration
    Variables" of :rfc:`2461` [4], unless administratively configured.

    A requesting router discards any prefixes for which the preferred
    lifetime is greater than the valid lifetime.  A delegating router
    ignores the lifetimes set by the requesting router if the preferred
    lifetime is greater than the valid lifetime and ignores the values
    for T1 and T2 set by the requesting router if those values are
    greater than the preferred lifetime.

    The values in the preferred and valid lifetimes are the number of
    seconds remaining for each lifetime.

    An IA_PD Prefix option may appear only in an IA_PD option.  More than
    one IA_PD Prefix Option can appear in a single IA_PD option.

    The status of any operations involving this IA_PD Prefix option is
    indicated in a Status Code option in the IAprefix-options field.

    :type preferred_lifetime: int
    :type valid_lifetime: int
    :type prefix: IPv6Network
    :type options: list[Option]
    """

    option_type = OPTION_IAPREFIX

    def __init__(self, prefix: IPv6Network=None, preferred_lifetime: int=0, valid_lifetime: int=0,
                 options: [Option]=None):
        self.prefix = prefix
        """The IPv6 prefix"""

        self.preferred_lifetime = preferred_lifetime
        """The preferred lifetime of this IPv6 prefix"""

        self.valid_lifetime = valid_lifetime
        """The valid lifetime of this IPv6 prefix"""

        self.options = options or []
        """The list of options related to this IAPrefixOption"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.preferred_lifetime, int) or not (0 <= self.preferred_lifetime < 2 ** 32):
            raise ValueError("Preferred lifetime must be an unsigned 32 bit integer")

        if not isinstance(self.valid_lifetime, int) or not (0 <= self.valid_lifetime < 2 ** 32):
            raise ValueError("Valid lifetime must be an unsigned 32 bit integer")

        if not isinstance(self.prefix, IPv6Network) or self.prefix.is_link_local or self.prefix.is_loopback \
                or self.prefix.is_multicast:
            raise ValueError("Prefix must be a routable IPv6 prefix")

        # Check if all options are allowed
        self.validate_contains(self.options)
        for option in self.options:
            option.validate()

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
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

        self.preferred_lifetime, self.valid_lifetime = unpack_from('!II', buffer, offset=offset + my_offset)
        my_offset += 8

        prefix_length = buffer[offset + my_offset]
        my_offset += 1

        address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        # Combine address and prefix length into prefix
        self.prefix = IPv6Network('{!s}/{:d}'.format(address, prefix_length))

        # Parse the options
        self.options = []
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HHIIB', self.option_type, len(options_buffer) + 25,
                           self.preferred_lifetime, self.valid_lifetime, self.prefix.prefixlen))
        buffer.extend(self.prefix.network_address.packed)
        buffer.extend(options_buffer)
        return buffer

# Add options to the registry
register_option(IAPDOption)
register_option(IAPrefixOption)

# Register where these options may occur
SolicitMessage.add_may_contain(IAPDOption)
AdvertiseMessage.add_may_contain(IAPDOption)
RequestMessage.add_may_contain(IAPDOption)
RenewMessage.add_may_contain(IAPDOption)
RebindMessage.add_may_contain(IAPDOption)
ReleaseMessage.add_may_contain(IAPDOption)
ReplyMessage.add_may_contain(IAPDOption)

IAPDOption.add_may_contain(IAPrefixOption)
IAPDOption.add_may_contain(StatusCodeOption, 0, 1)

IAPrefixOption.add_may_contain(StatusCodeOption, 0, 1)
