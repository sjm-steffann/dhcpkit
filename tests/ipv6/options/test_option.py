"""
Test the basic option implementation
"""
import unittest

from dhcpkit.ipv6.options import UnknownOption, Option


class OptionTestCase(unittest.TestCase):
    def setUp(self):
        # The following attributes must be overruled by child classes
        # The basics are tested with a simple UnknownOption
        self.option_bytes = bytes.fromhex('ffff0010') + b'0123456789abcdef'
        self.option_object = UnknownOption(65535, b'0123456789abcdef')
        self.parse_option()

    def parse_option(self):
        self.length, self.option = Option.parse(self.option_bytes)
        self.assertIsInstance(self.option, Option)
        self.option_class = type(self.option)

    def test_length(self):
        self.assertEqual(self.length, len(self.option_bytes))

    def test_parse(self):
        self.assertEqual(self.option, self.option_object)

    def test_save_parsed(self):
        self.assertEqual(self.option_bytes, self.option.save())

    def test_save_fixture(self):
        self.assertEqual(self.option_bytes, self.option_object.save())

    def test_validate(self):
        # This should be ok
        self.option.validate()

    def test_overflow(self):
        with self.assertRaisesRegex(ValueError, 'longer than .* buffer'):
            self.option_class.parse(self.option_bytes, length=len(self.option_bytes) - 1)

    def test_load_from_wrong_buffer(self):
        if issubclass(self.option_class, UnknownOption):
            # UnknownOption accepts any parseable buffer, no point in testing that one
            return

        option = self.option_class()
        with self.assertRaisesRegex(ValueError, 'buffer does not contain'):
            option.load_from(bytes.fromhex('fffe0000'))


if __name__ == '__main__':
    unittest.main()
