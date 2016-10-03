"""
Test the ReconfigureMessageOption implementation
"""
import unittest

from dhcpkit.ipv6.messages import MSG_RENEW
from dhcpkit.ipv6.options import ReconfigureMessageOption
from dhcpkit.tests.ipv6.options import test_option


class ReconfigureMessageOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0013000105')
        self.option_object = ReconfigureMessageOption(message_type=MSG_RENEW)
        self.parse_option()

    def test_message_type(self):
        self.option.message_type = 0
        with self.assertRaisesRegex(ValueError, 'type must be'):
            self.option.validate()

        self.option.message_type = 4
        with self.assertRaisesRegex(ValueError, 'type must be'):
            self.option.validate()

        self.option.message_type = 5
        self.option.validate()

        self.option.message_type = 6
        with self.assertRaisesRegex(ValueError, 'type must be'):
            self.option.validate()

        self.option.message_type = 10
        with self.assertRaisesRegex(ValueError, 'type must be'):
            self.option.validate()

        self.option.message_type = 11
        self.option.validate()

        self.option.message_type = 12
        with self.assertRaisesRegex(ValueError, 'type must be'):
            self.option.validate()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'must have length 1'):
            ReconfigureMessageOption.parse(bytes.fromhex('0013000005'))

        with self.assertRaisesRegex(ValueError, 'must have length 1'):
            ReconfigureMessageOption.parse(bytes.fromhex('001300020500'))


if __name__ == '__main__':
    unittest.main()
