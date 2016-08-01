"""
Handlers for the options defined in dhcpkit.ipv6.extensions.subscriber_id
"""
import logging

from dhcpkit.ipv6.extensions.subscriber_id import SubscriberIdOption
from dhcpkit.ipv6.server.handlers.basic_relay import CopyRelayOptionHandler

logger = logging.getLogger(__name__)


class CopySubscriberIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for SubscriberIdOptions in relay messages
    """

    def __init__(self):
        super().__init__(SubscriberIdOption)
