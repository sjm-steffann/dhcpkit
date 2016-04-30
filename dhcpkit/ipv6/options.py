"""
Classes and constants for the options defined in :rfc:`3315`
"""
from functools import total_ordering
from ipaddress import IPv6Address
from struct import unpack_from, pack

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.messages import Message, SolicitMessage, AdvertiseMessage, RequestMessage, ConfirmMessage, \
    RenewMessage, RebindMessage, DeclineMessage, ReleaseMessage, ReplyMessage, ReconfigureMessage, \
    InformationRequestMessage, RelayForwardMessage, RelayReplyMessage
from dhcpkit.protocol_element import ProtocolElement

OPTION_CLIENTID = 1
OPTION_SERVERID = 2
OPTION_IA_NA = 3
OPTION_IA_TA = 4
OPTION_IAADDR = 5
OPTION_ORO = 6
OPTION_PREFERENCE = 7
OPTION_ELAPSED_TIME = 8
OPTION_RELAY_MSG = 9
OPTION_AUTH = 11
OPTION_UNICAST = 12
OPTION_STATUS_CODE = 13
OPTION_RAPID_COMMIT = 14
OPTION_USER_CLASS = 15
OPTION_VENDOR_CLASS = 16
OPTION_VENDOR_OPTS = 17
OPTION_INTERFACE_ID = 18
OPTION_RECONF_MSG = 19
OPTION_RECONF_ACCEPT = 20

# IANA has recorded the status codes defined in the following table.
# IANA will manage the definition of additional status codes in the
# future.
#
# Name         Code Description
# ----------   ---- -----------
# Success         0 Success.
# UnspecFail      1 Failure, reason unspecified; this
#                   status code is sent by either a client
#                   or a server to indicate a failure
#                   not explicitly specified in this
#                   document.
# NoAddrsAvail    2 Server has no addresses available to assign to
#                   the IA(s).
# NoBinding       3 Client record (binding) unavailable.
# NotOnLink       4 The prefix for the address is not appropriate for
#                   the link to which the client is attached.
# UseMulticast    5 Sent by a server to a client to force the
#                   client to send messages to the server.
#                   using the All_DHCP_Relay_Agents_and_Servers
#                   address.

STATUS_SUCCESS = 0
STATUS_UNSPECFAIL = 1
STATUS_NOADDRSAVAIL = 2
STATUS_NOBINDING = 3
STATUS_NOTONLINK = 4
STATUS_USEMULTICAST = 5


# This subclass remains abstract
# noinspection PyAbstractClass
class Option(ProtocolElement):
    """
    :rfc:`3315#section-22.1`

    The format of DHCP options is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          option-code          |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                          option-data                          |
      |                      (option-len octets)                      |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        An unsigned integer identifying the specific option type carried in this option.

    option-len
        An unsigned integer giving the length of the option-data field in this option in octets.

    option-data
        The data for the option; the format of this data depends on the definition of the option.

    DHCPv6 options are scoped by using encapsulation.  Some options apply
    generally to the client, some are specific to an IA, and some are
    specific to the addresses within an IA.  These latter two cases are
    discussed in sections 22.4 and 22.6.

    :type option_type: int
    """

    # This needs to be overwritten in subclasses
    option_type = 0

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int = 0) -> type:
        """
        Return the appropriate subclass from the registry, or UnknownOption if no subclass is registered.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :return: The best known class for this option data
        """
        from dhcpkit.ipv6.option_registry import option_registry
        option_type = unpack_from('!H', buffer, offset=offset)[0]
        return option_registry.get(option_type, UnknownOption)

    def parse_option_header(self, buffer: bytes, offset: int = 0, length: int = None) -> (int, int):
        """
        Parse the option code and length from the buffer and perform some basic validation.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer and the value of the option-len field
        """
        option_type, option_len = unpack_from('!HH', buffer, offset=offset)
        my_offset = 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain {} data'.format(self.__class__.__name__))

        if length is not None and option_len + my_offset > length:
            raise ValueError('This option is longer than the available buffer')

        return my_offset, option_len


class UnknownOption(Option):
    """
    Container for raw option content for cases where we don't know how to decode the option.

    :type option_data: bytes
    """

    def __init__(self, option_type: int = 0, option_data: bytes = b''):
        self.option_type = option_type
        """The type number of this option"""

        self.option_data = option_data
        """The option data as bytes"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.option_type, int) or not (0 <= self.option_type < 2 ** 16):
            raise ValueError("Option type must be an unsigned 16 bit integer")

        if not isinstance(self.option_data, bytes):
            raise ValueError("Option data must be sequence of bytes")

        if len(self.option_data) >= 2 ** 16:
            raise ValueError("Option data cannot be longer than 65535 bytes")

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

        self.option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.option_data = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        return pack('!HH', self.option_type, len(self.option_data)) + self.option_data


class ClientIdOption(Option):
    """
    :rfc:`3315#section-22.2`

    The Client Identifier option is used to carry a DUID (see section 9)
    identifying a client between a client and a server.  The format of
    the Client Identifier option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_CLIENTID        |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                              DUID                             .
      .                        (variable length)                      .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_CLIENTID (1).

    option-len
        Length of DUID in octets.

    DUID
        The DUID for the client.

    :type duid: DUID
    """

    option_type = OPTION_CLIENTID

    def __init__(self, duid: DUID = None):
        self.duid = duid
        """The DUID of the client"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.duid, DUID):
            raise ValueError("DUID is not a DUID object")

        self.duid.validate()

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

        duid_len, self.duid = DUID.parse(buffer, offset=offset + my_offset, length=option_len)
        my_offset += duid_len

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        duid_buffer = self.duid.save()
        return pack('!HH', self.option_type, len(duid_buffer)) + duid_buffer


