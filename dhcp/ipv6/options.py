from struct import unpack_from, pack

from dhcp.parsing import StructuredElement


# This subclass remains abstract
# noinspection PyAbstractClass
class Option(StructuredElement):
    option_registry = {}  # type: Dict[int, type]

    def __init__(self):
        # The DHCP option type
        self.option_type = 0

    @classmethod
    def register_option_type(cls, option_code: int, subclass: type):
        """
        Register a new option type in the option registry.

        :param option_code: The code for this option
        :param subclass: A subclass of Option that implements the option
        """
        if not issubclass(subclass, cls):
            raise TypeError('Only Options can be registered')

        cls.option_registry[option_code] = subclass

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        """
        Return the appropriate subclass from the registry, or DHCPOption itself if no subclass is registered.

        :param buffer: The buffer to read data from
        :return: The best known class for this option data
        """
        option_type = unpack_from('!H', buffer, offset=offset)[0]
        return cls.option_registry.get(option_type, UnknownOption)


class UnknownOption(Option):
    def __init__(self, option_type: int=0, option_data: bytes=b''):
        super().__init__()
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
