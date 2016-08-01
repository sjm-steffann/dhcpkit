"""
Handlers for the options defined in dhcpkit.ipv6.extensions.linklayer
"""
import logging

from dhcpkit.ipv6.extensions.linklayer_id import LinkLayerIdOption
from dhcpkit.ipv6.server.handlers.basic_relay import CopyRelayOptionHandler

logger = logging.getLogger(__name__)


class CopyLinkLayerIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for LinkLayerIdOption in relay messages
    """

    def __init__(self):
        super().__init__(LinkLayerIdOption)
