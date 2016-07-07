"""
Option handlers for the basic :rfc:`3315` options
"""

import logging

from dhcpkit.ipv6.options import InterfaceIdOption
from dhcpkit.ipv6.server.handlers.basic_relay import CopyRelayOptionHandler

logger = logging.getLogger(__name__)


class InterfaceIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for InterfaceIdOptions in relay messages
    """

    def __init__(self):
        super().__init__(InterfaceIdOption)
