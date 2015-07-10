import unittest

from dhcp.ipv6 import duid_registry
from dhcp.ipv6.duids import DUID
from dhcp.parsing import StructuredElement


# noinspection PyAbstractClass
class GoodDUID(DUID):
    duid_type = 255


# noinspection PyAbstractClass
class BadDUID(StructuredElement):
    pass


class TestDUIDRegistry(unittest.TestCase):
    def setUp(self):
        # Save the real registry
        self.original_registry = duid_registry.registry
        self.original_name_registry = duid_registry.name_registry

        # Test with a blank one
        duid_registry.registry = {}
        duid_registry.name_registry = {}

    def tearDown(self):
        # Restore the real registry
        duid_registry.registry = self.original_registry
        duid_registry.name_registry = self.original_name_registry

    def test_good_registration(self):
        self.assertDictEqual(duid_registry.registry, {})
        self.assertDictEqual(duid_registry.name_registry, {})
        duid_registry.register(GoodDUID)
        self.assertDictEqual(duid_registry.registry, {255: GoodDUID})
        self.assertDictEqual(duid_registry.name_registry, {'good': GoodDUID})

    def test_bad_registration(self):
        self.assertDictEqual(duid_registry.registry, {})
        self.assertDictEqual(duid_registry.name_registry, {})
        self.assertRaisesRegex(TypeError, 'Only DUIDs', duid_registry.register, BadDUID)
        self.assertDictEqual(duid_registry.registry, {})
        self.assertDictEqual(duid_registry.name_registry, {})


if __name__ == '__main__':
    unittest.main()
