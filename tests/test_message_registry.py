import unittest

from dhcpkit.ipv6 import message_registry
from dhcpkit.ipv6.messages import Message
from dhcpkit.protocol_element import ProtocolElement


# noinspection PyAbstractClass
class GoodMessage(Message):
    message_type = 255


# noinspection PyAbstractClass
class BadMessage(ProtocolElement):
    pass


class TestMessageRegistry(unittest.TestCase):
    def setUp(self):
        # Save the real registry
        self.original_registry = message_registry.registry
        self.original_name_registry = message_registry.name_registry

        # Test with a blank one
        message_registry.registry = {}
        message_registry.name_registry = {}

    def tearDown(self):
        # Restore the real registry
        message_registry.registry = self.original_registry
        message_registry.name_registry = self.original_name_registry

    def test_good_registration(self):
        self.assertDictEqual(message_registry.registry, {})
        self.assertDictEqual(message_registry.name_registry, {})
        message_registry.register(GoodMessage)
        self.assertDictEqual(message_registry.registry, {255: GoodMessage})
        self.assertDictEqual(message_registry.name_registry, {'good': GoodMessage})

    def test_bad_registration(self):
        self.assertDictEqual(message_registry.registry, {})
        self.assertDictEqual(message_registry.name_registry, {})
        self.assertRaisesRegex(TypeError, 'Only Messages', message_registry.register, BadMessage)
        self.assertDictEqual(message_registry.registry, {})
        self.assertDictEqual(message_registry.name_registry, {})


if __name__ == '__main__':
    unittest.main()
