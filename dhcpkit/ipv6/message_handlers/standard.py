"""
A base handler that decodes the incoming request and dispatches it to methods that implement standard DHCP server
behaviour.
"""

import configparser
import logging

from dhcpkit.ipv6 import extensions, option_handlers
from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.exceptions import CannotRespondError, UseMulticastError
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.message_handlers import MessageHandler
from dhcpkit.ipv6.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.messages import Message, RelayServerMessage, SolicitMessage, RequestMessage, ConfirmMessage, \
    RenewMessage, \
    RebindMessage, InformationRequestMessage, ReleaseMessage, DeclineMessage
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.option_handlers.basic import ClientIdOptionHandler, ServerIdOptionHandler, ConfirmStatusOptionHandler, \
    ReleaseStatusOptionHandler, DeclineStatusOptionHandler
from dhcpkit.ipv6.option_handlers.interface_id import InterfaceIdOptionHandler
from dhcpkit.ipv6.option_handlers.unanswered import UnansweredIAPDOptionHandler, UnansweredIAOptionHandler
from dhcpkit.ipv6.options import ClientIdOption, ServerIdOption, StatusCodeOption, STATUS_USEMULTICAST, IAAddressOption, \
    IANAOption, IATAOption
from dhcpkit.utils import camelcase_to_underscore
from dhcpkit.ipv6.messages import ClientServerMessage, ReplyMessage, AdvertiseMessage
from dhcpkit.ipv6.options import RapidCommitOption

logger = logging.getLogger(__name__)

# Load all extensions and option handlers
extensions.load_all()
option_handlers.load_all()


class StandardMessageHandler(MessageHandler):
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

    def handle_reload(self):
        """
        Reconstruct the DUID and all option handlers from the data in the configuration.
        """
        # Parse this once so we don't have to re-parse at every request
        duid_bytes = bytes.fromhex(self.config['server']['duid'])
        length, self.server_duid = DUID.parse(duid_bytes, length=len(duid_bytes))

        # Allow rapid commit?
        self.allow_rapid_commit = self.config.getboolean('server', 'allow-rapid-commit', fallback=False)

        # Build the option handlers
        self.option_handlers = []

        # These are mandatory
        self.option_handlers.append(ServerIdOptionHandler(duid=self.server_duid))
        self.option_handlers.append(ClientIdOptionHandler())
        self.option_handlers.append(InterfaceIdOptionHandler())

        # Add the ones from the configuration
        for section_name in self.config.sections():
            parts = section_name.split(' ')
            if parts[0] != 'option':
                # Not an option
                continue

            option_handler_name = parts[1]
            option_handler_id = len(parts) > 2 and parts[2] or None
            option_handler_class = option_handlers.option_handler_name_registry.get(option_handler_name)
            if not option_handler_class or not issubclass(option_handler_class, OptionHandler):
                raise configparser.ParsingError("Unknown option handler: {}".format(option_handler_name))

            logger.debug("Creating {} from config".format(option_handler_class.__name__))
            option = option_handler_class.from_config(self.config[section_name], option_handler_id=option_handler_id)
            self.option_handlers.append(option)

        # Add cleanup handlers if they are not yet included so they run last in the post processing phase
        if not any([isinstance(option_handler, UnansweredIAOptionHandler)
                    for option_handler in self.option_handlers]):
            self.option_handlers.append(UnansweredIAOptionHandler())

        if not any([isinstance(option_handler, UnansweredIAPDOptionHandler)
                    for option_handler in self.option_handlers]):
            self.option_handlers.append(UnansweredIAPDOptionHandler())

        # Confirm/Release/Decline messages always need a status
        self.option_handlers.append(ConfirmStatusOptionHandler())
        self.option_handlers.append(ReleaseStatusOptionHandler())
        self.option_handlers.append(DeclineStatusOptionHandler())

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

        elif isinstance(bundle.request, (RequestMessage, RenewMessage, RebindMessage,
                                         ReleaseMessage, DeclineMessage, InformationRequestMessage)):
            bundle.response = ReplyMessage(bundle.request.transaction_id)

        elif isinstance(bundle.request, ConfirmMessage):
            # Receipt of Confirm Messages: If [...] there were no addresses in any of the IAs sent by the client, the
            # server MUST NOT send a reply to the client.
            found = False
            for option in bundle.request.get_options_of_type((IANAOption, IATAOption, IAPDOption)):
                if option.get_options_of_type((IAAddressOption, IAPrefixOption)):
                    # Found an address or prefix option
                    found = True
                    break

            if not found:
                raise CannotRespondError

            bundle.response = ReplyMessage(bundle.request.transaction_id)

        else:
            logger.warning("Do not know how to reply to {}".format(type(bundle.request).__name__))
            raise CannotRespondError

        # Build the plain chain of relay reply messages
        bundle.create_outgoing_relay_messages()

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
            except CannotRespondError:
                bundle.response = None
            except UseMulticastError:
                bundle.response = self.construct_use_multicast_reply(bundle)

        return bundle.outgoing_message


handler = StandardMessageHandler
