import unittest

import dhcpkit.ipv6.messages
from dhcpkit.protocol_element import ProtocolElement


# noinspection PyAbstractClass
class GoodMessage(dhcpkit.ipv6.messages.Message):
    message_type = 255


# noinspection PyAbstractClass
class BadMessage(ProtocolElement):
    pass


class TestMessageRegistry(unittest.TestCase):
    def setUp(self):
        # Save the real registry
        self.original_registry = dhcpkit.ipv6.messages.message_registry
        self.original_name_registry = dhcpkit.ipv6.messages.message_name_registry

        # Test with a blank one
        dhcpkit.ipv6.messages.message_registry = {}
        dhcpkit.ipv6.messages.message_name_registry = {}

    def tearDown(self):
        # Restore the real registry
        dhcpkit.ipv6.messages.message_registry = self.original_registry
        dhcpkit.ipv6.messages.message_name_registry = self.original_name_registry

    def test_good_registration(self):
        self.assertDictEqual(dhcpkit.ipv6.messages.message_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.messages.message_name_registry, {})
        dhcpkit.ipv6.messages.register_message(GoodMessage)
        self.assertDictEqual(dhcpkit.ipv6.messages.message_registry, {255: GoodMessage})
        self.assertDictEqual(dhcpkit.ipv6.messages.message_name_registry, {'good': GoodMessage})

    def test_bad_registration(self):
        self.assertDictEqual(dhcpkit.ipv6.messages.message_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.messages.message_name_registry, {})
        self.assertRaisesRegex(TypeError, 'Only Messages', dhcpkit.ipv6.messages.register_message, BadMessage)
        self.assertDictEqual(dhcpkit.ipv6.messages.message_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.messages.message_name_registry, {})


if __name__ == '__main__':
    unittest.main()