class ServerIdOption(Option):
    """
    :rfc:`3315#section-22.3`

    The Server Identifier option is used to carry a DUID (see section 9)
    identifying a server between a client and a server.  The format of
    the Server Identifier option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_SERVERID        |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                              DUID                             .
      .                        (variable length)                      .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_SERVERID (2).

    option-len
        Length of DUID in octets.

    DUID
        The DUID for the server.

    :type duid: DUID
    """

    option_type = OPTION_SERVERID

    def __init__(self, duid: DUID = None):
        self.duid = duid
        """The DUID of the server"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.duid, DUID):
            raise ValueError("DUID is not a DUID object")

        self.duid.validate()

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

        duid_len, self.duid = DUID.parse(buffer, offset=offset + my_offset, length=option_len)
        my_offset += duid_len

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        duid_buffer = self.duid.save()
        return pack('!HH', self.option_type, len(duid_buffer)) + duid_buffer


@total_ordering
class IANAOption(Option):
    """
    :rfc:`3315#section-22.4`

    The Identity Association for Non-temporary Addresses option (IA_NA
    option) is used to carry an IA_NA, the parameters associated with the
    IA_NA, and the non-temporary addresses associated with the IA_NA.

    Addresses appearing in an IA_NA option are not temporary addresses
    (see section 22.5).

    The format of the IA_NA option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          OPTION_IA_NA         |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                        IAID (4 octets)                        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              T1                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              T2                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .                         IA_NA-options                         .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_IA_NA (3).

    option-len
        12 + length of IA_NA-options field.

    IAID
        The unique identifier for this IA_NA; the IAID must be unique among the identifiers for all of this client's
        IA_NAs.  The number space for IA_NA IAIDs is separate from the number space for IA_TA IAIDs.

    T1
        The time at which the client contacts the server from which the addresses in the IA_NA were obtained to extend
        the lifetimes of the addresses assigned to the IA_NA; T1 is a time duration relative to the current time
        expressed in units of seconds.

    T2
        The time at which the client contacts any available server to extend the lifetimes of the addresses assigned to
        the IA_NA; T2 is a time duration relative to the current time expressed in units of seconds.

    IA_NA-options
        Options associated with this IA_NA.

    The IA_NA-options field encapsulates those options that are specific
    to this IA_NA.  For example, all of the IA Address Options carrying
    the addresses associated with this IA_NA are in the IA_NA-options
    field.

    An IA_NA option may only appear in the options area of a DHCP
    message.  A DHCP message may contain multiple IA_NA options.

    The status of any operations involving this IA_NA is indicated in a
    Status Code option in the IA_NA-options field.

    Note that an IA_NA has no explicit "lifetime" or "lease length" of
    its own.  When the valid lifetimes of all of the addresses in an
    IA_NA have expired, the IA_NA can be considered as having expired.
    T1 and T2 are included to give servers explicit control over when a
    client recontacts the server about a specific IA_NA.

    In a message sent by a client to a server, values in the T1 and T2
    fields indicate the client's preference for those parameters.  The
    client sets T1 and T2 to 0 if it has no preference for those values.
    In a message sent by a server to a client, the client MUST use the
    values in the T1 and T2 fields for the T1 and T2 parameters, unless
    those values in those fields are 0.  The values in the T1 and T2
    fields are the number of seconds until T1 and T2.

    The server selects the T1 and T2 times to allow the client to extend
    the lifetimes of any addresses in the IA_NA before the lifetimes
    expire, even if the server is unavailable for some short period of
    time.  Recommended values for T1 and T2 are .5 and .8 times the
    shortest preferred lifetime of the addresses in the IA that the
    server is willing to extend, respectively.  If the "shortest"
    preferred lifetime is 0xffffffff ("infinity"), the recommended T1 and
    T2 values are also 0xffffffff.  If the time at which the addresses in
    an IA_NA are to be renewed is to be left to the discretion of the
    client, the server sets T1 and T2 to 0.

    If a server receives an IA_NA with T1 greater than T2, and both T1
    and T2 are greater than 0, the server ignores the invalid values of
    T1 and T2 and processes the IA_NA as though the client had set T1 and
    T2 to 0.

    If a client receives an IA_NA with T1 greater than T2, and both T1
    and T2 are greater than 0, the client discards the IA_NA option and
    processes the remainder of the message as though the server had not
    included the invalid IA_NA option.

    Care should be taken in setting T1 or T2 to 0xffffffff ("infinity").
    A client will never attempt to extend the lifetimes of any addresses
    in an IA with T1 set to 0xffffffff.  A client will never attempt to
    use a Rebind message to locate a different server to extend the
    lifetimes of any addresses in an IA with T2 set to 0xffffffff.

    :type iaid: bytes
    :type t1: int
    :type t2: int
    :type options: list[Option]
    """

    option_type = OPTION_IA_NA

    def __init__(self, iaid: bytes = b'\x00\x00\x00\x00', t1: int = 0, t2: int = 0, options: [Option] = None):
        self.iaid = iaid
        """The unique identifier for this IA_NA"""

        self.t1 = t1
        """The time at which the client contacts the server to renew its addresses"""

        self.t2 = t2
        """The time at which the client contacts any available server to rebind its addresses"""

        self.options = options or []
        """The list of options contained in this IANAOption"""

    # IANAObjects are sortable by IAID
    def __lt__(self, other):
        if not isinstance(other, IANAOption):
            return NotImplemented

        return self.iaid < other.iaid

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
        :rtype: T() or None
        """
        for option in self.options:
            if isinstance(option, klass):
                return option

    def get_addresses(self) -> [IPv6Address]:
        """
        Get all addresses from IAAddressOptions

        :returns: list if addresses
        """
        return [suboption.address for suboption in self.get_options_of_type(IAAddressOption)]


