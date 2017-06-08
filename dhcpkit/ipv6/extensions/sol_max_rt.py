"""
Implementation of SOL-MAX-RT and INF-MAX-RT options as specified in :rfc:`7083`.
"""

from struct import pack, unpack_from
from typing import Union

from dhcpkit.ipv6.messages import AdvertiseMessage, ReplyMessage
from dhcpkit.ipv6.options import Option

OPTION_SOL_MAX_RT = 82
OPTION_INF_MAX_RT = 83


class SolMaxRTOption(Option):
    """
    :rfc:`7083#section-4`

    A DHCPv6 server sends the SOL_MAX_RT option to a client to override
    the default value of SOL_MAX_RT.  The value of SOL_MAX_RT in the
    option replaces the default value defined in Section 3.  One use for
    the SOL_MAX_RT option is to set a longer value for SOL_MAX_RT, which
    reduces the Solicit traffic from a client that has not received a
    response to its Solicit messages.

    The format of the SOL_MAX_RT option is:

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          option-code          |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                       SOL_MAX_RT value                        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_SOL_MAX_RT (82).

    option-len
        4.

    SOL_MAX_RT value
        Overriding value for SOL_MAX_RT in seconds; MUST be in range: 60 <= "value" <= 86400 (1 day).

    :type sol_max_rt: int
    """

    option_type = OPTION_SOL_MAX_RT

    def __init__(self, sol_max_rt: int = 0):
        self.sol_max_rt = sol_max_rt
        """The new value of SOL_MAX_RT for the client"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.sol_max_rt, int) or not (0 <= self.sol_max_rt < 2 ** 32):
            raise ValueError("SOL_MAX_RT must be an unsigned 32 bit integer")

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

        if option_len != 4:
            raise ValueError('SOL_MAX_RT Options must have length 4')

        self.sol_max_rt = unpack_from('!I', buffer, offset=offset + my_offset)[0]
        my_offset += 4

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HHI', self.option_type, 4, self.sol_max_rt)


class InfMaxRTOption(Option):
    """
    :rfc:`7083#section-5`

    A DHCPv6 server sends the INF_MAX_RT option to a client to override
    the default value of INF_MAX_RT.  The value of INF_MAX_RT in the
    option replaces the default value defined in Section 3.  One use for
    the INF_MAX_RT option is to set a longer value for INF_MAX_RT, which
    reduces the Information-request traffic from a client that has not
    received a response to its Information-request messages.

    The format of the INF_MAX_RT option is:

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          option-code          |         option-len            |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                       INF_MAX_RT value                        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_INF_MAX_RT (83).

    option-len
        4.

    INF_MAX_RT value
        Overriding value for INF_MAX_RT in seconds; MUST be in range: 60 <= "value" <= 86400 (1 day).

    :type inf_max_rt: int
    """

    option_type = OPTION_INF_MAX_RT

    def __init__(self, inf_max_rt: int = 0):
        self.inf_max_rt = inf_max_rt
        """The new value for INF_MAX_RT for the client"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.inf_max_rt, int) or not (0 <= self.inf_max_rt < 2 ** 32):
            raise ValueError("INF_MAX_RT must be an unsigned 32 bit integer")

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

        if option_len != 4:
            raise ValueError('INF_MAX_RT Options must have length 4')

        self.inf_max_rt = unpack_from('!I', buffer, offset=offset + my_offset)[0]
        my_offset += 4

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HHI', self.option_type, 4, self.inf_max_rt)


# Register where these options may occur
AdvertiseMessage.add_may_contain(SolMaxRTOption, 0, 1)
ReplyMessage.add_may_contain(SolMaxRTOption, 0, 1)

AdvertiseMessage.add_may_contain(InfMaxRTOption, 0, 1)
ReplyMessage.add_may_contain(InfMaxRTOption, 0, 1)
