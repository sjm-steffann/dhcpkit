import configparser
import logging

import dhcp.ipv6.extensions
from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import Message

logger = logging.getLogger(__name__)


class DumpRequestsHandler(Handler):
    def handle(self, received_message: Message, sender: tuple, receiver: tuple):
        # Print the incoming request
        logger.debug("Received message from {} to {}, {}".format(sender[0], receiver[0], received_message))

        # Not sending any response
        return None


def get_handler(config: configparser.ConfigParser):
    dhcp.ipv6.extensions.load_all()
    return DumpRequestsHandler(config)
