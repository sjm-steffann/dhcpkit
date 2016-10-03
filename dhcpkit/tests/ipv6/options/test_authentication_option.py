"""
Test the ElapsedTimeOption implementation
"""
import unittest

from dhcpkit.ipv6.options import AuthenticationOption
from dhcpkit.tests.ipv6.options import test_option


class AuthenticationOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('000b000d1234567890abcdef13579ae89f')
        self.option_object = AuthenticationOption(protocol=18, algorithm=52, rdm=86,
                                                  replay_detection=b'\x78\x90\xab\xcd\xef\x13\x57\x9a',
                                                  auth_info=b'\xe8\x9f')
        self.parse_option()

    def test_validate_protocol(self):
        self.check_unsigned_integer_property('protocol', size=8)

    def test_validate_algorithm(self):
        self.check_unsigned_integer_property('algorithm', size=8)

    def test_validate_rdm(self):
        self.check_unsigned_integer_property('rdm', size=8)

    def test_replay_detection(self):
        self.option.replay_detection = b'ABCDEFG'
        with self.assertRaisesRegex(ValueError, 'must contain 8 bytes'):
            self.option.validate()

        self.option.replay_detection = b'ABCDEFGH'
        self.option.validate()

        self.option.replay_detection = b'ABCDEFGHI'
        with self.assertRaisesRegex(ValueError, 'must contain 8 bytes'):
            self.option.validate()

        self.option.replay_detection = 'ABCDEFGH'
        with self.assertRaisesRegex(ValueError, 'must contain 8 bytes'):
            self.option.validate()

    def test_auth_info(self):
        self.option.auth_info = 'ABCDEFGH'
        with self.assertRaisesRegex(ValueError, 'must contain bytes'):
            self.option.validate()

        self.option.auth_info = b'ABCDEFGH'
        self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            AuthenticationOption.parse(bytes.fromhex('000b00000000ffff'))


if __name__ == '__main__':
    unittest.main()
