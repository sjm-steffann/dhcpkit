"""
Utility functions for IPv6 DHCP
"""
import logging
from ipaddress import IPv6Address, IPv6Network
from typing import Iterable, List, Optional, Tuple

from dhcpkit.ipv6.messages import ClientServerMessage, Message, RelayForwardMessage, UnknownMessage

logger = logging.getLogger(__name__)


def split_relay_chain(message: Message) -> Tuple[Optional[ClientServerMessage], List[RelayForwardMessage]]:
    """
    Separate the relay chain from the actual request message.

    :param message: The incoming message
    :returns: The request and the chain of relay messages starting with the one closest to the client
    """
    relay_messages = []
    while isinstance(message, RelayForwardMessage):
        relay_messages.insert(0, message)
        message = message.relayed_message

    # Check if we could actually read the message
    if isinstance(message, UnknownMessage):
        logger.warning("Received an unrecognised message of type {}".format(message.message_type))
        return None, []

    # Check that this message is a client->server message
    if not isinstance(message, ClientServerMessage) or not message.from_client_to_server:
        logger.warning("A server should not receive {} from a client".format(message.__class__.__name__))
        return None, []

    # Save it as the request
    return message, relay_messages


def address_in_prefixes(address: IPv6Address, prefixes: Iterable[IPv6Network]) -> bool:
    """
    Check whether the given address is part of one of the given prefixes

    :param address: The IPv6 address to check
    :param prefixes: The list of IPv6 prefixes
    :type prefixes: list[IPv6Network]
    :return: Whether the address is part of one of the prefixes
    """
    for prefix in prefixes:
        if address in prefix:
            return True

    return False


def prefix_overlaps_prefixes(prefix: IPv6Network, prefixes: Iterable[IPv6Network]) -> bool:
    """
    Check whether the given address is part of one of the given prefixes

    :param prefix: The IPv6 prefix to check
    :param prefixes: The list of IPv6 prefixes
    :type prefixes: list[IPv6Network]
    :return: Whether the address is part of one of the prefixes
    """
    for other_prefix in prefixes:
        if prefix.overlaps(other_prefix):
            return True

    return False


def is_global_unicast(address: IPv6Address) -> bool:
    """
    Check if an address is a global unicast address according to :rfc:`4291`.

    :param address: The address to check
    :return: Whether it is a global unicast address
    """
    return not (address == IPv6Address('::') or
                address == IPv6Address('::1') or
                address in IPv6Network('ff00::/8') or
                address in IPv6Network('fe80::/10'))
