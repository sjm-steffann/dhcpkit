import unittest

from dhcp.ipv6.utils import create_transaction_id


class TestTransactionID(unittest.TestCase):
    def test_transaction_id(self):
        transaction_id = create_transaction_id()
        self.assertIsInstance(transaction_id, bytes)
        self.assertEqual(len(transaction_id), 3)


if __name__ == '__main__':
    unittest.main()
