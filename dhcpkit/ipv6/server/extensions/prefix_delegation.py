"""
Server extension to handle prefix delegation options properly
"""
import logging

from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, STATUS_NO_PREFIX_AVAIL
from dhcpkit.ipv6.messages import RebindMessage, ReleaseMessage, RenewMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import STATUS_NO_BINDING, StatusCodeOption
from dhcpkit.ipv6.server.handlers import CannotRespondError, Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from typing import List

logger = logging.getLogger(__name__)


def create_cleanup_handlers() -> List[Handler]:
    """
    Create handlers to clean up stuff in the transaction bundle

    :return: Handlers to add to the handler chain
    """
    return [UnansweredIAPDOptionHandler()]


class UnansweredIAPDOptionHandler(Handler):
    """
    A handler that answers to all unanswered IAPDOptions

    :param authoritative: Whether this handler is authorised to tell clients to stop using prefixes
    """

    def __init__(self, authoritative: bool = True):
        super().__init__()
        self.authoritative = authoritative

    def handle(self, bundle: TransactionBundle):
        """
        Make sure that every :class:`.IAPDOption` is answered.

        :param bundle: The transaction bundle
        """
        for option in bundle.get_unhandled_options(IAPDOption):
            if isinstance(bundle.request, (SolicitMessage, RequestMessage)):
                # If the delegating router will not assign any prefixes to any IA_PDs in a subsequent Request from the
                # requesting router, the delegating router MUST send an Advertise message to the requesting router that
                # includes the IA_PD with no prefixes in the IA_PD and a Status Code option in the IA_PD containing
                # status code NoPrefixAvail and a status message for the user
                #
                # We do the same for unanswered requests
                bundle.response.options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NO_PREFIX_AVAIL, "No prefixes available")
                ]))

            elif isinstance(bundle.request, RenewMessage):
                # Renew message: If the delegating router cannot find a binding for the requesting router's IA_PD the
                # delegating router returns the IA_PD containing no prefixes with a Status Code option set to
                # NoBinding in the Reply message.

                prefixes = ', '.join(map(str, option.get_prefixes()))
                logger.warning("No handler renewed {}: sending NoBinding status".format(prefixes))

                bundle.response.options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NO_BINDING, "No prefixes assigned to you")
                ]))

            elif isinstance(bundle.request, RebindMessage):
                # Rebind message: If the delegating router cannot find a binding for the requesting router's IA_PD and
                # the delegating router determines that the prefixes in the IA_PD are not appropriate for the link to
                # which the requesting router's interface is attached according to the delegating routers explicit
                # configuration, the delegating router MAY send a Reply message to the requesting router containing
                # the IA_PD with the lifetimes of the prefixes in the IA_PD set to zero.  This Reply constitutes an
                # explicit notification to the requesting router that the prefixes in the IA_PD are no longer valid.
                #
                # If the delegating router is unable to determine if the prefix is not appropriate for the link, the
                # Rebind message is discarded.
                #
                # The authoritative flag indicates whether this option may claim whether it is able to determine if a
                # prefix is appropriate for the link.
                if not self.authoritative:
                    raise CannotRespondError("Server is not authoritative and cannot reject rebind")

                prefixes = ', '.join(map(str, option.get_prefixes()))
                logger.warning("No handler answered rebind of {}: withdrawing prefixes".format(prefixes))

                reply_suboptions = []
                for suboption in option.get_options_of_type(IAPrefixOption):
                    reply_suboptions.append(IAPrefixOption(suboption.prefix, preferred_lifetime=0, valid_lifetime=0))

                bundle.response.options.append(IAPDOption(option.iaid, options=reply_suboptions))

            elif isinstance(bundle.request, ReleaseMessage):
                # For each IA in the Release message for which the server has no binding information, the server adds an
                # IA option using the IAID from the Release message, and includes a Status Code option with the value
                # NoBinding in the IA option.  No other options are included in the IA option.
                bundle.response.options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NO_BINDING, "No prefixes assigned to you")
                ]))
