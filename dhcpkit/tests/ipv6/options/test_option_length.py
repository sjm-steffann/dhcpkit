"""
Test the implementation of option length checking
"""
import unittest
from struct import pack
from typing import Union

from dhcpkit.ipv6.option_registry import option_registry
from dhcpkit.ipv6.options import Option
from dhcpkit.tests.ipv6.options import test_option


# A dummy option that may not be in a RelayMessageOption
class LengthTestingOption(Option):
    """
    Fake DHCPv6 option for testing length checks
    """
    option_type = 65535

    def __init__(self, data: bytes = b''):
        self.data = data

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=1, max_length=2)

        self.data = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return pack('!HH', self.option_type, len(self.data)) + self.data


class RelayMessageOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        option_registry[65535] = LengthTestingOption

        self.option_bytes = bytes.fromhex('ffff000161')
        self.option_object = LengthTestingOption(data=b'a')
        self.parse_option()

    def tearDown(self):
        del option_registry[65535]

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            LengthTestingOption.parse(bytes.fromhex('ffff0000'))

        with self.assertRaisesRegex(ValueError, 'longer than the maximum length'):
            LengthTestingOption.parse(bytes.fromhex('ffff0003'))


if __name__ == '__main__':
    unittest.main()
