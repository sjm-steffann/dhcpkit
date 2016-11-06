"""
Tests for datatypes for use in configuration files
"""
import unittest

from dhcpkit.common.server.config_datatypes import domain_name


class DomainNameTestCase(unittest.TestCase):
    def test_valid(self):
        valid_domain_names = [
            ('steffann.nl', 'steffann.nl'),
            ('Steffann.Nl', 'steffann.nl'),
            ('STEFFANN.NL', 'steffann.nl'),
            ('10ww.steffann.nl', '10ww.steffann.nl'),
            ('local', 'local'),
            ('LOCAL', 'local'),
        ]

        for test, output in valid_domain_names:
            with self.subTest(test=test):
                self.assertEqual(domain_name(test), output)

    def test_name_too_long(self):
        oversized_domain_name = '10ww.' \
                                'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                'nl'
        with self.assertRaisesRegex(ValueError, 'must be 255 characters'):
            domain_name(oversized_domain_name)

    def test_label_too_long(self):
        oversized_label_name = '10ww.steffann-steffann-steffann-steffann-steffann-steffann-steffann-steffann.nl'
        with self.assertRaisesRegex(ValueError, 'must be 1 to 63 characters'):
            domain_name(oversized_label_name)


if __name__ == '__main__':
    unittest.main()
