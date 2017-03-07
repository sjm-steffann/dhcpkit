"""
Test the encoding and parsing of domain names
"""
import unittest

from dhcpkit.utils import encode_domain, encode_domain_list, parse_domain_bytes, parse_domain_list_bytes


class DomainNameTestCase(unittest.TestCase):
    def setUp(self):
        self.good_domain_bytes = b'\x0510-ww\x08steffann\x02nl\x00'
        self.good_relative_domain_bytes = b'\x0510-ww\x08steffann\x02nl'
        self.good_domain_name = '10-ww.steffann.nl.'
        self.good_relative_domain_name = '10-ww.steffann.nl'

        self.oversized_label_bytes = b'\x0410ww\x47steffann-steffann-steffann-steffann-' \
                                     b'steffann-steffann-steffann-steffann\x02nl\x00'
        self.oversized_label_name = '10ww.steffann-steffann-steffann-steffann-steffann-steffann-steffann-steffann.nl'

        self.oversized_domain_bytes = b'\x0410ww' \
                                      b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                      b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                      b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                      b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                      b'\x02nl\x00'
        self.oversized_relative_domain_bytes = b'\x0410ww' \
                                               b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                               b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                               b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann' \
                                               b'\x3esteffann-steffann-steffann-steffann-steffann-steffann-steffann'
        self.oversized_domain_name = '10ww.' \
                                     'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                     'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                     'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                     'steffann-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                     'nl'

        self.idn_domain_bytes = b'\x03www\x07example\x0bxn--j6w193g\x00'
        self.idn_domain_name = 'www.example.香港.'

        self.idn_oversized_label_bytes = b'\x0410ww' \
                                         b'\x43stffnn-steffann-steffann-steffann-steffann-steffann-steffann-o8e12a' \
                                         b'\x02nl\x00'

        self.idn_oversized_label_name = '10ww.' \
                                        'stéffänn-steffann-steffann-steffann-steffann-steffann-steffann.' \
                                        'nl'

        self.buffer_overflow_bytes = b'\x0410ww\x10END'
        self.unending_bytes = b'\x0410ww\x03END'

    def test_parse_good(self):
        offset, domain_name = parse_domain_bytes(self.good_domain_bytes)
        self.assertEqual(offset, len(self.good_domain_bytes))
        self.assertEqual(domain_name, self.good_domain_name)

    def test_parse_relative(self):
        offset, domain_name = parse_domain_bytes(self.good_relative_domain_bytes, allow_relative=True)
        self.assertEqual(offset, len(self.good_relative_domain_bytes))
        self.assertEqual(domain_name, self.good_relative_domain_name)

    def test_encode_good(self):
        domain_bytes = encode_domain(self.good_domain_name)
        self.assertEqual(domain_bytes, self.good_domain_bytes)

    def test_encode_relative(self):
        domain_bytes = encode_domain(self.good_relative_domain_name, allow_relative=True)
        self.assertEqual(domain_bytes, self.good_relative_domain_bytes)

        domain_bytes = encode_domain(self.good_domain_name + '.', allow_relative=True)
        self.assertEqual(domain_bytes, self.good_domain_bytes)

    def test_parse_idn(self):
        offset, domain_name = parse_domain_bytes(self.idn_domain_bytes)
        self.assertEqual(offset, len(self.idn_domain_bytes))
        self.assertEqual(domain_name, self.idn_domain_name)

    def test_encode_idn(self):
        domain_bytes = encode_domain(self.idn_domain_name)
        self.assertEqual(domain_bytes, self.idn_domain_bytes)

    def test_parse_oversized_domain(self):
        self.assertRaisesRegex(ValueError, 'must be 255 characters or less', parse_domain_bytes,
                               self.oversized_domain_bytes)

    def test_parse_oversized_relative_domain(self):
        self.assertRaisesRegex(ValueError, 'must be 255 characters or less', parse_domain_bytes,
                               self.oversized_relative_domain_bytes, allow_relative=True)

    def test_encode_oversized_domain(self):
        self.assertRaisesRegex(ValueError, 'must be 255 characters or less', encode_domain, self.oversized_domain_name)

    def test_parse_idn_oversized_label(self):
        self.assertRaisesRegex(ValueError, 'labels must be 1 to 63 characters', parse_domain_bytes,
                               self.idn_oversized_label_bytes)

    def test_encode_idn_oversized_label(self):
        self.assertRaisesRegex(ValueError, 'labels must be 1 to 63 characters', encode_domain,
                               self.idn_oversized_label_name)

    def test_parse_oversized_label(self):
        self.assertRaisesRegex(ValueError, 'labels must be 1 to 63 characters', parse_domain_bytes,
                               self.oversized_label_bytes)

    def test_encode_oversized_label(self):
        self.assertRaisesRegex(ValueError, 'labels must be 1 to 63 characters', encode_domain,
                               self.oversized_label_name)

    def test_parse_buffer_overflow(self):
        self.assertRaisesRegex(ValueError, 'exceeds available buffer', parse_domain_bytes, self.buffer_overflow_bytes)

    def test_parse_unending(self):
        self.assertRaisesRegex(ValueError, 'must end with a 0-length label', parse_domain_bytes, self.unending_bytes)


class DomainNameListTestCase(unittest.TestCase):
    def setUp(self):
        self.good_domains_bytes = b'\x06google\x03com\x00\x0410ww\x08steffann\x02nl\x00'
        self.good_domains_list = ['google.com.', '10ww.steffann.nl.']

    def test_parse_good(self):
        offset, domain_names = parse_domain_list_bytes(self.good_domains_bytes)
        self.assertEqual(offset, len(self.good_domains_bytes))
        self.assertListEqual(domain_names, self.good_domains_list)

    def test_encode_good(self):
        domain_bytes = encode_domain_list(self.good_domains_list)
        self.assertEqual(domain_bytes, self.good_domains_bytes)


if __name__ == '__main__':
    unittest.main()
