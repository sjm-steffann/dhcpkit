import unittest

from dhcpkit.rwlock import RWLock


class TestRWLock(unittest.TestCase):
    def setUp(self):
        self.lock = RWLock()

    def test_readers(self):
        with self.lock.read_lock():
            self.assertEqual(self.lock.readers, 1)
            self.assertEqual(self.lock.writers, 0)
            self.assertFalse(self.lock.blocked_for_readers)
            self.assertTrue(self.lock.blocked_for_writers)

            # Multiple readers can hold the lock simultaneously
            with self.lock.read_lock():
                self.assertEqual(self.lock.readers, 2)
                self.assertEqual(self.lock.writers, 0)
                self.assertFalse(self.lock.blocked_for_readers)
                self.assertTrue(self.lock.blocked_for_writers)

    def test_writers(self):
        with self.lock.write_lock():
            self.assertEqual(self.lock.readers, 0)
            self.assertEqual(self.lock.writers, 1)
            self.assertTrue(self.lock.blocked_for_readers)
            self.assertTrue(self.lock.blocked_for_writers)

    def test_unlocked(self):
        self.assertEqual(self.lock.readers, 0)
        self.assertEqual(self.lock.writers, 0)
        self.assertFalse(self.lock.blocked_for_readers)
        self.assertFalse(self.lock.blocked_for_writers)


if __name__ == '__main__':
    unittest.main()
