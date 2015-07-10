import importlib
import unittest

from dhcp.ipv6 import option_registry
from dhcp.ipv6.options import Option
from dhcp.parsing import StructuredElement


class GoodOption(Option):
    option_type = 65535


class BadOption(StructuredElement):
    pass


class TestOptionRegistry(unittest.TestCase):
    def setUp(self):
        importlib.reload(option_registry)

    def test_good_registration(self):
        self.assertDictEqual(option_registry.registry, {})
        self.assertDictEqual(option_registry.name_registry, {})
        option_registry.register(GoodOption)
        self.assertDictEqual(option_registry.registry, {65535: GoodOption})
        self.assertDictEqual(option_registry.name_registry, {'good': GoodOption})

    def test_bad_registration(self):
        self.assertDictEqual(option_registry.registry, {})
        self.assertDictEqual(option_registry.name_registry, {})
        self.assertRaises(TypeError, option_registry.register, BadOption)
        self.assertDictEqual(option_registry.registry, {})
        self.assertDictEqual(option_registry.name_registry, {})


if __name__ == '__main__':
    unittest.main()
