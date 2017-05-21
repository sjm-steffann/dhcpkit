"""
Common code to handle privileges
"""

import grp
import logging.handlers
import os
import pwd

logger = logging.getLogger(__name__)


def drop_privileges(user: pwd.struct_passwd, group: grp.struct_group, permanent: bool = True):
    """
    Drop root privileges and change to something more safe.

    :param user: The tuple with user info
    :param group: The tuple with group info
    :param permanent: Whether we want to drop just the euid (temporary), or all uids (permanent)
    """
    # Don't do anything if we are already the right user
    if os.geteuid() == user.pw_uid and os.getegid() == group.gr_gid:
        logger.debug("Already {}/{}, not changing privileges".format(user.pw_name, group.gr_name))
        return

    # Restore euid=0 if we have previously changed it
    if os.geteuid() != 0 and os.getuid() == 0:
        restore_privileges()

    if os.geteuid() != 0:
        raise RuntimeError("Not running as root: cannot change uid/gid to {}/{}".format(user.pw_name, group.gr_name))

    # Remove group privileges
    os.setgroups([])

    if permanent:
        os.setgid(group.gr_gid)
        os.setuid(user.pw_uid)
    else:
        os.setegid(group.gr_gid)
        os.seteuid(user.pw_uid)

    # Ensure a very conservative umask
    os.umask(0o077)

    if permanent:
        logger.debug("Permanently dropped privileges to {}/{}".format(user.pw_name, group.gr_name))
    else:
        logger.debug("Dropped privileges to {}/{}".format(user.pw_name, group.gr_name))


def restore_privileges():
    """
    Restore root privileges
    """
    if os.getuid() != 0:
        user = pwd.getpwuid(os.getuid())
        logger.warning("Root privileges have been permanently dropped, continuing as {}".format(user.pw_name))
        return

    if os.geteuid() == 0 and os.getegid() == 0:
        # Already root, don't need to do anything
        return

    os.seteuid(0)
    os.setegid(0)

    logger.debug("Restored root privileges")
