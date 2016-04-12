"""
Classes and constants for the DUIDs defined in :rfc:`3315`
"""
from struct import unpack_from, pack

from dhcpkit.protocol_element import ProtocolElement

# DUID type codes

DUID_LLT = 1
DUID_EN = 2
DUID_LL = 3


# This subclass remains abstract
# noinspection PyAbstractClass
class DUID(ProtocolElement):
    """
    :rfc:`3315#section-9.1`

    A DUID consists of a two-octet type code represented in network byte
    order, followed by a variable number of octets that make up the
    actual identifier.  A DUID can be no more than 128 octets long (not
    including the type code).
    """

    # This needs to be overwritten in subclasses
    duid_type = 0

    def __hash__(self) -> int:
        """
        Make DUIDs hashable.

        :return: The hash value
        """
        return hash(self.save())

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int = 0) -> type:
        """
        Return the appropriate subclass from the registry, or UnknownDUID if no subclass is registered.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :return: The best known class for this duid data
        """
        from dhcpkit.ipv6.duid_registry import duid_registry
        duid_type = unpack_from('!H', buffer, offset=offset)[0]
        return duid_registry.get(duid_type, UnknownDUID)

    def parse_duid_header(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Parse the DUID type and perform some basic validation.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        if not length:
            raise ValueError('DUIDs length must be explicitly provided when parsing')

        duid_type = unpack_from('!H', buffer, offset=offset)[0]
        my_offset = 2

        if duid_type != self.duid_type:
            raise ValueError('The provided buffer does not contain {} data'.format(self.__class__.__name__))

        return my_offset


class UnknownDUID(DUID):
    """
    Container for raw DUID content for cases where we don't know how to decode the DUID.
    """

    def __init__(self, duid_type: int = 0, duid_data: bytes = b''):
        self.duid_type = duid_type
        self.duid_data = duid_data

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        self.duid_type = unpack_from('!H', buffer, offset=offset)[0]
        my_offset = self.parse_duid_header(buffer, offset, length)

        duid_len = length - my_offset
        self.duid_data = buffer[offset + my_offset:offset + my_offset + duid_len]
        my_offset += duid_len

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!H', self.duid_type) + self.duid_data


class LinkLayerTimeDUID(DUID):
    """
    :rfc:`3315#section-9.2`

    This type of DUID consists of a two octet type field containing the
    value 1, a two octet hardware type code, four octets containing a
    time value, followed by link-layer address of any one network
    interface that is connected to the DHCP device at the time that the
    DUID is generated.  The time value is the time that the DUID is
    generated represented in seconds since midnight (UTC), January 1,
    2000, modulo 2^32.  The hardware type MUST be a valid hardware type
    assigned by the IANA as described in :rfc:`826` [14].  Both the time and
    the hardware type are stored in network byte order.  The link-layer
    address is stored in canonical form, as described in :rfc:`2464` [2].

    The following diagram illustrates the format of a DUID-LLT::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |               1               |    hardware type (16 bits)    |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                        time (32 bits)                         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .             link-layer address (variable length)              .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    The choice of network interface can be completely arbitrary, as long
    as that interface provides a globally unique link-layer address for
    the link type, and the same DUID-LLT SHOULD be used in configuring
    all network interfaces connected to the device, regardless of which
    interface's link-layer address was used to generate the DUID-LLT.

    Clients and servers using this type of DUID MUST store the DUID-LLT
    in stable storage, and MUST continue to use this DUID-LLT even if the
    network interface used to generate the DUID-LLT is removed.  Clients
    and servers that do not have any stable storage MUST NOT use this
    type of DUID.

    Clients and servers that use this DUID SHOULD attempt to configure
    the time prior to generating the DUID, if that is possible, and MUST
    use some sort of time source (for example, a real-time clock) in
    generating the DUID, even if that time source could not be configured
    prior to generating the DUID.  The use of a time source makes it
    unlikely that two identical DUID-LLTs will be generated if the
    network interface is removed from the client and another client then
    uses the same network interface to generate a DUID-LLT.  A collision
    between two DUID-LLTs is very unlikely even if the clocks have not
    been configured prior to generating the DUID.

    This method of DUID generation is recommended for all general purpose
    computing devices such as desktop computers and laptop computers, and
    also for devices such as printers, routers, and so on, that contain
    some form of writable non-volatile storage.

    Despite our best efforts, it is possible that this algorithm for
    generating a DUID could result in a client identifier collision.  A
    DHCP client that generates a DUID-LLT using this mechanism MUST
    provide an administrative interface that replaces the existing DUID
    with a newly-generated DUID-LLT.
    """

    duid_type = DUID_LLT

    def __init__(self, hardware_type: int = 0, time: int = 0, link_layer_address: bytes = b''):
        self.hardware_type = hardware_type
        self.time = time
        self.link_layer_address = link_layer_address

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.hardware_type, int) or not (0 <= self.hardware_type < 2 ** 16):
            raise ValueError("Hardware type must be an unsigned 16 bit integer")

        if not isinstance(self.time, int) or not (0 <= self.time < 2 ** 32):
            raise ValueError("Time must be an unsigned 32 bit integer")

        if not isinstance(self.link_layer_address, bytes):
            raise ValueError("Link-layer address must be a sequence of bytes")

        if len(self.link_layer_address) > 120:
            raise ValueError("DUID-LLT link-layer address cannot be longer than 120 bytes")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset = self.parse_duid_header(buffer, offset, length)

        self.hardware_type, self.time = unpack_from('!HI', buffer, offset=offset + my_offset)
        my_offset += 6

        ll_len = length - my_offset
        self.link_layer_address = buffer[offset + my_offset:offset + my_offset + ll_len]
        my_offset += ll_len

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HHI', self.duid_type, self.hardware_type, self.time) + self.link_layer_address


