"""
Basic handler testing
"""
import unittest

from dhcpkit.ipv6.server.handlers import Handler


class TestHandler(Handler):
    """
    A handler that doesn't do anything
    """
    pass


class HandlerTestCase(unittest.TestCase):
    def test_str(self):
        handler = TestHandler()
        self.assertEqual(str(handler), 'TestHandler')


if __name__ == '__main__':
    unittest.main()
