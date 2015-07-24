"""
A base handler that decodes the incoming request and dispatches it to methods that implement standard DHCP server
behaviour.
"""

import configparser
import logging

from dhcp.ipv6 import extensions, option_registry
from dhcp.ipv6.duids import DUID
from dhcp.ipv6.handlers import Handler, CannotReplyError, UseMulticastError
from dhcp.ipv6.handlers.transaction_bundle import TransactionBundle
from dhcp.ipv6.messages import Message, RelayServerMessage, SolicitMessage
from dhcp.ipv6.option_handlers import UnansweredIANAOptionHandler, UnansweredIATAOptionHandler
from dhcp.ipv6.options import ClientIdOption, ServerIdOption, StatusCodeOption, STATUS_USEMULTICAST, OptionHandler, \
    Option
from dhcp.utils import camelcase_to_underscore
from dhcp.ipv6.messages import ClientServerMessage, ReplyMessage, AdvertiseMessage
from dhcp.ipv6.options import RapidCommitOption

logger = logging.getLogger(__name__)

# Load all extensions so we can handle them
extensions.load_all()


class StandardHandler(Handler):
    """
    This is the base class for standard handlers. It implements the standard handling of the DHCP protocol. Subclasses
    only need to provide the right addresses and options.

    :type server_duid: DUID
    :type allow_rapid_commit: bool
    :type option_handlers: list[OptionHandler]
    """

    server_duid = None
    allow_rapid_commit = False
    option_handlers = None

    def __init__(self, config: configparser.ConfigParser):
        """
        Initialise the handler. The config is provided from the configuration file, which is guaranteed to have a
        [handler] section.

        Objects of this class *MUST* be thread-safe.

        :param config: Contents of the configuration file
        """
        super().__init__(config)
        self.handle_reload()

    # noinspection PyDocstring
    def handle_reload(self):
        # Parse this once so we don't have to re-parse at every request
        duid_bytes = bytes.fromhex(self.config['server']['duid'])
        length, self.server_duid = DUID.parse(duid_bytes, length=len(duid_bytes))

        # Allow rapid commit?
        self.allow_rapid_commit = self.config.getboolean('server', 'allow-rapid-commit', fallback=False)

        # Build the option handlers
        self.option_handlers = []

        # These are mandatory
        self.option_handlers.append(ServerIdOption.handler_from_duid(duid=self.server_duid))
        self.option_handlers.append(ClientIdOption.handler())

        # Add the ones from the configuration
        for section_name in self.config.sections():
            parts = section_name.split(' ')
            if parts[0] != 'option':
                # Not an option
                continue

            option_name = parts[1]
            option_class = option_registry.name_registry.get(option_name)
            """:type: Option"""

            if not option_class or not issubclass(option_class, Option):
                raise configparser.ParsingError("Unknown option: {}".format(option_name))

            section_name = 'option {}'.format(option_name)
            option = option_class.handler_from_config(self.config[section_name])
            self.option_handlers.append(option)

        # Add cleanup handlers
        self.option_handlers.append(UnansweredIANAOptionHandler())
        self.option_handlers.append(UnansweredIATAOptionHandler())

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

    def construct_use_multicast_reply(self, bundle: TransactionBundle):
        """
        Construct a message signalling to the client that they should have used multicast.

        :param bundle: The transaction bundle containing the incoming request
        :return: The proper answer to tell a client to use multicast
        """
        # Make sure we only tell this to requests that came in over multicast
        if not bundle.received_over_multicast:
            return None

        return ReplyMessage(bundle.request.transaction_id, options=[
            bundle.request.get_option_of_type(ClientIdOption),
            ServerIdOption(duid=self.server_duid),
            StatusCodeOption(STATUS_USEMULTICAST, "You cannot send requests directly to this server, "
                                                  "please use the proper multicast addresses")
        ])

    def init_response(self, bundle: TransactionBundle):
        """
        Create the message object in bundle.response

        :param bundle: The transaction bundle
        """
        # Start building the response
        if isinstance(bundle.request, SolicitMessage):
            if self.allow_rapid_commit and bundle.request.get_option_of_type(RapidCommitOption) is not None:
                bundle.response = ReplyMessage(bundle.request.transaction_id)
            else:
                bundle.response = AdvertiseMessage(bundle.request.transaction_id)
        else:
            logger.warning("Do not know how to reply to {}".format(type(bundle.request).__name__))
            raise CannotReplyError

    def handle(self, received_message: RelayServerMessage, received_over_multicast: bool) -> Message or None:
        """
        The main dispatcher for incoming messages.

        :param received_message: The parsed incoming request
        :param received_over_multicast: Whether the request was received over multicast
        :returns: The message to reply with
        """

        bundle = TransactionBundle(incoming_message=received_message, received_over_multicast=received_over_multicast)

        if not bundle.request:
            # Nothing to do...
            return None

        # Handle
        print('\x1b[34m{!s}\x1b[37m'.format(bundle.incoming_message))

        # Lock and handle
        with self.lock.read_lock():
            try:
                # Pre-process the request
                for option_handler in self.option_handlers:
                    option_handler.pre(bundle)

                # Init the response
                self.init_response(bundle)

                # Process the request
                for option_handler in self.option_handlers:
                    option_handler.handle(bundle)

                # Post-process the request
                for option_handler in self.option_handlers:
                    option_handler.post(bundle)
            except CannotReplyError:
                bundle.response = None
            except UseMulticastError:
                bundle.response = self.construct_use_multicast_reply(bundle)

        print('\x1b[32m{!s}\x1b[37m'.format(bundle.outgoing_message))

        return bundle.outgoing_message


handler = StandardHandler