@total_ordering
class IATAOption(Option):
    """
    :rfc:`3315#section-22.5`

    The Identity Association for the Temporary Addresses (IA_TA) option
    is used to carry an IA_TA, the parameters associated with the IA_TA
    and the addresses associated with the IA_TA.  All of the addresses in
    this option are used by the client as temporary addresses, as defined
    in :rfc:`3041` [12].  The format of the IA_TA option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |         OPTION_IA_TA          |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                        IAID (4 octets)                        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .                         IA_TA-options                         .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_IA_TA (4).

    option-len
        4 + length of IA_TA-options field.

    IAID
        The unique identifier for this IA_TA; the IAID must be unique among the identifiers for all of this client's
        IA_TAs.  The number space for IA_TA IAIDs is separate from the number space for IA_NA IAIDs.

    IA_TA-options
        Options associated with this IA_TA.

    The IA_TA-Options field encapsulates those options that are specific
    to this IA_TA.  For example, all of the IA Address Options carrying
    the addresses associated with this IA_TA are in the IA_TA-options
    field.

    Each IA_TA carries one "set" of temporary addresses; that is, at most
    one address from each prefix assigned to the link to which the client
    is attached.

    An IA_TA option may only appear in the options area of a DHCP
    message.  A DHCP message may contain multiple IA_TA options.

    The status of any operations involving this IA_TA is indicated in a
    Status Code option in the IA_TA-options field.

    Note that an IA has no explicit "lifetime" or "lease length" of its
    own.  When the valid lifetimes of all of the addresses in an IA_TA
    have expired, the IA can be considered as having expired.

    An IA_TA option does not include values for T1 and T2.  A client MAY
    request that the lifetimes on temporary addresses be extended by
    including the addresses in a IA_TA option sent in a Renew or Rebind
    message to a server.  For example, a client would request an
    extension on the lifetime of a temporary address to allow an
    application to continue to use an established TCP connection.

    The client obtains new temporary addresses by sending an IA_TA option
    with a new IAID to a server.  Requesting new temporary addresses from
    the server is the equivalent of generating new temporary addresses as
    described in :rfc:`3041`.  The server will generate new temporary
    addresses and return them to the client.  The client should request
    new temporary addresses before the lifetimes on the previously
    assigned addresses expire.

    A server MUST return the same set of temporary address for the same
    IA_TA (as identified by the IAID) as long as those addresses are
    still valid.  After the lifetimes of the addresses in an IA_TA have
    expired, the IAID may be reused to identify a new IA_TA with new
    temporary addresses.

    This option MAY appear in a Confirm message if the lifetimes on the
    temporary addresses in the associated IA have not expired.

    :type iaid: bytes
    :type options: list[Option]
    """

    option_type = OPTION_IA_TA

    def __init__(self, iaid: bytes = b'\x00\x00\x00\x00', options: [Option] = None):
        self.iaid = iaid
        """The unique identifier for this IA_TA"""

        self.options = options or []
        """The list of options contained in this IATAOption"""

    # IATAObjects are sortable by IAID
    def __lt__(self, other):
        if not isinstance(other, IATAOption):
            return NotImplemented

        return self.iaid < other.iaid

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.iaid, bytes) or len(self.iaid) != 4:
            raise ValueError("IAID must be four bytes")

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

        self.iaid = buffer[offset + my_offset:offset + my_offset + 4]
        my_offset += 4

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
        buffer.extend(pack('!HH4s', self.option_type, len(options_buffer) + 4, self.iaid))
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
        :rtype: T() or None
        """
        for option in self.options:
            if isinstance(option, klass):
                return option

    def get_addresses(self) -> [IPv6Address]:
        """
        Get all addresses from IAAddressOptions

        :returns: list if addresses
        """
        return [suboption.address for suboption in self.get_options_of_type(IAAddressOption)]


class IAAddressOption(Option):
    """
    :rfc:`3315#section-22.6`

    The IA Address option is used to specify IPv6 addresses associated
    with an IA_NA or an IA_TA.  The IA Address option must be
    encapsulated in the Options field of an IA_NA or IA_TA option.  The
    Options field encapsulates those options that are specific to this
    address.

    The format of the IA Address option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          OPTION_IAADDR        |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                         IPv6 address                          |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                      preferred-lifetime                       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                        valid-lifetime                         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                        IAaddr-options                         .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_IAADDR (5).

    option-len
        24 + length of IAaddr-options field.

    IPv6 address
        An IPv6 address.

    preferred-lifetime
        The preferred lifetime for the IPv6 address in the option, expressed in units of seconds.

    valid-lifetime
        The valid lifetime for the IPv6 address in the option, expressed in units of seconds.

    IAaddr-options
        Options associated with this address.

    In a message sent by a client to a server, values in the preferred
    and valid lifetime fields indicate the client's preference for those
    parameters.  The client may send 0 if it has no preference for the
    preferred and valid lifetimes.  In a message sent by a server to a
    client, the client MUST use the values in the preferred and valid
    lifetime fields for the preferred and valid lifetimes.  The values in
    the preferred and valid lifetimes are the number of seconds remaining
    in each lifetime.

    A client discards any addresses for which the preferred lifetime is
    greater than the valid lifetime.  A server ignores the lifetimes set
    by the client if the preferred lifetime is greater than the valid
    lifetime and ignores the values for T1 and T2 set by the client if
    those values are greater than the preferred lifetime.

    Care should be taken in setting the valid lifetime of an address to
    0xffffffff ("infinity"), which amounts to a permanent assignment of
    an address to a client.

    An IA Address option may appear only in an IA_NA option or an IA_TA
    option.  More than one IA Address Option can appear in an IA_NA
    option or an IA_TA option.

    The status of any operations involving this IA Address is indicated
    in a Status Code option in the IAaddr-options field.

    :type address: IPv6Address
    :type preferred_lifetime: int
    :type valid_lifetime: int
    :type options: list[Option]
    """

    option_type = OPTION_IAADDR

    def __init__(self, address: IPv6Address = None, preferred_lifetime: int = 0, valid_lifetime: int = 0,
                 options: [Option] = None):
        self.address = address
        """The IPv6 address"""

        self.preferred_lifetime = preferred_lifetime
        """The preferred lifetime of this IPv6 address"""

        self.valid_lifetime = valid_lifetime
        """The valid lifetime of this IPv6 address"""

        self.options = options or []
        """The list of options related to this IAAddressOption"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.address, IPv6Address) or self.address.is_link_local or self.address.is_loopback \
                or self.address.is_multicast:
            raise ValueError("Address must be a routable IPv6 address")

        if not isinstance(self.preferred_lifetime, int) or not (0 <= self.preferred_lifetime < 2 ** 32):
            raise ValueError("Preferred lifetime must be an unsigned 32 bit integer")

        if not isinstance(self.valid_lifetime, int) or not (0 <= self.valid_lifetime < 2 ** 32):
            raise ValueError("Valid lifetime must be an unsigned 32 bit integer")

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

        self.address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        self.preferred_lifetime, self.valid_lifetime = unpack_from('!II', buffer, offset + my_offset)
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
        buffer.extend(pack('!HH', self.option_type, len(options_buffer) + 24))
        buffer.extend(self.address.packed)
        buffer.extend(pack('!II', self.preferred_lifetime, self.valid_lifetime))
        buffer.extend(options_buffer)
        return buffer


