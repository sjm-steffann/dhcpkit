"""
Test the included DUID types
"""
import unittest

from dhcpkit.ipv6.duids import DUID
from tests import fixtures


class UnknownDUIDTestCase(unittest.TestCase):
    def setUp(self):
        self.duid_object = fixtures.unknown_duid
        self.duid_bytes = fixtures.unknown_duid_bytes

    def test_parse(self):
        length = len(self.duid_bytes)
        parsed_length, parsed_object = DUID.parse(self.duid_bytes, length=length)
        self.assertEqual(parsed_length, length)
        self.assertEqual(parsed_object, self.duid_object)

    def test_parse_with_larger_buffer(self):
        offset = 50
        buffer = bytes(50 * [0]) + self.duid_bytes + bytes(50 * [0])
        length = len(self.duid_bytes)
        parsed_length, parsed_object = DUID.parse(buffer, offset=offset, length=length)
        self.assertEqual(parsed_length, length)
        self.assertEqual(parsed_object, self.duid_object)

    def test_save(self):
        saved_bytes = self.duid_object.save()
        self.assertEqual(saved_bytes, self.duid_bytes)


class LinkLayerTimeDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = fixtures.llt_duid
        self.duid_bytes = fixtures.llt_duid_bytes


class EnterpriseDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = fixtures.en_duid
        self.duid_bytes = fixtures.en_duid_bytes


class LinkLayerDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = fixtures.ll_duid
        self.duid_bytes = fixtures.ll_duid_bytes


if __name__ == '__main__':
    unittest.main()
