from abc import abstractmethod
import configparser
import logging

from dhcp.ipv6.duids import DUID
from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import Message, RelayServerMessage, UnknownClientServerMessage, ClientServerMessage, \
    RelayForwardMessage, ReplyMessage
from dhcp.ipv6.options import ClientIdOption, ServerIdOption, StatusCodeOption, STATUS_USEMULTICAST
from dhcp.utils import camelcase_to_underscore

logger = logging.getLogger(__name__)


class HandlerException(Exception):
    """
    Base class for handler exceptions
    """


class CannotReplyError(HandlerException):
    """
    This exception signals that we cannot reply to this client.
    """


class UseMulticastError(HandlerException):
    """
    This exception signals that a STATUS_USEMULTICAST should be returned to the client.
    """


class BaseHandler(Handler):
    """
    This the base class for custom handlers. It parses the relay chain, adds the relay chain to replies and calls
    separate messages for each incoming message type.
    """

    def __init__(self, config: configparser.ConfigParser):
        """
        Initialise the handler. The config is provided from the configuration file, which is guaranteed to have a
        [handler] section.

        Objects of this class *MUST* be thread-safe.

        :param config: Contents of the configuration file
        """
        super().__init__(config)

        # Parse this once so we don't have to reparse at every request
        duid_bytes = bytes.fromhex(self.config['server']['duid'])
        length, self.server_duid = DUID.parse(duid_bytes, length=len(duid_bytes))

    @staticmethod
    def split_relay_chain(message: Message) -> (list, ClientServerMessage):
        """
        Separate the relay chain from the actual request message.

        :param message: The incoming Message
        :return: The list of RelayServerMessages (relay closest to client first) and the ClientServerMessage
        """
        relay_messages = []

        while isinstance(message, RelayServerMessage):
            relay_messages.insert(0, message)
            message = message.relayed_message

        # Validate that this is a ClientServerMessage
        assert isinstance(message, ClientServerMessage)

        return relay_messages, message

    @staticmethod
    def determine_method_name(request: ClientServerMessage) -> str:
        """
        Automatically determine the method name that can handle this type of message. The default implementation
        bases this on the name of the class of the message, but subclasses may provide a different behaviour.

        :param request: The incoming ClientServer Message
        :return: The name of the method that can handle this request
        """
        class_name = request.__class__.__name__
        underscored = camelcase_to_underscore(class_name)
        return 'handle_' + underscored

    def construct_use_multicast_reply(self, request: ClientServerMessage):
        """
        Construct a message signalling to the client that they should have used multicast.

        :param request: The incoming request
        :return: The proper answer to tell a client to use multicast
        """
        return ReplyMessage(request.transaction_id, options=[
            request.get_option_of_type(ClientIdOption),
            ServerIdOption(duid=self.server_duid),
            StatusCodeOption(STATUS_USEMULTICAST, "You cannot send requests directly to this server, "
                                                  "please use the proper multicast addresses")
        ])

    def handle(self, received_message: Message, sender: tuple, receiver: tuple) -> Message or None:
        """
        The main dispatcher for incoming messages. This method will delegate to more specific methods after preparing
        the incoming message for processing. It will also take care of constructing and sending the reply, if any.

        :param received_message: The parsed incoming request
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """
        relay_messages, request = self.split_relay_chain(received_message)

        # Check if we could actually read the message
        if isinstance(request, UnknownClientServerMessage):
            logger.warning("Received an unrecognised message of type {}".format(request.message_type))
            return None

        # Check that this message is a client->server message
        if not received_message.from_client_to_server:
            logger.warning("A server should not receive {} from a client".format(request.__class__.__name__))
            return None

        # Find handler
        method_name = self.determine_method_name(request)
        method = getattr(self, method_name, None)
        if not method or not callable(method):
            logger.warning("Cannot handle {} from {}".format(request.__class__.__name__, sender[0]))
            return None

        # Handle
        print('\x1b[34m', request, '\x1b[37m')

        # Lock and handle
        with self.lock.read_lock():
            try:
                reply = method(request, relay_messages, sender, receiver)
            except CannotReplyError:
                reply = None
            except UseMulticastError:
                reply = self.construct_use_multicast_reply(request)

        print('\x1b[32m', reply, '\x1b[37m')

        if reply and not reply.from_server_to_client:
            logger.warning("A server should not send {} to a client".format(request.__class__.__name__))
            return None

        # If it's a plain ClientServerMessage then wrap it in RelayServerMessages if necessary
        if isinstance(reply, ClientServerMessage) and isinstance(received_message, RelayForwardMessage):
            reply = received_message.wrap_response(reply)

        return reply

    @abstractmethod
    def handle_solicit_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle SolicitMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_request_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle RequestMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_confirm_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle ConfirmMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_renew_message(self, request: ClientServerMessage, relay_messages: list,
                             sender: tuple, receiver: tuple) -> Message:
        """
        Handle RenewMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_rebind_message(self, request: ClientServerMessage, relay_messages: list,
                              sender: tuple, receiver: tuple) -> Message:
        """
        Handle RebindMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_release_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle ReleaseMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_decline_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle DeclineMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_information_request_message(self, request: ClientServerMessage, relay_messages: list,
                                           sender: tuple, receiver: tuple) -> Message:
        """
        Handle InformationRequestMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """
