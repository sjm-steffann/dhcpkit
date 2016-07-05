"""
Extra datatypes for the IPv6 DHCP server
"""
import grp
import pwd

import re

__all__ = ['domain_name', 'user_name', 'group_name']


def domain_name(value: str) -> str:
    """
    Validate and clean a domain name.

    :param value: Domain name
    :return: Validated and cleaned domain name
    """
    # Lowercase
    value = value.lower()

    # Simple basic checks: no whitespace
    if re.match(r'\s', value):
        raise ValueError("Domain names cannot contain whitespace")

    # no labels longer than 63
    for label in value.split('.'):
        if not (0 <= len(label) < 63):
            raise ValueError("Domain name labels must be between 1 and 63 characters long")

    # Ok for now
    return value


def user_name(value: str) -> pwd.struct_passwd:
    """
    Validate the given user name

    :param value: User name
    :return: Resolved user
    """
    try:
        return pwd.getpwnam(value)
    except KeyError:
        raise ValueError("User with name '{}' not found".format(value))


def group_name(value: str) -> grp.struct_group:
    """
    Validate the given group name

    :param value: Group name
    :return: Resolved group
    """
    try:
        return grp.getgrnam(value)
    except KeyError:
        raise ValueError("Group with name '{}' not found".format(value))
