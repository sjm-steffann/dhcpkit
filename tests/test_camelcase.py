import unittest
from dhcpkit.utils import camelcase_to_underscore, camelcase_to_dash


class TestCamelCase(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
