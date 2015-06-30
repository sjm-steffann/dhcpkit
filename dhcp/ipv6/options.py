from struct import unpack_from, pack

from dhcp.parsing import StructuredElement

# This subclass remains abstract
# noinspection PyAbstractClass
class Option(StructuredElement):
    """
    https://tools.ietf.org/html/rfc3315#section-22.1

    The format of DHCP options is:

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |          option-code          |           option-len          |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                          option-data                          |
      |                      (option-len octets)                      |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

      option-code   An unsigned integer identifying the specific option
                    type carried in this option.

      option-len    An unsigned integer giving the length of the
                    option-data field in this option in octets.

      option-data   The data for the option; the format of this data
                    depends on the definition of the option.

    DHCPv6 options are scoped by using encapsulation.  Some options apply
    generally to the client, some are specific to an IA, and some are
    specific to the addresses within an IA.  These latter two cases are
    discussed in sections 22.4 and 22.6.
    """

    # This needs to be overwritten in subclasses
    option_type = 0

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        """
        Return the appropriate subclass from the registry, or UnknownOption if no subclass is registered.

        :param buffer: The buffer to read data from
        :return: The best known class for this option data
        """
        from dhcp.ipv6.option_registry import registry

        option_type = unpack_from('!H', buffer, offset=offset)[0]
        return registry.get(option_type, UnknownOption)

    def parse_option_header(self, buffer: bytes, offset: int=0, length: int=None) -> (int, int):
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
    def __init__(self, option_type: int=0, option_data: bytes=b''):
        self.option_type = option_type
        self.option_data = option_data

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        self.option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.option_data = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> bytes:
        return pack('!HH', self.option_type, len(self.option_data)) + self.option_data
