"""
Test whether the basic stuff of Registry works as intended
"""
import logging
import unittest
from collections import OrderedDict

import pkg_resources
from dhcpkit.ipv6.options import ClientIdOption, ServerIdOption
from dhcpkit.registry import Registry


class TestRegistry(Registry):
    """
    A registry that doesn't exist to test with
    """
    entry_point = 'dhcpkit.tests.registry'


class ElementOccurrenceTestCase(unittest.TestCase):
    def test_registry_loading(self):
        entry_map = pkg_resources.get_entry_map('dhcpkit')

        # Steal the distribution from an existing entry
        dist = entry_map['dhcpkit.ipv6.options']['1'].dist

        entry_map['dhcpkit.tests.registry'] = {
            # Test string ID
            'one': pkg_resources.EntryPoint.parse('one = dhcpkit.ipv6.options:ClientIdOption', dist=dist),

            # Test numerical ID
            '1': pkg_resources.EntryPoint.parse('1 = dhcpkit.ipv6.options:ServerIdOption', dist=dist),
        }

        test_registry = TestRegistry()
        self.assertEqual(len(test_registry), 2)
        self.assertEqual(test_registry['one'], ClientIdOption)
        self.assertEqual(test_registry[1], ServerIdOption)

    def test_duplicate_entries(self):
        entry_map = pkg_resources.get_entry_map('dhcpkit')

        # Steal the distribution from an existing entry
        dist = entry_map['dhcpkit.ipv6.options']['1'].dist

        # Test one ID appearing multiple times (can happen if other packages overwrite our keys)
        entry_map['dhcpkit.tests.registry'] = OrderedDict()
        entry_map['dhcpkit.tests.registry']['1'] = pkg_resources.EntryPoint.parse(
            '1 = dhcpkit.ipv6.options:ClientIdOption', dist=dist)
        entry_map['dhcpkit.tests.registry']['1 '] = pkg_resources.EntryPoint.parse(
            '1 = dhcpkit.ipv6.options:ServerIdOption', dist=dist)

        with self.assertLogs('dhcpkit.registry', logging.WARNING) as cm:
            test_registry = TestRegistry()

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], '^WARNING:.*:Multiple entry points found for TestRegistry 1')

        self.assertEqual(len(test_registry), 1)
        self.assertEqual(test_registry[1], ClientIdOption)

    def test_bad_entry(self):
        entry_map = pkg_resources.get_entry_map('dhcpkit')

        # Steal the distribution from an existing entry
        dist = entry_map['dhcpkit.ipv6.options']['1'].dist

        entry_map['dhcpkit.tests.registry'] = {
            # Test something that doesn't exist
            'bad': pkg_resources.EntryPoint.parse('bad = dhcpkit.tests.does_not_exist:DummyOption', dist=dist),
        }

        with self.assertLogs('dhcpkit.registry', logging.WARNING) as cm:
            test_registry = TestRegistry()

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], '^ERROR:.*:Entry point bad .* could not be loaded')

        self.assertEqual(len(test_registry), 0)


if __name__ == '__main__':
    unittest.main()
