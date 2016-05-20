"""
Option handlers for the :rfc:`4649` options
"""
import logging

from dhcpkit.ipv6.extensions.remote_id.options import RemoteIdOption
from dhcpkit.ipv6.option_handlers import CopyRelayOptionHandler

logger = logging.getLogger(__name__)


class CopyRemoteIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for RemoteIdOptions in relay messages
    """

    def __init__(self):
        super().__init__(RemoteIdOption)
