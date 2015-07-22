"""
A base handler that decodes the incoming request and dispatches it to the right methods.
"""

from abc import abstractmethod
import configparser
from ipaddress import IPv6Address
import logging

from dhcp.ipv6.duids import DUID
from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import Message, ClientServerMessage, \
    RelayForwardMessage, ReplyMessage
from dhcp.ipv6.options import ClientIdOption, ServerIdOption, StatusCodeOption, STATUS_USEMULTICAST
from dhcp.utils import camelcase_to_underscore
from ipv6 import option_registry
from ipv6.messages import UnknownMessage
from ipv6.options import Option

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


class TransactionBundle:
    """
    A bundle with all data about a transaction. This makes it much easier to pass around multiple pieces of information.

    :type handler: BaseHandler
    :type sender: tuple
    :type receiver: tuple
    :type incoming_message: Message
    :type request: ClientServerMessage
    :type relay_messages: list[RelayForwardMessage]
    :type response: ClientServerMessage
    :type handler_state: dict[OptionHandler, object]
    """

    def __init__(self, handler: BaseHandler, sender: tuple, receiver: tuple, incoming_message: Message):
        self.handler = handler
        self.sender = sender
        self.receiver = receiver
        self.incoming_message = incoming_message

        # Convenience properties for easy access to the request and chain without having to walk the chain every time
        self.request, self.relay_messages = self.split_relay_chain(incoming_message)

        # This is where the user puts the response
        # (without reply relay chain, that is added by @property outgoing_message)
        self.response = None

        # State holding space for option handlers, indexed by option handler object
        self.handler_state = {}

    @staticmethod
    def split_relay_chain(message: Message) -> (ClientServerMessage, [RelayForwardMessage]):
        """
        Separate the relay chain from the actual request message.

        :param message: The incoming message
        :returns: The request and the chain of relay messages starting with the one closest to the client
        """
        relay_messages = []
        while isinstance(message, RelayForwardMessage):
            relay_messages.insert(0, message)
            message = message.relayed_message

        # Check if we could actually read the message
        if isinstance(message, UnknownMessage):
            logger.warning("Received an unrecognised message of type {}".format(message.message_type))
            return None, None

        # Check that this message is a client->server message
        if not isinstance(message, ClientServerMessage) or not message.from_client_to_server:
            logger.warning("A server should not receive {} from a client".format(message.__class__.__name__))
            return None, None

        # Save it as the request
        return message, relay_messages

    @property
    def outgoing_message(self):
        """
        Wrap the response in a relay chain if necessary
        """
        if self.response is None:
            # No response is ok
            return None

        response = self.response
        if response and not response.from_server_to_client:
            logger.error("A server should not send {} to a client".format(response.__class__.__name__))
            return None

        # If it's a plain ClientServerMessage then wrap it in RelayReplyMessage if necessary
        if isinstance(response, ClientServerMessage) and self.relay_messages:
            response = self.relay_messages[-1].wrap_response(response)

        return response


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

        # Parse this once so we don't have to re-parse at every request
        duid_bytes = bytes.fromhex(self.config['server']['duid'])
        length, self.server_duid = DUID.parse(duid_bytes, length=len(duid_bytes))

        # Allow rapid commit?
        self.allow_rapid_commit = self.config.getboolean('server', 'allow-rapid-commit', fallback=False)

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

    def get_options_from_config(self) -> [Option]:
        """
        Look for option configurations in the config. Section names are [option xyz] where xyz is an option name.

        :return: The options
        """
        options = []
        for section_name in self.config.sections():
            parts = section_name.split(' ')
            if parts[0] != 'option':
                # Not an option
                continue

            option_name = parts[1]
            option_class = option_registry.name_registry.get(option_name)
            if not option_class:
                raise configparser.ParsingError("Unknown option: {}".format(option_name))

            section_name = 'option {}'.format(option_name)
            option = option_class.from_config_section(self.config[section_name])
            options.append(option)

        return options

    def construct_use_multicast_reply(self, bundle: TransactionBundle):
        """
        Construct a message signalling to the client that they should have used multicast.

        :param bundle: The transaction bundle containing the incoming request
        :return: The proper answer to tell a client to use multicast
        """
        # Make sure we only tell this to requests that came in over multicast
        if not IPv6Address(bundle.receiver[0]).is_multicast:
            return None

        return ReplyMessage(bundle.request.transaction_id, options=[
            bundle.request.get_option_of_type(ClientIdOption),
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
        bundle = TransactionBundle(handler=self,
                                   sender=sender, receiver=receiver,
                                   incoming_message=received_message)

        if not bundle.request:
            # Nothing to do...
            return None

        # Check if there is a ServerId in the request
        server_id = bundle.request.get_option_of_type(ServerIdOption)
        if server_id and server_id.duid != self.server_duid:
            # This message is not for this server
            return None

        # Find handler
        method_name = self.determine_method_name(bundle.request)
        method = getattr(self, method_name, None)
        if not method or not callable(method):
            logger.warning("Cannot handle {} from {}".format(bundle.request.__class__.__name__, sender[0]))
            return None

        # Handle
        print('\x1b[34m', bundle.request, '\x1b[37m')

        # Lock and handle
        with self.lock.read_lock():
            try:
                bundle.reply = method(bundle)
            except CannotReplyError:
                bundle.reply = None
            except UseMulticastError:
                bundle.reply = self.construct_use_multicast_reply(bundle)

        print('\x1b[32m', bundle.reply, '\x1b[37m')

        return bundle.outgoing_message

    @abstractmethod
    def handle_solicit_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle SolicitMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_request_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle RequestMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_confirm_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle ConfirmMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_renew_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle RenewMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_rebind_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle RebindMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_release_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle ReleaseMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_decline_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle DeclineMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """

    @abstractmethod
    def handle_information_request_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        """
        Handle InformationRequestMessages

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: The message to reply with
        """
