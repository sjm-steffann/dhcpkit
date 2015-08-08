import unittest

import dhcpkit.ipv6.options
from dhcpkit.protocol_element import ProtocolElement


# noinspection PyAbstractClass
class GoodOption(dhcpkit.ipv6.options.Option):
    option_type = 65535


# noinspection PyAbstractClass
class BadOption(ProtocolElement):
    pass


class TestOptionRegistry(unittest.TestCase):
    def setUp(self):
        # Save the real registry
        self.original_registry = dhcpkit.ipv6.options.option_registry
        self.original_name_registry = dhcpkit.ipv6.options.option_name_registry

        # Test with a blank one
        dhcpkit.ipv6.options.option_registry = {}
        dhcpkit.ipv6.options.option_name_registry = {}

    def tearDown(self):
        # Restore the real registry
        dhcpkit.ipv6.options.option_registry = self.original_registry
        dhcpkit.ipv6.options.option_name_registry = self.original_name_registry

    def test_good_registration(self):
        self.assertDictEqual(dhcpkit.ipv6.options.option_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.options.option_name_registry, {})
        dhcpkit.ipv6.options.register_option(GoodOption)
        self.assertDictEqual(dhcpkit.ipv6.options.option_registry, {65535: GoodOption})
        self.assertDictEqual(dhcpkit.ipv6.options.option_name_registry, {'good': GoodOption})

    def test_bad_registration(self):
        self.assertDictEqual(dhcpkit.ipv6.options.option_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.options.option_name_registry, {})
        self.assertRaisesRegex(TypeError, 'Only Options', dhcpkit.ipv6.options.register_option, BadOption)
        self.assertDictEqual(dhcpkit.ipv6.options.option_registry, {})
        self.assertDictEqual(dhcpkit.ipv6.options.option_name_registry, {})


if __name__ == '__main__':
    unittest.main()
