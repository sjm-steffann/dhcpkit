"""
Implementation of the DHCPv6-PD-Exclude option as specified in :rfc:`4833`.
"""

from struct import pack
from typing import Union

from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption
from dhcpkit.ipv6.options import Option

OPTION_PD_EXCLUDE = 67


class PDExcludeOption(Option):
    """
    :rfc:`6603#section-4.2`

    .. code-block:: none

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |       OPTION_PD_EXCLUDE       |         option-len            |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |  prefix-len   | IPv6 subnet ID (1 to 16 octets)               ~
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

                           Prefix Exclude Option

    option-code:
        OPTION_PD_EXCLUDE (67).

    option-len:
        1 + length of IPv6 subnet ID in octets.  A valid option-len is between 2 and 17.

    prefix-len:
        The length of the excluded prefix in bits.  The prefix-len MUST be between
        'OPTION_IAPREFIX prefix-length'+1 and 128.

    IPv6 subnet ID:
        A variable-length IPv6 subnet ID up to 128 bits.

    The IPv6 subnet ID contains prefix-len minus 'OPTION_IAPREFIX prefix-
    length' bits extracted from the excluded prefix starting from the bit
    position 'OPTION_IAPREFIX prefix-length'.  The extracted subnet ID
    MUST be left-shifted to start from a full octet boundary, i.e., left-
    shift of 'OPTION_IAPREFIX prefix-length' mod 8 bits.  The subnet ID
    MUST be zero-padded to the next full octet boundary.
    """

    option_type = OPTION_PD_EXCLUDE

    def __init__(self, prefix_length: int = 64, subnet_id: bytes = None):
        self.prefix_length = prefix_length
        self.subnet_id = subnet_id

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.prefix_length, int) or not (1 <= self.prefix_length <= 128):
            raise ValueError("Prefix length must be an integer between 1 and 128")

        if not isinstance(self.subnet_id, bytes) or not (1 <= len(self.subnet_id) <= 16):
            raise ValueError("Subnet-ID must be sequence of 1 to 16 bytes")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=2, max_length=17)

        # Prefix length
        self.prefix_length = buffer[offset + my_offset]
        my_offset += 1

        # Subnet-ID
        subnet_id_length = option_len - 1
        self.subnet_id = buffer[offset + my_offset:offset + my_offset + subnet_id_length]
        my_offset += subnet_id_length

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HHB', self.option_type, 1 + len(self.subnet_id), self.prefix_length))
        buffer.extend(self.subnet_id)

        return buffer


# Register where these options may occur
IAPDOption.add_may_contain(PDExcludeOption, 0, 1)
