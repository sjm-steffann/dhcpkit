"""
Test the DNS options implementations
"""
import unittest

from dhcpkit.ipv6.extensions.timezone import PosixTimezoneOption, TZDBTimezoneOption
from dhcpkit.tests.ipv6.options import test_option


class PosixTimezoneOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('00290023') + b'EST5EDT4,M3.2.0/02:00,M11.1.0/02:00'
        self.option_object = PosixTimezoneOption(timezone='EST5EDT4,M3.2.0/02:00,M11.1.0/02:00')
        self.parse_option()

    def test_validate_timezone(self):
        self.option.timezone = None
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.timezone = b'EST5EDT4,M3.2.0/02:00,M11.1.0/02:00'
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.timezone = ['EST5EDT4,M3.2.0/02:00,M11.1.0/02:00']
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.timezone = ':/etc/timezone/Europe/London'
        with self.assertRaisesRegex(ValueError, 'colon'):
            self.option.validate()

        self.option.timezone = 'x' * 65536
        with self.assertRaisesRegex(ValueError, '65535 characters or less'):
            self.option.validate()

        self.option.timezone = 'Some random string'
        with self.assertRaisesRegex(ValueError, 'does not conform to POSIX.1'):
            self.option.validate()

        # noinspection SpellCheckingInspection
        valid_timezones = [
            'EST5EDT4,M3.2.0/02:00,M11.1.0/02:00',
            'GRNLNDST3GRNLNDDT,M10.3.0/00:00:00,M2.4.0/00:00:00',
            'CST6CDT,M3.2.0/2:00:00,M11.1.0/2:00:00',
            'CET6CEST5:30,M4.5.0/02:00:00,M10.5.0/03:00:00',
            'HAST10HADT,M4.2.0/03:0:0,M10.2.0/03:0:00',
            'AST9ADT,M3.2.0,M11.1.0',
            'AST9ADT,M3.2.0/03:0:0,M11.1.0/03:0:0',
            'EST5EDT,M3.2.0/02:00:00,M11.1.0/02:00:00',
            'GRNLNDST3GRNLNDDT,M10.3.0/00:00:00,M2.4.0/00:00:00',
            'EST5EDT,M3.2.0/02:00:00,M11.1.0',
            'EST5EDT,M3.2.0,M11.1.0/02:00:00',
            'CST6CDT,M3.2.0/2:00:00,M11.1.0/2:00:00',
            'MST7MDT,M3.2.0/2:00:00,M11.1.0/2:00:00',
            'PST8PDT,M3.2.0/2:00:00,M11.1.0/2:00:00',
            'EST+5EDT,M3.2.0/2,M11.1.0/2',
            'IST-2IDT,M3.4.4/26,M10.5.0',
            'WART4WARST,J1/0,J365/25',
            'WGT3WGST,M3.5.0/-2,M10.5.0/-1',
        ]

        # A bunch of timezone definitions from different manuals to verify against
        for tz in valid_timezones:
            self.option.timezone = tz
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            PosixTimezoneOption.parse(bytes.fromhex('00290024') + b'EST5EDT4,M3.2.0/02:00,M11.1.0/02:00')


class TZDBTimezoneOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('002a0010') + b'Europe/Amsterdam'
        self.option_object = TZDBTimezoneOption(timezone='Europe/Amsterdam')
        self.parse_option()

    def test_validate_timezone(self):
        self.option.timezone = None
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.timezone = b'Europe/Amsterdam'
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.timezone = ['Europe/Amsterdam']
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.option.validate()

        self.option.timezone = 'x' * 65536
        with self.assertRaisesRegex(ValueError, '65535 characters or less'):
            self.option.validate()

        self.option.timezone = 'Europe/Wörgl'
        with self.assertRaisesRegex(ValueError, 'only printable ASCII'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'longer than the available buffer'):
            TZDBTimezoneOption.parse(bytes.fromhex('002a0011') + b'Europe/Amsterdam')


if __name__ == '__main__':
    unittest.main()