class OptionRequestOption(Option):
    """
    :rfc:`3315#section-22.7`

    The Option Request option is used to identify a list of options in a
    message between a client and a server.  The format of the Option
    Request option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |           OPTION_ORO          |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    requested-option-code-1    |    requested-option-code-2    |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_ORO (6).

    option-len
        2 * number of requested options.

    requested-option-code-n
        The option code for an option requested by the client.

    A client MAY include an Option Request option in a Solicit, Request,
    Renew, Rebind, Confirm or Information-request message to inform the
    server about options the client wants the server to send to the
    client.  A server MAY include an Option Request option in a
    Reconfigure option to indicate which options the client should
    request from the server.

    :type requested_options: list[int]
    """

    option_type = OPTION_ORO

    def __init__(self, requested_options: [int] = None):
        self.requested_options = requested_options or []
        """The list of option type numbers that the client is interested in"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.requested_options, list):
            raise ValueError('Requested options must be a list')

        for option_code in self.requested_options:
            if not isinstance(option_code, int) or not (0 <= option_code < 2 ** 16):
                raise ValueError("Requested options must be a list of unsigned 16 bit integers")

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

        if option_len % 2 != 0:
            raise ValueError('Invalid option length')

        self.requested_options = list(unpack_from('!{}H'.format(option_len // 2), buffer, offset + my_offset))
        my_offset += option_len

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.requested_options) * 2))
        buffer.extend(pack('!{}H'.format(len(self.requested_options)), *self.requested_options))
        return buffer


class PreferenceOption(Option):
    """
    :rfc:`3315#section-22.8`

    The Preference option is sent by a server to a client to affect the
    selection of a server by the client.

    The format of the Preference option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |       OPTION_PREFERENCE       |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |  pref-value   |
      +-+-+-+-+-+-+-+-+

    option-code
        OPTION_PREFERENCE (7).

    option-len
        1.

    pref-value
        The preference value for the server in this message.

    A server MAY include a Preference option in an Advertise message to
    control the selection of a server by the client.  See section 17.1.3
    for the use of the Preference option by the client and the
    interpretation of Preference option data value.

    :type preference: int
    """

    option_type = OPTION_PREFERENCE

    def __init__(self, preference: int = 0):
        self.preference = preference
        """The preference that the client should treat this server with"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.preference, int) or not (0 <= self.preference < 2 ** 8):
            raise ValueError("Preference must be an unsigned 8 bit integer")

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

        if option_len != 1:
            raise ValueError('Preference Options must have length 1')

        self.preference = buffer[offset + my_offset]
        my_offset += 1

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()
        return pack('!HHB', self.option_type, 1, self.preference)


class ElapsedTimeOption(Option):
    """
    :rfc:`3315#section-22.9`

    ::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_ELAPSED_TIME      |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          elapsed-time         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_ELAPSED_TIME (8).

    option-len
        2.

    elapsed-time
        The amount of time since the client began its current DHCP transaction.  This time is expressed in hundredths
        of a second (10^-2 seconds).

    A client MUST include an Elapsed Time option in messages to indicate
    how long the client has been trying to complete a DHCP message
    exchange.  The elapsed time is measured from the time at which the
    client sent the first message in the message exchange, and the
    elapsed-time field is set to 0 in the first message in the message
    exchange.  Servers and Relay Agents use the data value in this option
    as input to policy controlling how a server responds to a client
    message.  For example, the elapsed time option allows a secondary
    DHCP server to respond to a request when a primary server has not
    answered in a reasonable time.  The elapsed time value is an
    unsigned, 16 bit integer.  The client uses the value 0xffff to
    represent any elapsed time values greater than the largest time value
    that can be represented in the Elapsed Time option.

    :type elapsed_time: int
    """

    option_type = OPTION_ELAPSED_TIME

    def __init__(self, elapsed_time: int = 0):
        self.elapsed_time = elapsed_time
        """The amount of time since the client began its current DHCP transaction"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.elapsed_time, int) or not (0 <= self.elapsed_time < 2 ** 16):
            raise ValueError("Elapsed time must be an unsigned 16 bit integer")

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

        if option_len != 2:
            raise ValueError('Elapsed Time Options must have length 2')

        self.elapsed_time = unpack_from('!H', buffer, offset=offset + my_offset)[0]
        my_offset += 2

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()
        return pack('!HHH', self.option_type, 2, self.elapsed_time)


class RelayMessageOption(Option):
    """
    :rfc:`3315#section-22.10`

    The Relay Message option carries a DHCP message in a Relay-forward or
    Relay-reply message.

    The format of the Relay Message option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |        OPTION_RELAY_MSG       |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      .                       DHCP-relay-message                      .
      .                                                               .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_RELAY_MSG (9)

    option-len
        Length of DHCP-relay-message

    DHCP-relay-message
        In a Relay-forward message, the received message, relayed verbatim to the next relay agent or server; in a
        Relay-reply message, the message to be copied and relayed to the relay agent or client whose address is in the
        peer-address field of the Relay-reply message

    :type relayed_message: Message
    """

    option_type = OPTION_RELAY_MSG

    def __init__(self, relayed_message: Message = None):
        self.relayed_message = relayed_message
        """The relayed DHCP message"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.relayed_message, Message):
            raise ValueError("Relayed message must be an IPv6 DHCP message")

        if not self.may_contain(self.relayed_message):
            raise ValueError("{} cannot contain {}".format(self.__class__.__name__,
                                                           self.relayed_message.__class__.__name__))

        self.relayed_message.validate()

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

        message_len, self.relayed_message = Message.parse(buffer, offset=offset + my_offset, length=option_len)
        my_offset += option_len

        if message_len != option_len:
            raise ValueError('The embedded message has a different length than the Relay Message Option', message_len,
                             option_len)

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        message = self.relayed_message.save()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(message)))
        buffer.extend(message)
        return buffer


class AuthenticationOption(Option):
    """
    :rfc:`3315#section-22.11`

    The Authentication option carries authentication information to
    authenticate the identity and contents of DHCP messages.  The use of
    the Authentication option is described in section 21.  The format of
    the Authentication option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          OPTION_AUTH          |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |   protocol    |   algorithm   |      RDM      |               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+               |
      |                                                               |
      |          replay detection (64 bits)           +-+-+-+-+-+-+-+-+
      |                                               |   auth-info   |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+               |
      .                   authentication information                  .
      .                       (variable length)                       .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_AUTH (11).

    option-len
        11 + length of authentication information field.

    protocol
        The authentication protocol used in this authentication option.

    algorithm
        The algorithm used in the authentication protocol.

    RDM
        The replay detection method used in this authentication option.

    Replay detection
        The replay detection information for the RDM.

    authentication information
        The authentication information, as specified by the protocol and algorithm used in this authentication option.

    :type protocol: int
    :type algorithm: int
    :type rdm: int
    :type replay_detection: bytes
    :type auth_info: bytes
    """

    option_type = OPTION_AUTH

    def __init__(self, protocol: int = 0, algorithm: int = 0, rdm: int = 0,
                 replay_detection: bytes = b'\x00\x00\x00\x00\x00\x00\x00\x00', auth_info: bytes = b''):
        self.protocol = protocol
        self.algorithm = algorithm
        self.rdm = rdm
        self.replay_detection = replay_detection
        self.auth_info = auth_info

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.protocol, int) or not (0 <= self.protocol < 2 ** 8):
            raise ValueError("Protocol must be an unsigned 8 bit integer")

        if not isinstance(self.algorithm, int) or not (0 <= self.algorithm < 2 ** 8):
            raise ValueError("Algorithm must be an unsigned 8 bit integer")

        if not isinstance(self.rdm, int) or not (0 <= self.rdm < 2 ** 8):
            raise ValueError("RDM must be an unsigned 8 bit integer")

        if not isinstance(self.replay_detection, bytes) or len(self.replay_detection) != 8:
            raise ValueError("Replay detection must contain 8 bytes")

        if not isinstance(self.auth_info, bytes):
            raise ValueError("Authentication info must contain bytes")

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

        self.protocol = buffer[offset + my_offset]
        self.algorithm = buffer[offset + my_offset + 1]
        self.rdm = buffer[offset + my_offset + 2]
        my_offset += 3

        self.replay_detection = buffer[offset + my_offset:offset + my_offset + 8]
        my_offset += 8

        auth_data_length = option_len - 11
        self.auth_info = buffer[offset + my_offset:offset + my_offset + auth_data_length]
        my_offset += auth_data_length

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        buffer = bytearray()
        buffer.extend(pack('!HHBBB', self.option_type, len(self.auth_info) + 11,
                           self.protocol, self.algorithm, self.rdm))
        buffer.extend(self.replay_detection)
        buffer.extend(self.auth_info)
        return buffer


