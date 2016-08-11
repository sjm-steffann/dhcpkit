"""
Extra datatypes for the server configuration
"""

from ipaddress import IPv6Address

from dhcpkit.ipv6.messages import Message
from dhcpkit.utils import camelcase_to_dash
from typing import Type


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
