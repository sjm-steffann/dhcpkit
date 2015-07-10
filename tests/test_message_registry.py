import importlib
import unittest

from dhcp.ipv6 import message_registry
from dhcp.ipv6.messages import Message
from dhcp.parsing import StructuredElement


# noinspection PyAbstractClass
class GoodMessage(Message):
    message_type = 255


# noinspection PyAbstractClass
class BadMessage(StructuredElement):
    pass


class TestMessageRegistry(unittest.TestCase):
    def setUp(self):
        importlib.reload(message_registry)

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
