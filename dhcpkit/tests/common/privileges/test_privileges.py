"""
Test whether the common privilege functions work as intended
"""
import grp
import logging
import os
import pwd
import unittest

from dhcpkit.common.privileges import drop_privileges, restore_privileges


class PrivilegeTestCase(unittest.TestCase):
    def setUp(self):
        # Make sure our effective UID is root, if we can
        if os.getuid() == 0:
            os.seteuid(0)
            os.setegid(0)

    def tearDown(self):
        # Make sure to restore our effective UID to root, if we can
        if os.getuid() == 0:
            os.seteuid(0)
            os.setegid(0)

    @staticmethod
    def get_nobody() -> pwd.struct_passwd:
        try:
            return pwd.getpwnam('nobody')
        except KeyError:
            return pwd.struct_passwd(pw_name='nobody',
                                     pw_passwd='*',
                                     pw_uid=-1,
                                     pw_gid=-1,
                                     pw_gecos='Unprivileged User',
                                     pw_dir='/tmp',
                                     pw_shell='/usr/bin/false')

    @staticmethod
    def get_somebody() -> pwd.struct_passwd:
        return pwd.getpwall()[-1]

    def test_drop_privileges_not_necessary(self):
        # Get whatever our current user already is
        user = pwd.getpwuid(os.geteuid())
        group = grp.getgrgid(os.getegid())

        with self.assertLogs('', level='NOTSET') as cm:
            drop_privileges(user, group, permanent=False)

        self.assertEqual(len(cm.records), 1)
        self.assertRegex(cm.records[0].msg, 'Already .*, not changing privileges')

    @unittest.skipIf(os.getuid() != 0, "Need to be root to test privilege manipulation")
    def test_drop_privileges_with_restore(self):
        # Get some user
        user = self.get_somebody()
        group = grp.getgrgid(user.pw_gid)

        # Switch to a different account
        nobody = self.get_nobody()
        os.setegid(nobody.pw_uid)
        os.seteuid(nobody.pw_gid)

        with self.assertLogs('', level='NOTSET') as cm:
            drop_privileges(user, group, permanent=False)

        self.assertEqual(len(cm.records), 2)
        self.assertRegex(cm.records[0].msg, 'Restored root privileges')
        self.assertRegex(cm.records[1].msg, 'Dropped privileges to ')

    @unittest.skipIf(os.getuid() == 0, "Need to be non-root to test privilege manipulation handling")
    def test_restore_privileges_as_non_root(self):
        with self.assertLogs('', level='NOTSET') as cm:
            restore_privileges()

        self.assertEqual(len(cm.records), 1)
        self.assertRegex(cm.records[0].msg, 'Root privileges have been permanently dropped, continuing as ')

    @unittest.skipIf(os.getuid() != 0, "Need to be root to test privilege manipulation")
    def test_restore_privileges_as_root(self):
        with self.assertLogs('', level='NOTSET') as cm:
            logger = logging.getLogger('test_restore_privileges_as_root')
            logger.debug("This should be the only log entry")

            restore_privileges()

        self.assertEqual(len(cm.records), 1)
        self.assertEqual(cm.records[0].msg, 'This should be the only log entry')

    @unittest.skipIf(os.getuid() != 0, "Need to be root to test privilege manipulation")
    def test_restore_privileges_as_effective_other(self):
        # Switch to a different account
        nobody = self.get_nobody()
        os.setegid(nobody.pw_uid)
        os.seteuid(nobody.pw_gid)

        with self.assertLogs('', level='NOTSET') as cm:
            restore_privileges()

        self.assertEqual(len(cm.records), 1)
        self.assertEqual(cm.records[0].msg, 'Restored root privileges')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
