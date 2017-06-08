"""
Implementation of the Echo Request option as specified in :rfc:`4994`.
"""
from struct import pack, unpack_from
from typing import Iterable, List, Union

from dhcpkit.ipv6.options import Option, UnknownOption
from dhcpkit.protocol_element import ElementDataRepresentation

OPTION_ERO = 43


class EchoRequestOption(Option):
    """
    The relay agent adds options in the Relay Forward message that the
    server uses to guide its decision making with regard to address
    assignment, prefix delegation, and configuration parameters.  The
    relay agent also knows which of these options that it will need to
    efficiently return replies to the client.  It uses the relay agent
    Echo Request option to inform the server of the list of relay agent
    options that the server must echo back.

    The format of the DHCPv6 Relay Agent Echo Request option is shown
    below:

    .. code-block:: none

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |           OPTION_ERO          |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |    requested-option-code-1    |    requested-option-code-2    |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code
        OPTION_ERO (43).

    option-len
        2 * number of requested options.

    requested-option-code-n
        The option code for an option requested by the relay agent.

    :type requested_options: list[int]
    """

    option_type = OPTION_ERO

    def __init__(self, requested_options: Iterable[int] = None):
        self.requested_options = list(requested_options or [])
        """The list of option type numbers that the relay wants to receive back"""

    def display_requested_options(self) -> List[ElementDataRepresentation]:
        """
        Provide a nicer output when displaying the requested options.

        :return: A list of option names
        """
        from dhcpkit.ipv6.option_registry import option_registry

        out = []
        for option_type in self.requested_options:
            class_name = option_registry.get(option_type, UnknownOption).__name__
            out.append(ElementDataRepresentation("{} ({})".format(class_name, option_type)))

        return out

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

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.requested_options) * 2))
        buffer.extend(pack('!{}H'.format(len(self.requested_options)), *self.requested_options))
        return buffer
