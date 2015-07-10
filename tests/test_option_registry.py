import unittest

from dhcp.ipv6 import option_registry
from dhcp.ipv6.options import Option
from dhcp.parsing import StructuredElement


# noinspection PyAbstractClass
class GoodOption(Option):
    option_type = 65535


# noinspection PyAbstractClass
class BadOption(StructuredElement):
    pass


class TestOptionRegistry(unittest.TestCase):
    def setUp(self):
        # Save the real registry
        self.original_registry = option_registry.registry
        self.original_name_registry = option_registry.name_registry

        # Test with a blank one
        option_registry.registry = {}
        option_registry.name_registry = {}

    def tearDown(self):
        # Restore the real registry
        option_registry.registry = self.original_registry
        option_registry.name_registry = self.original_name_registry

    def test_good_registration(self):
        self.assertDictEqual(option_registry.registry, {})
        self.assertDictEqual(option_registry.name_registry, {})
        option_registry.register(GoodOption)
        self.assertDictEqual(option_registry.registry, {65535: GoodOption})
        self.assertDictEqual(option_registry.name_registry, {'good': GoodOption})

    def test_bad_registration(self):
        self.assertDictEqual(option_registry.registry, {})
        self.assertDictEqual(option_registry.name_registry, {})
        self.assertRaisesRegex(TypeError, 'Only Options', option_registry.register, BadOption)
        self.assertDictEqual(option_registry.registry, {})
        self.assertDictEqual(option_registry.name_registry, {})


if __name__ == '__main__':
    unittest.main()
