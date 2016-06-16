"""
Handlers for the basic :rfc:`3315` options
"""

import logging

from dhcpkit.ipv6.options import ClientIdOption
from dhcpkit.ipv6.server.handlers.basic import CopyOptionHandler

logger = logging.getLogger(__name__)


class ClientIdHandler(CopyOptionHandler):
    """
    The handler for ClientIdOptions
    """

    def __init__(self):
        super().__init__(ClientIdOption, always_send=True)
