from abc import ABC
import configparser
import logging
import re
import threading

from dhcp.ipv6.listening_socket import ListeningSocket
from dhcp.ipv6.messages import Message, RelayServerMessage, UnknownClientServerMessage

logger = logging.getLogger(__name__)


class Handler(ABC):
    def __init__(self, config: configparser.ConfigParser):
        """
        Initialise the handler. The config is provided from the configuration file, which is guaranteed to have a
        [handler] section.

        Objects of this class *MUST* be thread-safe.

        :param config: Contents of the configuration file
        """
        self.config = config

    @staticmethod
    def get_relay_chain(message: Message) -> (list, Message):
        """
        Separate the relay chain from the actual request message.

        :param message: The incoming Message
        :return: The list of RelayServerMessages (relay closest to client first) and the ClientServerMessage
        """
        relay_messages = []

        while isinstance(message, RelayServerMessage):
            relay_messages.insert(0, message)
            message = message.relayed_message

        return relay_messages, message

    @staticmethod
    def determine_method_name(request: Message) -> str:
        """
        Automatically determine the method name that can handle this type of message. The default implementation
        bases this on the name of the class of the message, but subclasses may provide a different behaviour.

        :param request: The incoming ClientServer Message
        :return: The name of the method that can handle this request
        """
        class_name = request.__class__.__name__

        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)

        return 'handle_' + s2.lower()

    def handle(self, listening_socket: ListeningSocket, sender: tuple, message: Message):
        """
        The main dispatcher for incoming messages. This method will delegate to more specific methods after preparing
        the incoming message for processing. It will also take care of constructing and sending the reply, if any.

        :param listening_socket: The ListeningSocket object that received the message
        :param sender: The address of the sender
        :param message: The parsed incoming request
        """
        try:
            relay_messages, request = self.get_relay_chain(message)

            # Check if we could actually read the message
            if isinstance(request, UnknownClientServerMessage):
                logger.warning("Received an unrecognised message of type {}".format(request.message_type))
                return

            # Check that this message is a client->server message
            if not message.from_client_to_server:
                logger.warning("A server should not receive {} from a client".format(request.__class__.__name__))
                return

            # Find handler
            method_name = self.determine_method_name(request)
            method = getattr(self, method_name, None)
            if not method or not callable(method):
                logger.warning("Cannot handle {} from {}".format(request.__class__.__name__, sender[0]))
                return

            # Handle


        except Exception as e:
            # Catch-all exception handler
            logger.exception("Cought unexpected exception {!r}".format(e))
