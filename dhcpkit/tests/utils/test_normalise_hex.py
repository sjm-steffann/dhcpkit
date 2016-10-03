"""
Test the camelcase conversion functions
"""
import unittest

from dhcpkit.utils import normalise_hex


class NormaliseHexTestCase(unittest.TestCase):
    def test_hex(self):
        self.assertEqual(normalise_hex(''), '')
        self.assertEqual(normalise_hex('1a2b3c'), '1a2b3c')
        self.assertEqual(normalise_hex('1a:2b:3c'), '1a2b3c')
        self.assertEqual(normalise_hex('1a:2b3c'), '1a2b3c')
        self.assertEqual(normalise_hex('1a2b:3c'), '1a2b3c')

    def test_hex_with_colons(self):
        self.assertEqual(normalise_hex('', include_colons=True), '')
        self.assertEqual(normalise_hex('1a2b3c', include_colons=True), '1a:2b:3c')
        self.assertEqual(normalise_hex('1a:2b:3c', include_colons=True), '1a:2b:3c')
        self.assertEqual(normalise_hex('1a:2b3c', include_colons=True), '1a:2b:3c')
        self.assertEqual(normalise_hex('1a2b:3c', include_colons=True), '1a:2b:3c')

    def test_bad_hex(self):
        with self.assertRaisesRegex(ValueError, 'not valid hex'):
            normalise_hex('1a2:b3c')

        with self.assertRaisesRegex(ValueError, 'not valid hex'):
            normalise_hex('Something')


if __name__ == '__main__':
    unittest.main()
