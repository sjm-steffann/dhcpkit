"""
Test the included DUID types
"""
import unittest

from dhcpkit.ipv6.duids import DUID, LinkLayerTimeDUID, LinkLayerDUID, EnterpriseDUID
from tests.ipv6 import fixtures


class UnknownDUIDTestCase(unittest.TestCase):
    def setUp(self):
        self.duid_object = fixtures.unknown_duid
        self.duid_bytes = fixtures.unknown_duid_bytes

    def test_hash(self):
        duid_hash = hash(self.duid_object)
        self.assertIsInstance(duid_hash, int)

    def test_parse(self):
        with self.assertRaisesRegex(ValueError, 'length'):
            DUID.parse(self.duid_bytes)

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

    def test_wrong_parser(self):
        with self.assertRaisesRegex(ValueError, 'does not contain LinkLayerDUID'):
            duid = LinkLayerDUID()
            duid.load_from(self.duid_bytes, length=len(self.duid_bytes))

    def test_validate_hardware_type(self):
        good_duid_object = LinkLayerTimeDUID(0, 0, b'demo')
        good_duid_object.validate()

        bad_duid_object = LinkLayerTimeDUID(-1, 0, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            bad_duid_object.validate()

        bad_duid_object = LinkLayerTimeDUID(2 ** 16, 0, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            bad_duid_object.validate()

    def test_validate_time(self):
        good_duid_object = LinkLayerTimeDUID(0, 0, b'demo')
        good_duid_object.validate()

        bad_duid_object = LinkLayerTimeDUID(0, -1, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 32 bit integer'):
            bad_duid_object.validate()

        bad_duid_object = LinkLayerTimeDUID(0, 2 ** 32, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 32 bit integer'):
            bad_duid_object.validate()

    def test_validate_link_layer(self):
        # noinspection PyTypeChecker
        bad_duid_object = LinkLayerTimeDUID(0, 0, 'demo')
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            bad_duid_object.validate()

    def test_validate_length(self):
        good_duid_object = LinkLayerTimeDUID(0, 0, 122 * b'x')
        good_duid_object.validate()

        bad_duid_object = LinkLayerTimeDUID(0, 0, 123 * b'x')
        with self.assertRaisesRegex(ValueError, 'cannot be longer than 122 bytes'):
            bad_duid_object.validate()


class EnterpriseDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = fixtures.en_duid
        self.duid_bytes = fixtures.en_duid_bytes

    def test_wrong_parser(self):
        with self.assertRaisesRegex(ValueError, 'does not contain LinkLayerTimeDUID'):
            duid = LinkLayerTimeDUID()
            duid.load_from(self.duid_bytes, length=len(self.duid_bytes))

    def test_validate_enterprise_number(self):
        good_duid_object = EnterpriseDUID(0, b'demo')
        good_duid_object.validate()

        bad_duid_object = EnterpriseDUID(-1, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 32 bit integer'):
            bad_duid_object.validate()

        bad_duid_object = EnterpriseDUID(2 ** 32, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 32 bit integer'):
            bad_duid_object.validate()

    def test_validate_identifier(self):
        # noinspection PyTypeChecker
        bad_duid_object = EnterpriseDUID(0, 'demo')
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            bad_duid_object.validate()

    def test_validate_length(self):
        good_duid_object = EnterpriseDUID(0, 124 * b'x')
        good_duid_object.validate()

        bad_duid_object = EnterpriseDUID(0, 125 * b'x')
        with self.assertRaisesRegex(ValueError, 'cannot be longer than 124 bytes'):
            bad_duid_object.validate()


class LinkLayerDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = fixtures.ll_duid
        self.duid_bytes = fixtures.ll_duid_bytes

    def test_wrong_parser(self):
        with self.assertRaisesRegex(ValueError, 'does not contain EnterpriseDUID'):
            duid = EnterpriseDUID()
            duid.load_from(self.duid_bytes, length=len(self.duid_bytes))

    def test_validate_hardware_type(self):
        good_duid_object = LinkLayerDUID(0, b'demo')
        good_duid_object.validate()

        bad_duid_object = LinkLayerDUID(-1, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            bad_duid_object.validate()

        bad_duid_object = LinkLayerDUID(2 ** 16, b'demo')
        with self.assertRaisesRegex(ValueError, 'unsigned 16 bit integer'):
            bad_duid_object.validate()

    def test_validate_link_layer(self):
        # noinspection PyTypeChecker
        bad_duid_object = LinkLayerDUID(0, 'demo')
        with self.assertRaisesRegex(ValueError, 'sequence of bytes'):
            bad_duid_object.validate()

    def test_validate_length(self):
        good_duid_object = LinkLayerDUID(0, 126 * b'x')
        good_duid_object.validate()

        bad_duid_object = LinkLayerDUID(0, 127 * b'x')
        with self.assertRaisesRegex(ValueError, 'cannot be longer than 126 bytes'):
            bad_duid_object.validate()


if __name__ == '__main__':
    unittest.main()
