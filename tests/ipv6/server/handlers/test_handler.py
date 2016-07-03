import unittest

from dhcpkit.ipv6.server.handlers import Handler


class TestHandler(Handler):
    pass


class HandlerTestCase(unittest.TestCase):
    def test_str(self):
        handler = TestHandler()
        self.assertEqual(str(handler), 'TestHandler')


if __name__ == '__main__':
    unittest.main()
