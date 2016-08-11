"""
Extra datatypes for the IPv6 DHCP server
"""
import datetime
import grp
import pwd

from dhcpkit.utils import encode_domain, normalise_hex

__all__ = ['domain_name', 'user_name', 'group_name']


def domain_name(value: str) -> str:
    """
    Validate and clean a domain name.

    :param value: Domain name
    :return: Validated and cleaned domain name
    """
    # Lowercase
    value = value.lower()

    # Test validity by trying to encode it
    encode_domain(value)

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


def number_of_workers(value: str) -> int:
    """
    The number of worker processes, must be 1 or more
    :param value: The number of processes
    :return: The validated number of processes
    """
    value = int(value)
    if value < 1:
        raise ValueError("Number of workers must be at least 1")
    return value


def hex_bytes(value: str) -> bytes:
    """
    A sequence of bytes provided as a hexadecimal string.

    :param value: The hexadecimal string
    :return: The corresponding bytes
    """
    value = normalise_hex(value)
    return bytes.fromhex(value)


def iso8601_timestamp(value: str) -> int:
    """
    Convert an ISO8601 timestamp into a unix timestamp

    :param value: ISO8601 formatted timestamp
    :return: Unix timestamp
    """
    dt = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())


def unsigned_int_8(value: str) -> int:
    """
    Parse value as an integer and verify that it is an unsigned 8-bit value.

    :param value: The number as a string
    :return: The corresponding integer
    """
    value = int(value)
    if not (0 <= value < 2 ** 8):
        raise ValueError("The specified value must be an unsigned 8-bit integer")
    return value


def unsigned_int_16(value: str) -> int:
    """
    Parse value as an integer and verify that it is an unsigned 16-bit value.

    :param value: The number as a string
    :return: The corresponding integer
    """
    value = int(value)
    if not (0 <= value < 2 ** 16):
        raise ValueError("The specified value must be an unsigned 16-bit integer")
    return value


def unsigned_int_32(value: str) -> int:
    """
    Parse value as an integer and verify that it is an unsigned 32-bit value.

    :param value: The number as a string
    :return: The corresponding integer
    """
    value = int(value)
    if not (0 <= value < 2 ** 32):
        raise ValueError("The specified value must be an unsigned 32-bit integer")
    return value
