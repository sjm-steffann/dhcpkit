"""
Option handlers that cleans up unanswered requests
"""
import logging

from dhcpkit.ipv6.messages import ConfirmMessage, DeclineMessage, RebindMessage, ReleaseMessage, RenewMessage, \
    RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import IAAddressOption, IANAOption, IATAOption, STATUS_NOT_ON_LINK, STATUS_NO_ADDRS_AVAIL, \
    STATUS_NO_BINDING, StatusCodeOption
from dhcpkit.ipv6.server.handlers import CannotRespondError, Handler
from dhcpkit.ipv6.server.handlers.utils import force_status
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class UnansweredIAOptionHandler(Handler):
    """
    A handler that answers to all unanswered IANAOptions and IATAOptions

    :param authoritative: Whether this handler is authorised to tell clients to stop using prefixes
    """

    def __init__(self, authoritative: bool = True):
        super().__init__()
        self.authoritative = authoritative

    def handle(self, bundle: TransactionBundle):
        """
        Make sure that every :class:`.IANAOption` and :class:`.IATAOption` is answered.

        :param bundle: The transaction bundle
        """
        for option in bundle.get_unhandled_options((IANAOption, IATAOption)):
            ia_class = type(option)

            if isinstance(bundle.request, (SolicitMessage, RequestMessage)):
                # If the server will not assign any addresses to any IAs in a subsequent Request from the client, the
                # server MUST send an Advertise message to the client that includes only a Status Code option with code
                # NoAddrsAvail and a status message for the user
                #
                # We do the same for unanswered requests
                bundle.response.options.append(ia_class(option.iaid, options=[
                    StatusCodeOption(STATUS_NO_ADDRS_AVAIL, "No addresses available")
                ]))

            elif isinstance(bundle.request, ConfirmMessage):
                # When the server receives a Confirm message, the server determines whether the addresses in the
                # Confirm message are appropriate for the link to which the client is attached.  If all of the
                # addresses in the Confirm message pass this test, the server returns a status of Success.  If any of
                # the addresses do not pass this test, the server returns a status of NotOnLink.  If the server is
                # unable to perform this test (for example, the server does not have information about prefixes on the
                # link to which the client is connected), or there were no addresses in any of the IAs sent by the
                # client, the server MUST NOT send a reply to the client.
                #
                # The "there were no addresses in any of the IAs sent by the client" check is done by the message
                # handler.
                if not self.authoritative:
                    raise CannotRespondError("Server is not authoritative and cannot reject confirm")

                addresses = ', '.join(map(str, option.get_addresses()))
                logger.warning("No handler confirmed {}: sending NotOnLink status".format(addresses))

                force_status(bundle.response.options,
                             StatusCodeOption(STATUS_NOT_ON_LINK, "Those addresses are not appropriate on this link"))

            elif isinstance(bundle.request, RenewMessage):
                # If the server cannot find a client entry for the IA the server returns the IA containing no addresses
                # with a Status Code option set to NoBinding in the Reply message.
                #
                # If the server finds that any of the addresses are not appropriate for the link to which the client is
                # attached, the server returns the address to the client with lifetimes of 0.
                addresses = ', '.join(map(str, option.get_addresses()))

                if self.authoritative:
                    logger.warning("No handler renewed {}: withdrawing addresses".format(addresses))

                    reply_suboptions = []
                    for suboption in option.get_options_of_type(IAAddressOption):
                        reply_suboptions.append(IAAddressOption(suboption.address,
                                                                preferred_lifetime=0, valid_lifetime=0))

                    bundle.response.options.append(ia_class(option.iaid, options=reply_suboptions))
                else:
                    logger.warning("No handler renewed {}: sending NoBinding status".format(addresses))

                    bundle.response.options.append(ia_class(option.iaid, options=[
                        StatusCodeOption(STATUS_NO_BINDING, "No addresses assigned to you")
                    ]))

            elif isinstance(bundle.request, RebindMessage):
                # If the server cannot find a client entry for the IA and the server determines that the addresses in
                # the IA are not appropriate for the link to which the client's interface is attached according to the
                # server's explicit configuration information, the server MAY send a Reply message to the client
                # containing the client's IA, with the lifetimes for the addresses in the IA set to zero.  This Reply
                # constitutes an explicit notification to the client that the addresses in the IA are no longer valid.
                # In this situation, if the server does not send a Reply message it silently discards the Rebind
                # message.
                #
                # If the server finds that any of the addresses are no longer appropriate for the link to which the
                # client is attached, the server returns the address to the client with lifetimes of 0.
                if not self.authoritative:
                    raise CannotRespondError("Server is not authoritative and cannot reject rebind")

                addresses = ', '.join(map(str, option.get_addresses()))
                logger.warning("No handler answered rebind of {}: withdrawing addresses".format(addresses))

                reply_suboptions = []
                for suboption in option.get_options_of_type(IAAddressOption):
                    reply_suboptions.append(IAAddressOption(suboption.address, preferred_lifetime=0, valid_lifetime=0))

                bundle.response.options.append(ia_class(option.iaid, options=reply_suboptions))

            elif isinstance(bundle.request, DeclineMessage):
                # For each IA in the Decline message for which the server has no binding information, the server adds
                # an IA option using the IAID from the Release message and includes a Status Code option with the value
                # NoBinding in the IA option.  No other options are included in the IA option.
                bundle.response.options.append(ia_class(option.iaid, options=[
                    StatusCodeOption(STATUS_NO_BINDING, "No addresses assigned to you")
                ]))

            elif isinstance(bundle.request, ReleaseMessage):
                # For each IA in the Release message for which the server has no binding information, the server adds an
                # IA option using the IAID from the Release message, and includes a Status Code option with the value
                # NoBinding in the IA option.  No other options are included in the IA option.
                bundle.response.options.append(ia_class(option.iaid, options=[
                    StatusCodeOption(STATUS_NO_BINDING, "No addresses assigned to you")
                ]))