class ServerUnicastOption(Option):
    """
    :rfc:`3315#section-22.12`

    The server sends this option to a client to indicate to the client
    that it is allowed to unicast messages to the server.  The format of
    the Server Unicast option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          OPTION_UNICAST       |        option-len             |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                                                               |
      |                       server-address                          |
      |                                                               |
      |                                                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_UNICAST (12).

    option-len
        16.

    server-address
        The IP address to which the client should send messages delivered using unicast.

    The server specifies the IPv6 address to which the client is to send
    unicast messages in the server-address field.  When a client receives
    this option, where permissible and appropriate, the client sends
    messages directly to the server using the IPv6 address specified in
    the server-address field of the option.

    When the server sends a Unicast option to the client, some messages
    from the client will not be relayed by Relay Agents, and will not
    include Relay Agent options from the Relay Agents.  Therefore, a
    server should only send a Unicast option to a client when Relay
    Agents are not sending Relay Agent options.  A DHCP server rejects
    any messages sent inappropriately using unicast to ensure that
    messages are relayed by Relay Agents when Relay Agent options are in
    use.

    Details about when the client may send messages to the server using
    unicast are in section 18.

    :type server_address: IPv6Address
    """

    option_type = OPTION_UNICAST

    def __init__(self, server_address: IPv6Address = None):
        self.server_address = server_address
        """The global unicast address that the client may contact this server on"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.server_address, IPv6Address) or self.server_address.is_loopback \
                or self.server_address.is_multicast or self.server_address.is_unspecified:
            raise ValueError("Server address must be a valid IPv6 address")

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

        if option_len != 16:
            raise ValueError('Server Unicast Options must have length 16')

        self.server_address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, 16))
        buffer.extend(self.server_address.packed)
        return buffer


class StatusCodeOption(Option):
    """
    :rfc:`3315#section-22.13`

    This option returns a status indication related to the DHCP message
    or option in which it appears.  The format of the Status Code option
    is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |       OPTION_STATUS_CODE      |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          status-code          |                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
      .                                                               .
      .                        status-message                         .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_STATUS_CODE (13).

    option-len
        2 + length of status-message.

    status-code
        The numeric code for the status encoded in this option.  The status codes are defined in section 24.4.

    status-message
        A UTF-8 encoded text string suitable for display to an end user, which MUST NOT be null-terminated.

    A Status Code option may appear in the options field of a DHCP
    message and/or in the options field of another option.  If the Status
    Code option does not appear in a message in which the option could
    appear, the status of the message is assumed to be Success.

    :type status_code: int
    :type status_message: str
    """

    option_type = OPTION_STATUS_CODE

    def __init__(self, status_code: int = 0, status_message: str = ''):
        self.status_code = status_code
        """The status code"""

        self.status_message = status_message
        """The status message suitable for display to an end user"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.status_code, int) or not (0 <= self.status_code < 2 ** 16):
            raise ValueError("Status code must be an unsigned 16 bit integer")

        if not isinstance(self.status_message, str):
            raise ValueError("Status message must be a string")

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

        self.status_code = unpack_from('!H', buffer, offset=offset + my_offset)[0]
        my_offset += 2

        message_length = option_len - 2
        self.status_message = bytes(buffer[offset + my_offset:offset + my_offset + message_length]).decode('utf-8')
        my_offset += message_length

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()
        message_bytes = self.status_message.encode('utf-8')

        buffer = bytearray()
        buffer.extend(pack('!HHH', self.option_type, len(message_bytes) + 2, self.status_code))
        buffer.extend(message_bytes)
        return buffer


class RapidCommitOption(Option):
    """
    :rfc:`3315#section-22.14`

    The Rapid Commit option is used to signal the use of the two message
    exchange for address assignment.  The format of the Rapid Commit
    option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_RAPID_COMMIT      |               0               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_RAPID_COMMIT (14).

    option-len
        0.

    A client MAY include this option in a Solicit message if the client
    is prepared to perform the Solicit-Reply message exchange described
    in section 17.1.1.

    A server MUST include this option in a Reply message sent in response
    to a Solicit message when completing the Solicit-Reply message
    exchange.

    **DISCUSSION:**

    Each server that responds with a Reply to a Solicit that includes
    a Rapid Commit option will commit the assigned addresses in the
    Reply message to the client, and will not receive any confirmation
    that the client has received the Reply message.  Therefore, if
    more than one server responds to a Solicit that includes a Rapid
    Commit option, some servers will commit addresses that are not
    actually used by the client.

    The problem of unused addresses can be minimized, for example, by
    designing the DHCP service so that only one server responds to the
    Solicit or by using relatively short lifetimes for assigned
    addresses.
    """

    option_type = OPTION_RAPID_COMMIT

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

        if option_len != 0:
            raise ValueError('Rapid Commit Options must have length 0')

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HH', self.option_type, 0)


