"""
The code to handle a message
"""
import logging
import multiprocessing
from typing import Iterable, List, Optional

from dhcpkit.common.server.logging import DEBUG_HANDLING
from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.extensions.leasequery import LeasequeryMessage, LeasequeryReplyMessage, STATUS_MALFORMED_QUERY, \
    STATUS_NOT_ALLOWED, STATUS_UNKNOWN_QUERY_TYPE
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.messages import AdvertiseMessage, ConfirmMessage, DeclineMessage, InformationRequestMessage, \
    RebindMessage, ReleaseMessage, RenewMessage, ReplyMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, IAAddressOption, IANAOption, IATAOption, STATUS_USE_MULTICAST, \
    ServerIdOption, StatusCodeOption
from dhcpkit.ipv6.server.extension_registry import server_extension_registry
from dhcpkit.ipv6.server.filters import Filter
from dhcpkit.ipv6.server.handlers import CannotRespondError, Handler, ReplyWithLeasequeryError, ReplyWithStatusError, \
    UseMulticastError
from dhcpkit.ipv6.server.handlers.client_id import ClientIdHandler
from dhcpkit.ipv6.server.handlers.interface_id import InterfaceIdOptionHandler
from dhcpkit.ipv6.server.handlers.rapid_commit import RapidCommitHandler
from dhcpkit.ipv6.server.handlers.server_id import ForOtherServerError, ServerIdHandler
from dhcpkit.ipv6.server.handlers.status_option import AddMissingStatusOptionHandler
from dhcpkit.ipv6.server.handlers.unanswered_ia import UnansweredIAOptionHandler
from dhcpkit.ipv6.server.handlers.unicast import RejectUnwantedUnicastHandler
from dhcpkit.ipv6.server.statistics import StatisticsSet
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Message processing class
    """

    def __init__(self, server_id: DUID, sub_filters: Iterable[Filter] = None, sub_handlers: Iterable[Handler] = None,
                 allow_rapid_commit: bool = False, rapid_commit_rejections: bool = False):
        self.server_id = server_id
        self.sub_filters = list(sub_filters or [])
        self.sub_handlers = list(sub_handlers or [])
        self.allow_rapid_commit = allow_rapid_commit
        self.rapid_commit_rejections = rapid_commit_rejections

        # Prepare static stuff
        self.setup_handlers = self.get_setup_handlers()
        self.cleanup_handlers = self.get_cleanup_handlers()

    def worker_init(self):
        """
        Separate initialisation that will be called in each worker process that is created. Things that can't be forked
        (think database connections etc) have to be initialised here.
        """
        logger.debug("Initialising MessageHandler in {}".format(multiprocessing.current_process().name))

        # Cascade to sub-filters and sub-handlers
        for sub_filter in self.sub_filters:
            sub_filter.worker_init()

        for sub_handler in self.sub_handlers:
            sub_handler.worker_init()

    def get_handlers(self, bundle: TransactionBundle) -> List[Handler]:
        """
        Get all handlers that are going to be applied to the request in the bundle.

        :param bundle: The transaction bundle
        :return: The list of handlers to apply
        """

        # Build the handlers list
        handlers = []
        """:type: [Handler]"""

        # Add setup handlers
        handlers += self.setup_handlers

        # Apply all sub-filters and collect their handlers. The idea behind this is that handlers on more-specific
        # filters take precedence over handlers on the outer filters.
        for sub_filter in self.sub_filters:
            handlers += sub_filter.get_handlers(bundle)

        # Now add our own handlers
        handlers += self.sub_handlers

        # Add cleanup handlers
        handlers += self.cleanup_handlers

        return handlers

    def get_setup_handlers(self) -> List[Handler]:
        """
        Build a list of setup handlers and cache it

        :return: The list of handlers
        """
        handlers = []
        """:type: [Handler]"""

        if self.allow_rapid_commit:
            # Rapid commit happens as the first thing in the post() stage
            handlers.append(RapidCommitHandler(self.rapid_commit_rejections))

        # These are mandatory
        handlers.append(ServerIdHandler(duid=self.server_id))
        handlers.append(ClientIdHandler())
        handlers.append(InterfaceIdOptionHandler())

        # Add setup handlers from extensions
        for extension_name, extension in server_extension_registry.items():
            create_setup_handlers = getattr(extension, 'create_setup_handlers', None)
            if create_setup_handlers:
                setup_handlers = create_setup_handlers()
                for setup_handler in setup_handlers:
                    logger.log(DEBUG_HANDLING, "Extension {} added {} to setup phase".format(
                        extension_name, setup_handler.__class__.__name__
                    ))
                handlers += setup_handlers

        return handlers

    @staticmethod
    def get_cleanup_handlers() -> List[Handler]:
        """
        Build a list of cleanup handlers and cache it

        :return: The list of handlers
        """
        handlers = []
        """:type: [Handler]"""

        # Reject unicast requests unless they have been explicitly permitted
        handlers.append(RejectUnwantedUnicastHandler())

        # Add cleanup handlers so they run last in the handling phase
        handlers.append(UnansweredIAOptionHandler())

        # Add cleanup handlers from extensions
        for extension_name, extension in server_extension_registry.items():
            create_cleanup_handlers = getattr(extension, 'create_cleanup_handlers', None)
            if create_cleanup_handlers:
                cleanup_handlers = create_cleanup_handlers()
                for cleanup_handler in cleanup_handlers:
                    logger.log(DEBUG_HANDLING, "Extension {} added {} to cleanup phase".format(
                        extension_name, cleanup_handler.__class__.__name__
                    ))
                handlers += cleanup_handlers

        # Confirm/Release/Decline messages always need a status
        handlers.append(AddMissingStatusOptionHandler())

        return handlers

    @staticmethod
    def init_response(bundle: TransactionBundle):
        """
        Create the message object in bundle.response

        :param bundle: The transaction bundle
        """
        # Start building the response
        if isinstance(bundle.request, SolicitMessage):
            bundle.response = AdvertiseMessage(bundle.request.transaction_id)

        elif isinstance(bundle.request, (RequestMessage, RenewMessage, RebindMessage,
                                         ReleaseMessage, DeclineMessage, InformationRequestMessage)):
            bundle.response = ReplyMessage(bundle.request.transaction_id)

        elif isinstance(bundle.request, ConfirmMessage):
            # Receipt of Confirm Messages: If [...] there were no addresses in any of the IAs sent by the client, the
            # server MUST NOT send a reply to the client.
            for option in bundle.request.get_options_of_type(IANAOption, IATAOption, IAPDOption):
                if option.get_options_of_type((IAAddressOption, IAPrefixOption)):
                    # Found an address or prefix option
                    break
            else:
                # Not found: ignore request
                raise CannotRespondError("No IAs present in confirm reply")

            bundle.response = ReplyMessage(bundle.request.transaction_id)

        elif isinstance(bundle.request, LeasequeryMessage):
            # The Leasequery protocol has its own reply type
            bundle.response = LeasequeryReplyMessage(bundle.request.transaction_id)

        else:
            raise CannotRespondError("Do not know how to reply to {}".format(type(bundle.request).__name__))

        # Build the plain chain of relay reply messages
        bundle.create_outgoing_relay_messages()

    def construct_plain_status_reply(self, bundle: TransactionBundle, option: StatusCodeOption) -> ReplyMessage:
        """
        Construct a reply message signalling a status code to the client.

        :param bundle: The transaction bundle containing the incoming request
        :param option: The status code option to include in the reply
        :return: A reply with only the bare necessities and a status code
        """
        return ReplyMessage(bundle.request.transaction_id, options=[
            bundle.request.get_option_of_type(ClientIdOption),
            ServerIdOption(duid=self.server_id),
            option
        ])

    def construct_leasequery_status_reply(self, bundle: TransactionBundle,
                                          option: StatusCodeOption) -> LeasequeryReplyMessage:
        """
        Construct a leasequery reply message signalling a status code to the client.

        :param bundle: The transaction bundle containing the incoming request
        :param option: The status code option to include in the reply
        :return: A leasequery reply with only the bare necessities and a status code
        """
        return LeasequeryReplyMessage(bundle.request.transaction_id, options=[
            bundle.request.get_option_of_type(ClientIdOption),
            ServerIdOption(duid=self.server_id),
            option
        ])

    def construct_use_multicast_reply(self, bundle: TransactionBundle) -> Optional[ReplyMessage]:
        """
        Construct a message signalling to the client that they should have used multicast.

        :param bundle: The transaction bundle containing the incoming request
        :return: The proper answer to tell a client to use multicast
        """
        # Make sure we only tell this to requests that came in over unicast
        if bundle.received_over_multicast:
            logger.error("Not telling client to use multicast, they already did...")
            return None

        return self.construct_plain_status_reply(
            bundle,
            StatusCodeOption(STATUS_USE_MULTICAST, "You cannot send requests directly to this server, "
                                                   "please use the proper multicast addresses")
        )

    def handle(self, bundle: TransactionBundle, statistics: StatisticsSet):
        """
        The main dispatcher for incoming messages.

        :param bundle: The transaction bundle
        :param statistics: Container for shared memory with statistics counters
        """
        if not bundle.request:
            # Nothing to do...
            return

        # Update the allow_rapid_commit flag
        bundle.allow_rapid_commit = self.allow_rapid_commit

        # Count the incoming message type
        statistics.count_message_in(bundle.request.message_type)

        # Log what we are doing (low-detail, so not DEBUG_HANDLING here)
        logger.debug("Handling {}".format(bundle))

        # Collect the handlers
        handlers = self.get_handlers(bundle)

        # Analyse pre
        for handler in handlers:
            # noinspection PyBroadException
            try:
                handler.analyse_pre(bundle)
            except:
                # Ignore all errors, analysis isn't that important
                logger.exception("{} pre analysis failed".format(handler.__class__.__name__))

        try:
            # Pre-process the request
            for handler in handlers:
                handler.pre(bundle)

            # Init the response
            self.init_response(bundle)

            # Process the request
            for handler in handlers:
                logger.log(DEBUG_HANDLING, "Applying {}".format(handler))
                handler.handle(bundle)

            # Post-process the request
            for handler in handlers:
                handler.post(bundle)

        except ForOtherServerError as e:
            # Specific form of CannotRespondError that should have its own log message
            message = str(e) or 'Message is for another server'
            logger.debug("{}: ignoring".format(message))
            statistics.count_for_other_server()
            bundle.response = None

        except CannotRespondError as e:
            message = str(e) or 'Cannot respond to this message'
            logger.warning("{}: ignoring".format(message))
            statistics.count_do_not_respond()
            bundle.response = None

        except UseMulticastError:
            logger.debug("Unicast request received when multicast is required: informing client")
            statistics.count_use_multicast()
            bundle.response = self.construct_use_multicast_reply(bundle)

        except ReplyWithStatusError as e:
            # Leasequery has its own reply message type
            if isinstance(e, ReplyWithLeasequeryError):
                bundle.response = self.construct_leasequery_status_reply(bundle, e.option)
            else:
                bundle.response = self.construct_plain_status_reply(bundle, e.option)

            logger.warning("Replying with {}".format(e))

            # Update the right counter based on the status code
            if e.option.status_code == STATUS_UNKNOWN_QUERY_TYPE:
                statistics.count_unknown_query_type()
            elif e.option.status_code == STATUS_MALFORMED_QUERY:
                statistics.count_malformed_query()
            elif e.option.status_code == STATUS_NOT_ALLOWED:
                statistics.count_not_allowed()
            else:
                statistics.count_other_error()

        # Analyse post
        for handler in handlers:
            # noinspection PyBroadException
            try:
                handler.analyse_post(bundle)
            except:
                # Ignore all errors, analysis isn't that important
                logger.exception("{} post analysis failed".format(handler.__class__.__name__))

        if bundle.response:
            logger.log(DEBUG_HANDLING, "Responding with {}".format(bundle.response.__class__.__name__))

            # Count the outgoing message type
            statistics.count_message_out(bundle.response.message_type)
        else:
            logger.log(DEBUG_HANDLING, "Not responding")
