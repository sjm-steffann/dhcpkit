"""
Test the ClientServerMessage implementation
"""
import unittest

from dhcpkit.ipv6.duids import EnterpriseDUID
from dhcpkit.ipv6.messages import ClientServerMessage, SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, ElapsedTimeOption, IANAOption, IATAOption, UnknownOption
from dhcpkit.tests.ipv6.messages import test_message
from dhcpkit.tests.ipv6.messages.test_unknown_message import unknown_packet


class ClientServerMessageTestCase(test_message.MessageTestCase):
    def setUp(self):
        # The following attributes must be overruled by child classes
        # The basics are tested with a simple SolicitMessage
        self.packet_fixture = bytes.fromhex('01'  # message_type
                                            '58595a'  # transaction_id
                                            '0001'  # option_type: OPTION_CLIENTID
                                            '0015'  # option_length
                                            '0002'  # duid_type: DUID_EN
                                            '00009d10'  # enterprise_number
                                            '444843504b6974556e697454657374'  # "DHCPKitUnitTest"
                                            '0008'  # option_type: OPTION_ELAPSED_TIME
                                            '0002'  # option_length
                                            '0000')  # elapsed_time
        self.message_fixture = SolicitMessage(transaction_id=b'XYZ', options=[
            ClientIdOption(duid=EnterpriseDUID(enterprise_number=40208, identifier=b'DHCPKitUnitTest')),
            ElapsedTimeOption(elapsed_time=0)
        ])
        self.parse_packet()

    def parse_packet(self):
        super().parse_packet()
        self.assertIsInstance(self.message, ClientServerMessage)

    def test_validate_transaction_id(self):
        self.message.transaction_id = b'AB'
        with self.assertRaisesRegex(ValueError, '3 bytes'):
            self.message.validate()

        self.message.transaction_id = b'ABCD'
        with self.assertRaisesRegex(ValueError, '3 bytes'):
            self.message.validate()

        self.message.transaction_id = 'ABC'
        with self.assertRaisesRegex(ValueError, '3 bytes'):
            self.message.validate()

    def test_validate_IAID_uniqueness(self):
        # The first one should be fine
        self.message.options.append(IANAOption(iaid=b'test'))
        self.message.validate()

        # Adding a different type with the same IAID is allowed
        self.message.options.append(IATAOption(iaid=b'test'))
        self.message.validate()

        # But adding another one with the same IAID is not allowed
        self.message.options.append(IATAOption(iaid=b'test'))
        with self.assertRaisesRegex(ValueError, 'not unique'):
            self.message.validate()

    def test_get_options_of_type(self):
        # Every ClientServerMessage has to have one ClientIdOption
        found_options = self.message.get_options_of_type(ClientIdOption)
        self.assertEqual(len(found_options), 1)
        self.assertIsInstance(found_options[0], ClientIdOption)

        # But our test-cases don't have an UnknownOption in them
        found_options = self.message.get_options_of_type(UnknownOption)
        self.assertEqual(len(found_options), 0)

    def test_get_option_of_type(self):
        # Every ClientServerMessage has to have a ClientIdOption
        found_option = self.message.get_option_of_type(ClientIdOption)
        self.assertIsInstance(found_option, ClientIdOption)

        # But our test-cases don't have an UnknownOption in them
        found_option = self.message.get_option_of_type(UnknownOption)
        self.assertIsNone(found_option)

    def test_load_from_wrong_buffer(self):
        message = self.message_class()
        with self.assertRaisesRegex(ValueError, 'buffer does not contain'):
            message.load_from(unknown_packet)


if __name__ == '__main__':
    unittest.main()
