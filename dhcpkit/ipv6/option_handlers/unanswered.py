"""
Option handlers that cleans up unanswered requests
"""
import logging

from dhcpkit.ipv6.exceptions import CannotRespondError
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, STATUS_NOPREFIXAVAIL, IAPrefixOption
from dhcpkit.ipv6.messages import SolicitMessage, RequestMessage, RenewMessage, RebindMessage, ReleaseMessage, \
    DeclineMessage, ConfirmMessage
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.option_handlers.utils import force_status
from dhcpkit.ipv6.options import StatusCodeOption, STATUS_NOADDRSAVAIL, STATUS_NOBINDING, \
    STATUS_NOTONLINK, IAAddressOption
from dhcpkit.ipv6.server.config_parser import str_to_bool
from dhcpkit.ipv6.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class UnansweredIAOptionHandler(OptionHandler):
    """
    A handler that answers to all unanswered IANAOptions and IATAOptions

    :param authoritative: Whether this handler is authorised to tell clients to stop using prefixes
    """

    def __init__(self, authoritative: bool = True):
        self.authoritative = authoritative

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        authoritative = section.get('authoritative', False)
        return cls(str_to_bool(authoritative))

    def handle(self, bundle: TransactionBundle):
        """
        Make sure that every :class:`.IANAOption` and :class:`.IATAOption` is answered.

        :param bundle: The transaction bundle
        """
        for option in bundle.get_unanswered_ia_options():
            ia_class = type(option)

            if isinstance(bundle.request, (SolicitMessage, RequestMessage)):
                # If the server will not assign any addresses to any IAs in a subsequent Request from the client, the
                # server MUST send an Advertise message to the client that includes only a Status Code option with code
                # NoAddrsAvail and a status message for the user
                #
                # We do the same for unanswered requests
                bundle.response.options.append(ia_class(option.iaid, options=[
                    StatusCodeOption(STATUS_NOADDRSAVAIL, "No addresses available")
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
                    raise CannotRespondError

                addresses = ', '.join([str(suboption.address)
                                       for suboption in option.get_options_of_type(IAAddressOption)])
                logger.warning("No handler confirmed {} for {}: "
                               "sending NotOnLink status".format(addresses, bundle.get_link_address()))

                force_status(bundle.response.options,
                             StatusCodeOption(STATUS_NOTONLINK, "Those addresses are not appropriate on this link"))

            elif isinstance(bundle.request, RenewMessage):
                # If the server cannot find a client entry for the IA the server returns the IA containing no addresses
                # with a Status Code option set to NoBinding in the Reply message.
                #
                # If the server finds that any of the addresses are not appropriate for the link to which the client is
                # attached, the server returns the address to the client with lifetimes of 0.
                addresses = ', '.join([str(suboption.address)
                                       for suboption in option.get_options_of_type(IAAddressOption)])

                if self.authoritative:
                    logger.warning("No handler renewed {} for {}: "
                                   "withdrawing addresses".format(addresses, bundle.get_link_address()))

                    reply_suboptions = []
                    for suboption in option.get_options_of_type(IAAddressOption):
                        reply_suboptions.append(IAAddressOption(suboption.address,
                                                                preferred_lifetime=0, valid_lifetime=0))

                    bundle.response.options.append(ia_class(option.iaid, options=reply_suboptions))
                else:
                    logger.warning("No handler renewed {} for {}: "
                                   "sending NoBinding status".format(addresses, bundle.get_link_address()))

                    bundle.response.options.append(ia_class(option.iaid, options=[
                        StatusCodeOption(STATUS_NOBINDING, "No addresses assigned to you")
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
                    raise CannotRespondError

                addresses = ', '.join([str(suboption.address)
                                       for suboption in option.get_options_of_type(IAAddressOption)])
                logger.warning("No handler answered rebind of {} for {}: "
                               "withdrawing addresses".format(addresses, bundle.get_link_address()))

                reply_suboptions = []
                for suboption in option.get_options_of_type(IAAddressOption):
                    reply_suboptions.append(IAAddressOption(suboption.address, preferred_lifetime=0, valid_lifetime=0))

                bundle.response.options.append(ia_class(option.iaid, options=reply_suboptions))

            elif isinstance(bundle.request, DeclineMessage):
                # For each IA in the Decline message for which the server has no binding information, the server adds
                # an IA option using the IAID from the Release message and includes a Status Code option with the value
                # NoBinding in the IA option.  No other options are included in the IA option.
                bundle.response.options.append(ia_class(option.iaid, options=[
                    StatusCodeOption(STATUS_NOBINDING, "No addresses assigned to you")
                ]))

            elif isinstance(bundle.request, ReleaseMessage):
                # For each IA in the Release message for which the server has no binding information, the server adds an
                # IA option using the IAID from the Release message, and includes a Status Code option with the value
                # NoBinding in the IA option.  No other options are included in the IA option.
                bundle.response.options.append(ia_class(option.iaid, options=[
                    StatusCodeOption(STATUS_NOBINDING, "No addresses assigned to you")
                ]))


class UnansweredIAPDOptionHandler(OptionHandler):
    """
    A handler that answers to all unanswered IAPDOptions

    :param authoritative: Whether this handler is authorised to tell clients to stop using prefixes
    """

    def __init__(self, authoritative: bool = True):
        self.authoritative = authoritative

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        authoritative = section.get('authoritative', False)
        return cls(str_to_bool(authoritative))

    def handle(self, bundle: TransactionBundle):
        """
        Make sure that every :class:`.IAPDOption` is answered.

        :param bundle: The transaction bundle
        """
        for option in bundle.get_unanswered_iapd_options():
            if isinstance(bundle.request, (SolicitMessage, RequestMessage)):
                # If the delegating router will not assign any prefixes to any IA_PDs in a subsequent Request from the
                # requesting router, the delegating router MUST send an Advertise message to the requesting router that
                # includes the IA_PD with no prefixes in the IA_PD and a Status Code option in the IA_PD containing
                # status code NoPrefixAvail and a status message for the user
                #
                # We do the same for unanswered requests
                bundle.response.options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NOPREFIXAVAIL, "No prefixes available")
                ]))

            elif isinstance(bundle.request, RenewMessage):
                # Renew message: If the delegating router cannot find a binding for the requesting router's IA_PD the
                # delegating router returns the IA_PD containing no prefixes with a Status Code option set to
                # NoBinding in the Reply message.

                prefixes = ', '.join([str(suboption.prefix)
                                      for suboption in option.get_options_of_type(IAPrefixOption)])
                logger.warning("No handler renewed {} for {}: "
                               "sending NoBinding status".format(prefixes, bundle.get_link_address()))

                bundle.response.options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NOBINDING, "No prefixes assigned to you")
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
                    raise CannotRespondError

                prefixes = ', '.join([str(suboption.prefix)
                                      for suboption in option.get_options_of_type(IAPrefixOption)])
                logger.warning("No handler answered rebind of {} for {}: "
                               "withdrawing prefixes".format(prefixes, bundle.get_link_address()))

                reply_suboptions = []
                for suboption in option.get_options_of_type(IAPrefixOption):
                    reply_suboptions.append(IAPrefixOption(suboption.prefix, preferred_lifetime=0, valid_lifetime=0))

                bundle.response.options.append(IAPDOption(option.iaid, options=reply_suboptions))

            elif isinstance(bundle.request, ReleaseMessage):
                # For each IA in the Release message for which the server has no binding information, the server adds an
                # IA option using the IAID from the Release message, and includes a Status Code option with the value
                # NoBinding in the IA option.  No other options are included in the IA option.
                bundle.response.options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NOBINDING, "No prefixes assigned to you")
                ]))
