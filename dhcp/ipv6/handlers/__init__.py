from abc import ABC
import configparser
import logging
import threading

from dhcp.ipv6.listening_socket import ListeningSocket
from dhcp.ipv6.messages import Message, RelayServerMessage

logger = logging.getLogger(__name__)


class Handler(ABC):
    def __init__(self, config: configparser.ConfigParser):
        """
        Initialise the handler. The config is provided from the configuration file, which is guaranteed to have a
        [handler] section.

        Objects of this class *MUST* be thread-safe and store their request state in self.local.

        :param config: Contents of the configuration file
        """
        self.config = config

        # Create a thread-local store for keeping request state in
        self.local = threading.local()

    @staticmethod
    def get_relay_chain(message: Message):
        relay_messages = []

        while isinstance(message, RelayServerMessage):
            relay_messages.insert(0, message)
            message = message.relayed_message

        return relay_messages, message

    def handle(self, listening_socket: ListeningSocket, sender: tuple, message: Message):
        """
        The main dispatcher for incoming messages. This method will delegate to more specific methods after preparing
        the incoming message for processing. It will also take care of constructing and sending the reply, if any.

        :param listening_socket: The ListeningSocket object that received the message
        :param sender: The address of the sender
        :param message: The parsed incoming request
        """
        try:
            self.local.relay_messages, self.local.request = self.get_relay_chain(message)
        except Exception as e:
            # Catch-all exception handler
            logger.exception("Cought unexpected exception {!r}".format(e))
