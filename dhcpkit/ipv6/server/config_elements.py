"""
The basic configuration objects
"""

import grp
import logging

from pip.utils import cached_property

from dhcpkit.common.server.logging.config_elements import Logging
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.messages import RelayServerMessage, Message, SolicitMessage, AdvertiseMessage, RequestMessage, \
    RenewMessage, RebindMessage, ReleaseMessage, InformationRequestMessage, DeclineMessage, ReplyMessage, ConfirmMessage
from dhcpkit.ipv6.options import IANAOption, IATAOption, IAAddressOption, ClientIdOption, ServerIdOption, \
    StatusCodeOption, STATUS_USEMULTICAST
from dhcpkit.ipv6.server.config_action import Action, CannotRespondError, UseMulticastError
from dhcpkit.ipv6.server.config_filter import Filter
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.server.utils import determine_local_duid

logger = logging.getLogger(__name__)


class MainConfig(Filter):
    """
    The top level configuration element
    """

    # This is not really a filter, it matches everything
    filter_description = 'root'
    filter_condition = '*'

    def clean_config_section(self):
        """
        Clean up the config, making sure we have user, group and DUID
        """
        if self._section.group is None:
            # No group specified
            try:
                self._section.group = grp.getgrgid(self._section.user.pw_gid)
            except KeyError:
                raise ValueError("User {} has a non-existent primary group {}".format(self._section.user.pw_name,
                                                                                      self._section.user.pw_gid))

        if not self._section.server_id:
            self._section.server_id = determine_local_duid()

    @cached_property
    def logging(self) -> Logging:
        """
        Shortcut to the logging configuration.

        :return: Logging configuration
        """
        return self._section.logging

    def match(self, bundle: TransactionBundle) -> bool:
        """
        The config root matches every message.

        :param bundle: The transaction bundle
        :return: True
        """
        return True

    def get_actions(self, bundle: TransactionBundle) -> [Action]:
        """
        Get all actions that are going to be applied to the request in the bundle.

        :param bundle: The transaction bundle
        :return: The list of actions to apply
        """

        # Build the actions list
        actions = []

        # if self.allow_rapid_commit:
        #     # Rapid commit happens as the first thing in the post() stage
        #     self.actions.append(RapidCommitOptionHandler(self.rapid_commit_rejections))

        # These are mandatory
        # actions.append(ServerIdOptionHandler(duid=self.server_duid))
        # actions.append(ClientIdOptionHandler())
        # actions.append(InterfaceIdOptionHandler())

        # Add the ones from the configuration
        actions += super().get_actions(bundle)

        # Add cleanup handlers so they run last in the handling phase
        # actions.append(UnansweredIAOptionHandler())
        # actions.append(UnansweredIAPDOptionHandler())

        # Confirm/Release/Decline messages always need a status
        # actions.append(ConfirmStatusOptionHandler())
        # actions.append(ReleaseStatusOptionHandler())
        # actions.append(DeclineStatusOptionHandler())

        return actions

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
            ServerIdOption(duid=self._section.server_id),
            StatusCodeOption(STATUS_USEMULTICAST, "You cannot send requests directly to this server, "
                                                  "please use the proper multicast addresses")
        ])

    def handle(self, received_message: RelayServerMessage, received_over_multicast: bool,
               marks: [str] = None) -> Message or None:
        """
        The main dispatcher for incoming messages.

        :param received_message: The parsed incoming request
        :param received_over_multicast: Whether the request was received over multicast
        :param marks: Marks to add to the transaction bundle, usually set by the listener
        :returns: The message to reply with
        """

        # Create the transaction
        bundle = TransactionBundle(incoming_message=received_message,
                                   received_over_multicast=received_over_multicast,
                                   allow_rapid_commit=self._section.allow_rapid_commit)

        if not bundle.request:
            # Nothing to do...
            return None

        # Add the marks so the filters can take them into account
        if marks:
            for mark in marks:
                bundle.add_mark(mark)

        # Collect the actions
        actions = self.get_actions(bundle)

        try:
            # Pre-process the request
            for option_handler in actions:
                option_handler.pre(bundle)

            # Init the response
            self.init_response(bundle)

            # Process the request
            for option_handler in actions:
                option_handler.handle(bundle)

            # Post-process the request
            for option_handler in actions:
                option_handler.post(bundle)

        except CannotRespondError:
            logger.debug("Cannot respond to this message: ignoring")
            bundle.response = None

        except UseMulticastError:
            logger.debug("Unicast request received when multicast is required: informing client")
            bundle.response = self.construct_use_multicast_reply(bundle)

        return bundle.outgoing_message