class UserClassOption(Option):
    """
    :rfc:`3315#section-22.15`

    The User Class option is used by a client to identify the type or
    category of user or applications it represents.

    The format of the User Class option is::

       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |       OPTION_USER_CLASS       |          option-len           |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                          user-class-data                      .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_USER_CLASS (15).

    option-len
        Length of user class data field.

    user-class-data
        The user classes carried by the client.

    The information contained in the data area of this option is
    contained in one or more opaque fields that represent the user class
    or classes of which the client is a member.  A server selects
    configuration information for the client based on the classes
    identified in this option.  For example, the User Class option can be
    used to configure all clients of people in the accounting department
    with a different printer than clients of people in the marketing
    department.  The user class information carried in this option MUST
    be configurable on the client.

    The data area of the user class option MUST contain one or more
    instances of user class data.  Each instance of the user class data
    is formatted as follows::

      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+
      |        user-class-len         |          opaque-data          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+

    The user-class-len is two octets long and specifies the length of the
    opaque user class data in network byte order.

    A server interprets the classes identified in this option according
    to its configuration to select the appropriate configuration
    information for the client.  A server may use only those user classes
    that it is configured to interpret in selecting configuration
    information for a client and ignore any other user classes.  In
    response to a message containing a User Class option, a server
    includes a User Class option containing those classes that were
    successfully interpreted by the server, so that the client can be
    informed of the classes interpreted by the server.

    :type user_classes: list[bytes]
    """

    option_type = OPTION_USER_CLASS

    def __init__(self, user_classes: [bytes] = None):
        self.user_classes = user_classes or []
        """The list of user classes"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.user_classes, list):
            raise ValueError("User classes must be a list")

        for user_class in self.user_classes:
            if not isinstance(user_class, bytes) or len(user_class) >= 2 ** 16:
                raise ValueError("User classes must be a list of bytes")

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

        # Parse the user classes
        self.user_classes = []
        """:type: [bytes]"""

        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            user_class_length = unpack_from('!H', buffer, offset=offset + my_offset)[0]
            my_offset += 2

            user_class = buffer[offset + my_offset:offset + my_offset + user_class_length]
            self.user_classes.append(user_class)
            my_offset += user_class_length

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed user classes')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        user_classes_bytes = bytearray()
        for user_class in self.user_classes:
            user_classes_bytes.extend(pack('!H', len(user_class)))
            user_classes_bytes.extend(user_class)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(user_classes_bytes)))
        buffer.extend(user_classes_bytes)
        return buffer


class VendorClassOption(Option):
    """
    :rfc:`3315#section-22.16`

    This option is used by a client to identify the vendor that
    manufactured the hardware on which the client is running.  The
    information contained in the data area of this option is contained in
    one or more opaque fields that identify details of the hardware
    configuration.  The format of the Vendor Class option is::

       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_VENDOR_CLASS      |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                       enterprise-number                       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                       vendor-class-data                       .
      .                             . . .                             .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_VENDOR_CLASS (16).

    option-len
        4 + length of vendor class data field.

    enterprise-number
        The vendor's registered Enterprise Number as registered with IANA [6].

    vendor-class-data
        The hardware configuration of the host on which the client is running.

    The vendor-class-data is composed of a series of separate items, each
    of which describes some characteristic of the client's hardware
    configuration.  Examples of vendor-class-data instances might include
    the version of the operating system the client is running or the
    amount of memory installed on the client.

    Each instance of the vendor-class-data is formatted as follows::

      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+
      |       vendor-class-len        |          opaque-data          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-...-+-+-+-+-+-+-+

    The vendor-class-len is two octets long and specifies the length of
    the opaque vendor class data in network byte order.

    :type enterprise_number: int
    :type vendor_classes: list[bytes]
    """

    option_type = OPTION_VENDOR_CLASS

    def __init__(self, enterprise_number: int = 0, vendor_classes: [bytes] = None):
        self.enterprise_number = enterprise_number
        """The enterprise number"""

        self.vendor_classes = vendor_classes or []
        """The list of vendor classes for this enterprise"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.enterprise_number, int) or not (0 <= self.enterprise_number < 2 ** 32):
            raise ValueError("Enterprise number must be an unsigned 32 bit integer")

        if not isinstance(self.vendor_classes, list):
            raise ValueError("Vendor classes must be a list")

        for vendor_class in self.vendor_classes:
            if not isinstance(vendor_class, bytes) or len(vendor_class) >= 2 ** 16:
                raise ValueError("Vendor classes must be a list of bytes")

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

        self.enterprise_number = unpack_from('!I', buffer, offset=offset + my_offset)[0]
        my_offset += 4

        # Parse the vendor classes
        self.vendor_classes = []
        """:type: [bytes]"""

        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            vendor_class_length = unpack_from('!H', buffer, offset=offset + my_offset)[0]
            my_offset += 2

            vendor_class = buffer[offset + my_offset:offset + my_offset + vendor_class_length]
            my_offset += vendor_class_length

            self.vendor_classes.append(vendor_class)

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed vendor classes')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        vendor_classes_bytes = bytearray()
        for vendor_class in self.vendor_classes:
            vendor_classes_bytes.extend(pack('!H', len(vendor_class)))
            vendor_classes_bytes.extend(vendor_class)

        buffer = bytearray()
        buffer.extend(pack('!HHI', self.option_type, len(vendor_classes_bytes) + 4, self.enterprise_number))
        buffer.extend(vendor_classes_bytes)
        return buffer


