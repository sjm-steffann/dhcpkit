import unittest

from dhcpkit.ipv6.duids import EnterpriseDUID
from dhcpkit.ipv6.options import ClientIdOption, Option


class TestClientIdOption(unittest.TestCase):
    def setUp(self):
        self.option_bytes = b'\x00\x01\x00\x15\x00\x02\x00\x00\x9d\x100123456789abcde'
        self.option_object = ClientIdOption(EnterpriseDUID(40208, b'0123456789abcde'))

    def test_parse(self):
        offset, option = Option.parse(self.option_bytes)
        self.assertEqual(offset, len(self.option_bytes))
        self.assertEqual(option, self.option_object)

    def test_validate_duid(self):
        # noinspection PyTypeChecker
        bad = ClientIdOption(b'0123456789abcdef')
        self.assertRaisesRegex(ValueError, 'DUID object', bad.validate)

    def test_save(self):
        output = self.option_object.save()
        self.assertEqual(output, self.option_bytes)


if __name__ == '__main__':
    unittest.main()
