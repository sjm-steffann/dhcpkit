"""
DHCP Request handler that just prints incoming requests
"""

import logging

from dhcpkit.ipv6 import extensions
from dhcpkit.ipv6.message_handlers import MessageHandler
from dhcpkit.ipv6.messages import Message, RelayServerMessage

logger = logging.getLogger(__name__)

# Load all extensions so we can handle them
extensions.load_all()


class DumpRequestsMessageHandler(MessageHandler):
    """
    DHCP Request handler that just prints incoming requests
    """

    def handle(self, received_message: RelayServerMessage, received_over_multicast: bool) -> Message or None:
        """
        Display the received message.

        :param received_message: The parsed incoming request, wrapped in an 'internal' RelayServerMessage
        :param received_over_multicast: Whether the request was received over multicast
        :returns: The message to reply with
        """
        # Print the incoming request
        received_using = 'multicast' if received_over_multicast else 'unicast'
        logger.debug("Received {} message {}".format(received_using, received_message))

        # Not sending any response
        return None


handler = DumpRequestsMessageHandler