class VendorSpecificInformationOption(Option):
    """
    :rfc:`3315#section-22.17`

    This option is used by clients and servers to exchange
    vendor-specific information.

    The format of the Vendor-specific Information option is::

       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_VENDOR_OPTS       |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                       enterprise-number                       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                          option-data                          .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_VENDOR_OPTS (17)

    option-len
        4 + length of option-data field

    enterprise-number
        The vendor's registered Enterprise Number as registered with IANA [6].

    option-data
        An opaque object of option-len octets, interpreted by vendor-specific code on the clients and servers

    The definition of the information carried in this option is vendor
    specific.  The vendor is indicated in the enterprise-number field.
    Use of vendor-specific information allows enhanced operation,
    utilizing additional features in a vendor's DHCP implementation.  A
    DHCP client that does not receive requested vendor-specific
    information will still configure the host device's IPv6 stack to be
    functional.

    The encapsulated vendor-specific options field MUST be encoded as a
    sequence of code/length/value fields of identical format to the DHCP
    options field.  The option codes are defined by the vendor identified
    in the enterprise-number field and are not managed by IANA.  Each of
    the encapsulated options is formatted as follows::

       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          opt-code             |             option-len        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                          option-data                          .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    opt-code
        The code for the encapsulated option.

    option-len
        An unsigned integer giving the length of the option-data field in this encapsulated option in octets.

    option-data
        The data area for the encapsulated option.

    Multiple instances of the Vendor-specific Information option may
    appear in a DHCP message.  Each instance of the option is interpreted
    according to the option codes defined by the vendor identified by the
    Enterprise Number in that option.

    :type enterprise_number: int
    :type vendor_options: list[(int, bytes)]
    """

    option_type = OPTION_VENDOR_OPTS

    def __init__(self, enterprise_number: int = 0, vendor_options: [(int, bytes)] = None):
        self.enterprise_number = enterprise_number
        """The enterprise number"""

        self.vendor_options = vendor_options or []
        """The list of vendor options for this enterprise where each option is a tuple containing a code and the data"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.enterprise_number, int) or not (0 <= self.enterprise_number < 2 ** 32):
            raise ValueError("Enterprise number must be an unsigned 32 bit integer")

        if not isinstance(self.vendor_options, list):
            raise ValueError("Vendor options must be a list of integer option-code and bytes option-value) tuples")

        for vendor_option in self.vendor_options:
            if not isinstance(vendor_option, tuple) or len(vendor_option) != 2 or \
                    not isinstance(vendor_option[0], int) or not (0 <= vendor_option[0] < 2 ** 16) or \
                    not isinstance(vendor_option[1], bytes) or len(vendor_option[1]) >= 2 ** 16:
                raise ValueError("Vendor options must be a list of integer option-code and bytes option-value) tuples")

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

        self.enterprise_number = unpack_from('!I', buffer, offset=offset + my_offset)[0]
        my_offset += 4

        # Parse the vendor options
        self.vendor_options = []
        """:type: [(int, bytes)]"""

        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            vendor_option_code, vendor_option_length = unpack_from('!HH', buffer, offset=offset + my_offset)
            my_offset += 4

            vendor_option = buffer[offset + my_offset:offset + my_offset + vendor_option_length]
            my_offset += vendor_option_length

            self.vendor_options.append((vendor_option_code, vendor_option))

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed vendor options')

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        vendor_options_bytes = bytearray()
        for vendor_option_code, vendor_option in self.vendor_options:
            vendor_options_bytes.extend(pack('!HH', vendor_option_code, len(vendor_option)))
            vendor_options_bytes.extend(vendor_option)

        buffer = bytearray()
        buffer.extend(pack('!HHI', self.option_type, len(vendor_options_bytes) + 4, self.enterprise_number))
        buffer.extend(vendor_options_bytes)
        return buffer


class InterfaceIdOption(Option):
    """
    :rfc:`3315#section-22.18`

    The relay agent MAY send the Interface-id option to identify the
    interface on which the client message was received.  If a relay agent
    receives a Relay-reply message with an Interface-id option, the relay
    agent relays the message to the client through the interface
    identified by the option.

    The format of the Interface ID option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_INTERFACE_ID      |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .                         interface-id                          .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_INTERFACE_ID (18).

    option-len
        Length of interface-id field.

    interface-id
        An opaque value of arbitrary length generated by the relay agent to identify one of the relay agent's
        interfaces.

    The server MUST copy the Interface-Id option from the Relay-Forward
    message into the Relay-Reply message the server sends to the relay
    agent in response to the Relay-Forward message.  This option MUST NOT
    appear in any message except a Relay-Forward or Relay-Reply message.

    Servers MAY use the Interface-ID for parameter assignment policies.
    The Interface-ID SHOULD be considered an opaque value, with policies
    based on exact match only; that is, the Interface-ID SHOULD NOT be
    internally parsed by the server.  The Interface-ID value for an
    interface SHOULD be stable and remain unchanged, for example, after
    the relay agent is restarted; if the Interface-ID changes, a server
    will not be able to use it reliably in parameter assignment policies.

    :type interface_id: bytes
    """

    option_type = OPTION_INTERFACE_ID

    def __init__(self, interface_id: bytes = b''):
        self.interface_id = interface_id
        """The interface-ID that the relay received the incoming message on"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.interface_id, bytes) or len(self.interface_id) >= 2 ** 16:
            raise ValueError("Interface-ID must be sequence of bytes")

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

        self.interface_id = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        return pack('!HH', self.option_type, len(self.interface_id)) + self.interface_id


