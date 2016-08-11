"""
Test the camelcase conversion functions
"""
import unittest

from dhcpkit.utils import camelcase_to_dash, camelcase_to_underscore


class CamelCaseTestCase(unittest.TestCase):
    def test_camelcase_to_underscore(self):
        self.assertEqual(camelcase_to_underscore('CamelCase'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('CamelCASE'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('CAMELCase'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('MyCAMELCase'), 'my_camel_case')
        self.assertEqual(camelcase_to_underscore('Camel123Case'), 'camel123_case')
        self.assertEqual(camelcase_to_underscore('CAMEL123Case'), 'camel123_case')
        self.assertEqual(camelcase_to_underscore('Camel-Case'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('camel-case'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('Camel_Case'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('camel_case'), 'camel_case')
        self.assertEqual(camelcase_to_underscore('SimpleCamelCase'), 'simple_camel_case')
        self.assertEqual(camelcase_to_underscore('DHCPTest'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCP-Test'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCP--Test'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCP_Test'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCP__Test'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCP-_Test'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCP_-Test'), 'dhcp_test')
        self.assertEqual(camelcase_to_underscore('DHCPv6Test'), 'dhc_pv6_test')
        self.assertEqual(camelcase_to_underscore('DHCPV6Test'), 'dhcpv6_test')
        self.assertEqual(camelcase_to_underscore('DHCPVersion6plusTest'), 'dhcp_version6plus_test')

    def test_camelcase_to_dash(self):
        self.assertEqual(camelcase_to_dash('CamelCase'), 'camel-case')
        self.assertEqual(camelcase_to_dash('CamelCASE'), 'camel-case')
        self.assertEqual(camelcase_to_dash('CAMELCase'), 'camel-case')
        self.assertEqual(camelcase_to_dash('MyCAMELCase'), 'my-camel-case')
        self.assertEqual(camelcase_to_dash('Camel123Case'), 'camel123-case')
        self.assertEqual(camelcase_to_dash('CAMEL123Case'), 'camel123-case')
        self.assertEqual(camelcase_to_dash('Camel-Case'), 'camel-case')
        self.assertEqual(camelcase_to_dash('camel-case'), 'camel-case')
        self.assertEqual(camelcase_to_dash('Camel_Case'), 'camel-case')
        self.assertEqual(camelcase_to_dash('camel_case'), 'camel-case')
        self.assertEqual(camelcase_to_dash('SimpleCamelCase'), 'simple-camel-case')
        self.assertEqual(camelcase_to_dash('DHCPTest'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCP-Test'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCP--Test'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCP_Test'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCP__Test'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCP-_Test'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCP_-Test'), 'dhcp-test')
        self.assertEqual(camelcase_to_dash('DHCPv6Test'), 'dhc-pv6-test')
        self.assertEqual(camelcase_to_dash('DHCPV6Test'), 'dhcpv6-test')
        self.assertEqual(camelcase_to_dash('DHCPVersion6plusTest'), 'dhcp-version6plus-test')

if __name__ == '__main__':
    unittest.main()
