"""
Handlers for the options defined in dhcpkit.ipv6.extensions.remote_id
"""
import logging

from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.server.handlers.basic_relay import CopyRelayOptionHandler

logger = logging.getLogger(__name__)


class CopyRemoteIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for RemoteIdOptions in relay messages
    """

    def __init__(self):
        super().__init__(RemoteIdOption)
