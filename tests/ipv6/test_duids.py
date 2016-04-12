"""
Test the included DUID types
"""
import unittest

from dhcpkit.ipv6.duids import DUID, LinkLayerTimeDUID, LinkLayerDUID, EnterpriseDUID, UnknownDUID


class UnknownDUIDTestCase(unittest.TestCase):
    def setUp(self):
        self.duid_object = UnknownDUID(duid_type=65535, duid_data=b'SomeRandomDUIDData')
        self.duid_bytes = bytes.fromhex('ffff536f6d6552616e646f6d4455494444617461')

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
        self.duid_object = LinkLayerTimeDUID(hardware_type=1, time=15, link_layer_address=bytes.fromhex('3431c43cb2f1'))
        self.duid_bytes = bytes.fromhex('000100010000000f3431c43cb2f1')

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
        good_duid_object = LinkLayerTimeDUID(0, 0, 120 * b'x')
        good_duid_object.validate()

        bad_duid_object = LinkLayerTimeDUID(0, 0, 121 * b'x')
        with self.assertRaisesRegex(ValueError, 'cannot be longer than 120 bytes'):
            bad_duid_object.validate()


class EnterpriseDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = EnterpriseDUID(enterprise_number=40208, identifier=b'DHCPKitUnitTestIdentifier')
        self.duid_bytes = bytes.fromhex('000200009d10444843504b6974556e6974546573744964656e746966696572')

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
        good_duid_object = EnterpriseDUID(0, 122 * b'x')
        good_duid_object.validate()

        bad_duid_object = EnterpriseDUID(0, 123 * b'x')
        with self.assertRaisesRegex(ValueError, 'cannot be longer than 122 bytes'):
            bad_duid_object.validate()


class LinkLayerDUIDTestCase(UnknownDUIDTestCase):
    def setUp(self):
        self.duid_object = LinkLayerDUID(hardware_type=1, link_layer_address=bytes.fromhex('3431c43cb2f1'))
        self.duid_bytes = bytes.fromhex('000300013431c43cb2f1')

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
        good_duid_object = LinkLayerDUID(0, 124 * b'x')
        good_duid_object.validate()

        bad_duid_object = LinkLayerDUID(0, 125 * b'x')
        with self.assertRaisesRegex(ValueError, 'cannot be longer than 124 bytes'):
            bad_duid_object.validate()


if __name__ == '__main__':
    unittest.main()
