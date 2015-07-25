"""
DHCP Request handler that just prints incoming requests
"""

import logging

from dhcp.ipv6 import extensions
from dhcp.ipv6.message_handlers import MessageHandler
from dhcp.ipv6.messages import Message, RelayServerMessage

logger = logging.getLogger(__name__)

# Load all extensions so we can handle them
extensions.load_all()


class DumpRequestsMessageHandler(MessageHandler):
    """
    DHCP Request handler that just prints incoming requests
    """

    # noinspection PyDocstring
    def handle(self, received_message: RelayServerMessage, received_over_multicast: bool) -> Message or None:
        # Print the incoming request
        logger.debug("Received {} message {}".format(received_over_multicast and 'multicast' or 'unicast',
                                                     received_message))

        # Not sending any response
        return None


handler = DumpRequestsMessageHandler
