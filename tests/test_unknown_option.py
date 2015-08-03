import unittest

from dhcpkit.ipv6.options import UnknownOption, Option


class TestUnknownOption(unittest.TestCase):
    def setUp(self):
        self.option_bytes = b'\x00\xff\x00\x100123456789abcdef'
        self.overflow_bytes = b'\x00\xff\x00\x100123456789abcde'
        self.option_object = UnknownOption(255, b'0123456789abcdef')

    def test_parse(self):
        offset, option = Option.parse(self.option_bytes)
        self.assertEqual(offset, 20)
        self.assertEqual(option, self.option_object)

    def test_validate_type(self):
        bad = UnknownOption(65536, b'0123456789abcdef')
        self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer', bad.validate)

    def test_validate_data(self):
        # noinspection PyTypeChecker
        bad = UnknownOption(65535, '0123456789abcdef')
        self.assertRaisesRegex(ValueError, 'bytes', bad.validate)

        bad = UnknownOption(65535, b'0123456789abcdef' * 10000)
        self.assertRaisesRegex(ValueError, 'bytes', bad.validate)

    def test_overflow(self):
        self.assertRaisesRegex(ValueError, 'longer than .* buffer', UnknownOption.parse, self.overflow_bytes)

    def test_save(self):
        output = self.option_object.save()
        self.assertEqual(output, self.option_bytes)


if __name__ == '__main__':
    unittest.main()
