"""
Extra datatypes for the server configuration
"""

# noinspection PyUnresolvedReferences
import datetime
from ipaddress import IPv6Address

from typing import Type

from dhcpkit.ipv6.messages import Message
from dhcpkit.utils import normalise_hex, camelcase_to_dash

# noinspection PyUnresolvedReferences
from dhcpkit.common.server.config_datatypes import *


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


def unicast_address(value: str) -> IPv6Address:
    """
    Parse an IPv6 address and make sure it is a unicast address

    :param value: The address as string
    :return: The parsed IPv6 address
    """
    address = IPv6Address(value)
    if address.is_link_local or address.is_loopback or address.is_multicast or address.is_unspecified:
        raise ValueError("Address must be a routable IPv6 address")
    return address


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


def message_type(value: str) -> Type[Message]:
    """
    Parse the value as the name of a DHCPv6 message type

    :param value: The name of the message type
    :return: The message class
    """
    from dhcpkit.ipv6.message_registry import message_registry

    # Prepare the value
    search_value = camelcase_to_dash(value)

    try:
        return message_registry.by_name[search_value]
    except KeyError:
        raise ValueError("{} is not a valid message type".format(value))