class EnterpriseDUID(DUID):
    """
    :rfc:`3315#section-9.3`

    This form of DUID is assigned by the vendor to the device.  It
    consists of the vendor's registered Private Enterprise Number as
    maintained by IANA [6] followed by a unique identifier assigned by
    the vendor.  The following diagram summarizes the structure of a
    DUID-EN::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |               2               |       enterprise-number       |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |   enterprise-number (contd)   |                               |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               |
      .                           identifier                          .
      .                       (variable length)                       .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    The source of the identifier is left up to the vendor defining it,
    but each identifier part of each DUID-EN MUST be unique to the device
    that is using it, and MUST be assigned to the device at the time it
    is manufactured and stored in some form of non-volatile storage.  The
    generated DUID SHOULD be recorded in non-erasable storage.  The
    enterprise-number is the vendor's registered Private Enterprise
    Number as maintained by IANA [6].  The enterprise-number is stored as
    an unsigned 32 bit number.

    An example DUID of this type might look like this::

      +---+---+---+---+---+---+---+---+
      | 0 | 2 | 0 | 0 | 0 |  9| 12|192|
      +---+---+---+---+---+---+---+---+
      |132|221| 3 | 0 | 9 | 18|
      +---+---+---+---+---+---+

    This example includes the two-octet type of 2, the Enterprise Number
    (9), followed by eight octets of identifier data
    (0x0CC084D303000912).
    """

    duid_type = DUID_EN

    def __init__(self, enterprise_number: int = 0, identifier: bytes = b''):
        self.enterprise_number = enterprise_number
        self.identifier = identifier

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.enterprise_number, int) or not (0 <= self.enterprise_number < 2 ** 32):
            raise ValueError("Enterprise number must be an unsigned 32 bit integer")

        if not isinstance(self.identifier, bytes):
            raise ValueError("Identifier must be a sequence of bytes")

        if len(self.identifier) > 122:
            raise ValueError("DUID-EN identifier cannot be longer than 122 bytes")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset = self.parse_duid_header(buffer, offset, length)

        self.enterprise_number = unpack_from('!I', buffer, offset=offset + my_offset)[0]
        my_offset += 4

        identifier_len = length - my_offset
        self.identifier = buffer[offset + my_offset:offset + my_offset + identifier_len]
        my_offset += identifier_len

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HI', self.duid_type, self.enterprise_number) + self.identifier


class LinkLayerDUID(DUID):
    """
    :rfc:`3315#section-9.4`

    This type of DUID consists of two octets containing the DUID type 3,
    a two octet network hardware type code, followed by the link-layer
    address of any one network interface that is permanently connected to
    the client or server device.  For example, a host that has a network
    interface implemented in a chip that is unlikely to be removed and

    used elsewhere could use a DUID-LL.  The hardware type MUST be a
    valid hardware type assigned by the IANA, as described in :rfc:`826`
    [14].  The hardware type is stored in network byte order.  The
    link-layer address is stored in canonical form, as described in
    :rfc:`2464` [2].  The following diagram illustrates the format of a
    DUID-LL::

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |               3               |    hardware type (16 bits)    |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      .                                                               .
      .             link-layer address (variable length)              .
      .                                                               .
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    The choice of network interface can be completely arbitrary, as long
    as that interface provides a unique link-layer address and is
    permanently attached to the device on which the DUID-LL is being
    generated.  The same DUID-LL SHOULD be used in configuring all
    network interfaces connected to the device, regardless of which
    interface's link-layer address was used to generate the DUID.

    DUID-LL is recommended for devices that have a permanently-connected
    network interface with a link-layer address, and do not have
    nonvolatile, writable stable storage.  DUID-LL MUST NOT be used by
    DHCP clients or servers that cannot tell whether or not a network
    interface is permanently attached to the device on which the DHCP
    client is running.
    """

    duid_type = DUID_LL

    def __init__(self, hardware_type: int = 0, link_layer_address: bytes = b''):
        self.hardware_type = hardware_type
        self.link_layer_address = link_layer_address

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.hardware_type, int) or not (0 <= self.hardware_type < 2 ** 16):
            raise ValueError("Hardware type must be an unsigned 16 bit integer")

        if not isinstance(self.link_layer_address, bytes):
            raise ValueError("Link-layer address must be a sequence of bytes")

        if len(self.link_layer_address) > 124:
            raise ValueError("DUID-LL link-layer address cannot be longer than 124 bytes")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset = self.parse_duid_header(buffer, offset, length)

        self.hardware_type = unpack_from('!H', buffer, offset=offset + my_offset)[0]
        my_offset += 2

        ll_len = length - my_offset
        self.link_layer_address = buffer[offset + my_offset:offset + my_offset + ll_len]
        my_offset += ll_len

        return my_offset

    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HH', self.duid_type, self.hardware_type) + self.link_layer_address
