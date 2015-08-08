import unittest

import dhcpkit.ipv6.duids
from dhcpkit.protocol_element import ProtocolElement


# noinspection PyAbstractClass
class GoodDUID(dhcpkit.ipv6.duids.DUID):
    duid_type = 255


# noinspection PyAbstractClass
class BadDUID(ProtocolElement):
    pass


class TestDUIDRegistry(unittest.TestCase):
    def setUp(self):
        # Save the real registry
        self.original_registry = dhcpkit.ipv6.duids.duid_registry
        self.original_name_registry = dhcpkit.ipv6.duids.duid_name_registry

        # Test with a blank one
        dhcpkit.ipv6.duids.duid_registry = {}
        dhcpkit.ipv6.duids.duid_name_registry = {}

    def tearDown(self):
        # Restore the real registry
        dhcpkit.ipv6.duids.duid_registry = self.original_registry
        dhcpkit.ipv6.duids.duid_name_registry = self.original_name_registry

    def test_good_registration(self):
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_name_registry, {})
        dhcpkit.ipv6.duids.register_duid(GoodDUID)
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_registry, {255: GoodDUID})
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_name_registry, {'good': GoodDUID})

    def test_bad_registration(self):
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_name_registry, {})
        self.assertRaisesRegex(TypeError, 'Only DUIDs', dhcpkit.ipv6.duids.register_duid, BadDUID)
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.duids.duid_name_registry, {})


if __name__ == '__main__':
    unittest.main()
