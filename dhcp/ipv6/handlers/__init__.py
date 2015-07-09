from abc import ABC
import configparser
import logging

from dhcp.ipv6 import option_registry
from dhcp.ipv6.duids import DUID
from dhcp.ipv6.messages import Message, RelayServerMessage, UnknownClientServerMessage, ClientServerMessage, \
    RelayForwardMessage
from dhcp.ipv6.options import OptionRequestOption
from dhcp.utils import camelcase_to_underscore

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

        # Parse this once so we don't have to reparse at every request
        duid_bytes = bytes.fromhex(self.config['server']['duid'])
        length, self.server_duid = DUID.parse(duid_bytes, length=len(duid_bytes))

    def reload(self) -> None:
        """
        This is called by the server on SIGHUP so the configuration can be reloaded, caches can be cleared etc.
        """
        pass

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
        underscored = camelcase_to_underscore(class_name)
        return 'handle_' + underscored

    def get_options_from_config(self):
        """
        Look in the config for sections named [option xyz] where xyz is the name of a DHCP option. Create option
        objects from the data in those sections.

        :return: [Option]
        """
        option_names = [section_name.split(' ')[1]
                        for section_name in self.config.sections()
                        if section_name.split(' ')[0] == 'option']

        options = []
        for section_name in option_names:
            if '-' in section_name or '_' in section_name:
                option_name = section_name.replace('-', '_').lower()
            else:
                option_name = camelcase_to_underscore(section_name)

            option_class = option_registry.name_registry.get(option_name)
            if not option_class:
                raise configparser.ParsingError("Unknown option: {}".format(option_name))

            section_name = 'option {}'.format(section_name)
            option = option_class.from_config_section(self.config[section_name])
            options.append(option)

        return options

    @staticmethod
    def filter_options_on_oro(options: list, oro: OptionRequestOption):
        """
        Only return the options that the client requested

        :param options: The list of options
        :param oro: The OptionRequestOption to use as a filter
        :return: The filtered list of options
        """
        if not oro:
            return options

        return [option for option in options if option.option_type in oro.requested_options]

    def handle(self, received_message: Message, sender: tuple, receiver: tuple) -> None or Message or (Message, tuple):
        """
        The main dispatcher for incoming messages. This method will delegate to more specific methods after preparing
        the incoming message for processing. It will also take care of constructing and sending the reply, if any.

        :param received_message: The parsed incoming request
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        """
        relay_messages, request = self.get_relay_chain(received_message)

        # Check if we could actually read the message
        if isinstance(request, UnknownClientServerMessage):
            logger.warning("Received an unrecognised message of type {}".format(request.message_type))
            return

        # Check that this message is a client->server message
        if not received_message.from_client_to_server:
            logger.warning("A server should not receive {} from a client".format(request.__class__.__name__))
            return

        # Find handler
        method_name = self.determine_method_name(request)
        method = getattr(self, method_name, None)
        if not method or not callable(method):
            logger.warning("Cannot handle {} from {}".format(request.__class__.__name__, sender[0]))
            return

        # Handle
        print('\x1b[34m', request, '\x1b[37m')

        result = method(request, relay_messages, sender, receiver)

        # A result is None, a Message or a (Message, destination) tuple.
        if isinstance(result, Message):
            outgoing_message = result
        elif isinstance(result, tuple):
            outgoing_message = result[0]
        else:
            outgoing_message = None

        print('\x1b[32m', outgoing_message, '\x1b[37m')

        if outgoing_message and not outgoing_message.from_server_to_client:
            logger.warning("A server should not send {} to a client".format(request.__class__.__name__))
            return

        # If it's a plain ClientServerMessage then wrap it in RelayServerMessages if necessary
        if isinstance(result, ClientServerMessage) and isinstance(received_message, RelayForwardMessage):
            return received_message.wrap_response(result)

        return result
