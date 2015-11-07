"""
Option handlers for the basic :rfc:`3315` options
"""

import logging

from dhcpkit.ipv6.option_handlers import CopyRelayOptionHandler
from dhcpkit.ipv6.options import InterfaceIdOption

logger = logging.getLogger(__name__)


class InterfaceIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for InterfaceIdOptions in relay messages
    """

    def __init__(self):
        super().__init__(InterfaceIdOption)