class ReconfigureMessageOption(Option):
    """
    :rfc:`3315#section-22.19`

    A server includes a Reconfigure Message option in a Reconfigure
    message to indicate to the client whether the client responds with a
    Renew message or an Information-request message.  The format of this
    option is::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |      OPTION_RECONF_MSG        |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    msg-type   |
      +-+-+-+-+-+-+-+-+

    option-code
        OPTION_RECONF_MSG (19).

    option-len
        1.

    msg-type
        5 for Renew message, 11 for Information-request message.

    The Reconfigure Message option can only appear in a Reconfigure
    message.

    :type message_type: int
    """

    option_type = OPTION_RECONF_MSG

    def __init__(self, message_type: int = 0):
        self.message_type = message_type
        """The message type that the client should respond with"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if self.message_type not in (5, 11):
            raise ValueError("Message type must be 5 (MSG_RENEW) or 11 (MSG_INFORMATION_REQUEST)")

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

        self.message_type = buffer[offset + my_offset]
        my_offset += 1

        self.validate()

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        self.validate()

        return pack('!HHB', self.option_type, 1, self.message_type)


class ReconfigureAcceptOption(Option):
    """
    :rfc:`3315#section-22.20`

    A client uses the Reconfigure Accept option to announce to the server
    whether the client is willing to accept Reconfigure messages, and a
    server uses this option to tell the client whether or not to accept
    Reconfigure messages.  The default behavior, in the absence of this
    option, means unwillingness to accept Reconfigure messages, or
    instruction not to accept Reconfigure messages, for the client and
    server messages, respectively.  The following figure gives the format
    of the Reconfigure Accept option::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |     OPTION_RECONF_ACCEPT      |               0               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_RECONF_ACCEPT (20).

    option-len
        0.
    """

    option_type = OPTION_RECONF_ACCEPT

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

        if option_len != 0:
            raise ValueError('Reconfigure Accept Options must have length 0')

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HH', self.option_type, 0)


# Specify which class may occur where
Message.add_may_contain(UnknownOption)
Message.add_may_contain(AuthenticationOption, 0, 1)

SolicitMessage.add_may_contain(ClientIdOption, 1, 1)
SolicitMessage.add_may_contain(IANAOption)
SolicitMessage.add_may_contain(IATAOption)
SolicitMessage.add_may_contain(OptionRequestOption, 0, 1)
SolicitMessage.add_may_contain(ElapsedTimeOption, 1, 1)
SolicitMessage.add_may_contain(RapidCommitOption, 0, 1)
SolicitMessage.add_may_contain(UserClassOption)
SolicitMessage.add_may_contain(VendorClassOption)
SolicitMessage.add_may_contain(VendorSpecificInformationOption)
SolicitMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

AdvertiseMessage.add_may_contain(ClientIdOption, 1, 1)
AdvertiseMessage.add_may_contain(ServerIdOption, 1, 1)
AdvertiseMessage.add_may_contain(IANAOption)
AdvertiseMessage.add_may_contain(IATAOption)
AdvertiseMessage.add_may_contain(PreferenceOption, 0, 1)
AdvertiseMessage.add_may_contain(StatusCodeOption, 0, 1)
AdvertiseMessage.add_may_contain(UserClassOption)
AdvertiseMessage.add_may_contain(VendorClassOption)
AdvertiseMessage.add_may_contain(VendorSpecificInformationOption)
AdvertiseMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

RequestMessage.add_may_contain(ClientIdOption, 1, 1)
RequestMessage.add_may_contain(ServerIdOption, 1, 1)
RequestMessage.add_may_contain(IANAOption)
RequestMessage.add_may_contain(IATAOption)
RequestMessage.add_may_contain(OptionRequestOption, 0, 1)
RequestMessage.add_may_contain(ElapsedTimeOption, 1, 1)
RequestMessage.add_may_contain(UserClassOption)
RequestMessage.add_may_contain(VendorClassOption)
RequestMessage.add_may_contain(VendorSpecificInformationOption)
RequestMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

ConfirmMessage.add_may_contain(ClientIdOption, 1, 1)
ConfirmMessage.add_may_contain(IANAOption)
ConfirmMessage.add_may_contain(IATAOption)
ConfirmMessage.add_may_contain(OptionRequestOption, 0, 1)
ConfirmMessage.add_may_contain(ElapsedTimeOption, 1, 1)
ConfirmMessage.add_may_contain(UserClassOption)
ConfirmMessage.add_may_contain(VendorClassOption)
ConfirmMessage.add_may_contain(VendorSpecificInformationOption)

RenewMessage.add_may_contain(ClientIdOption, 1, 1)
RenewMessage.add_may_contain(ServerIdOption, 1, 1)
RenewMessage.add_may_contain(IANAOption)
RenewMessage.add_may_contain(IATAOption)
RenewMessage.add_may_contain(OptionRequestOption, 0, 1)
RenewMessage.add_may_contain(ElapsedTimeOption, 1, 1)
RenewMessage.add_may_contain(UserClassOption)
RenewMessage.add_may_contain(VendorClassOption)
RenewMessage.add_may_contain(VendorSpecificInformationOption)
RenewMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

RebindMessage.add_may_contain(ClientIdOption, 1, 1)
RebindMessage.add_may_contain(IANAOption)
RebindMessage.add_may_contain(IATAOption)
RebindMessage.add_may_contain(OptionRequestOption, 0, 1)
RebindMessage.add_may_contain(ElapsedTimeOption, 1, 1)
RebindMessage.add_may_contain(UserClassOption)
RebindMessage.add_may_contain(VendorClassOption)
RebindMessage.add_may_contain(VendorSpecificInformationOption)
RebindMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

ReleaseMessage.add_may_contain(ClientIdOption, 1, 1)
ReleaseMessage.add_may_contain(ServerIdOption, 1, 1)
ReleaseMessage.add_may_contain(IANAOption)
ReleaseMessage.add_may_contain(IATAOption)
ReleaseMessage.add_may_contain(OptionRequestOption, 0, 1)
ReleaseMessage.add_may_contain(ElapsedTimeOption, 1, 1)
ReleaseMessage.add_may_contain(UserClassOption)
ReleaseMessage.add_may_contain(VendorClassOption)
ReleaseMessage.add_may_contain(VendorSpecificInformationOption)

DeclineMessage.add_may_contain(ClientIdOption, 1, 1)
DeclineMessage.add_may_contain(ServerIdOption, 1, 1)
DeclineMessage.add_may_contain(IANAOption)
DeclineMessage.add_may_contain(IATAOption)
DeclineMessage.add_may_contain(OptionRequestOption, 0, 1)
DeclineMessage.add_may_contain(ElapsedTimeOption, 1, 1)
DeclineMessage.add_may_contain(UserClassOption)
DeclineMessage.add_may_contain(VendorClassOption)
DeclineMessage.add_may_contain(VendorSpecificInformationOption)

ReplyMessage.add_may_contain(ClientIdOption, 0, 1)
ReplyMessage.add_may_contain(ServerIdOption, 1, 1)
ReplyMessage.add_may_contain(IANAOption)
ReplyMessage.add_may_contain(IATAOption)
ReplyMessage.add_may_contain(PreferenceOption, 0, 1)
ReplyMessage.add_may_contain(ServerUnicastOption, 0, 1)
ReplyMessage.add_may_contain(StatusCodeOption, 0, 1)
ReplyMessage.add_may_contain(RapidCommitOption, 0, 1)
ReplyMessage.add_may_contain(UserClassOption)
ReplyMessage.add_may_contain(VendorClassOption)
ReplyMessage.add_may_contain(VendorSpecificInformationOption)
ReplyMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

ReconfigureMessage.add_may_contain(ClientIdOption, 1, 1)
ReconfigureMessage.add_may_contain(ServerIdOption, 1, 1)
ReconfigureMessage.add_may_contain(OptionRequestOption, 0, 1)
ReconfigureMessage.add_may_contain(ReconfigureMessageOption, 1, 1)

InformationRequestMessage.add_may_contain(ClientIdOption, 1, 1)
InformationRequestMessage.add_may_contain(ServerUnicastOption, 0, 1)
InformationRequestMessage.add_may_contain(OptionRequestOption, 0, 1)
InformationRequestMessage.add_may_contain(ElapsedTimeOption, 1, 1)
InformationRequestMessage.add_may_contain(UserClassOption)
InformationRequestMessage.add_may_contain(VendorClassOption)
InformationRequestMessage.add_may_contain(VendorSpecificInformationOption)
InformationRequestMessage.add_may_contain(ReconfigureAcceptOption, 0, 1)

RelayForwardMessage.add_may_contain(RelayMessageOption, 1, 1)
RelayForwardMessage.add_may_contain(InterfaceIdOption, 0, 1)

RelayReplyMessage.add_may_contain(RelayMessageOption, 1, 1)
RelayReplyMessage.add_may_contain(InterfaceIdOption, 0, 1)

IANAOption.add_may_contain(IAAddressOption)
IANAOption.add_may_contain(StatusCodeOption)

IATAOption.add_may_contain(IAAddressOption)
IATAOption.add_may_contain(StatusCodeOption)

IAAddressOption.add_may_contain(StatusCodeOption)

RelayMessageOption.add_may_contain(Message)
