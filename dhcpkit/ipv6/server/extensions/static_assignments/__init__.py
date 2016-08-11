"""
An extension to get static assignments from CSV files, Shelves or an SQLite database
"""
import logging
from collections import namedtuple
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.common.server.logging import DEBUG_HANDLING
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.messages import ConfirmMessage, DeclineMessage, RebindMessage, ReleaseMessage, RenewMessage, \
    RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import IAAddressOption, IANAOption
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.utils import prefix_overlaps_prefixes
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

Assignment = namedtuple('Assignment', ['address', 'prefix'])


class StaticAssignmentHandler(Handler):
    """
    An option handler that gives a static address and/or prefix to clients
    """

    def __init__(self,
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param address_preferred_lifetime: The preferred lifetime in seconds for addresses
        :param address_valid_lifetime: The valid lifetime in seconds for addresses
        :param prefix_preferred_lifetime: The preferred lifetime in seconds for prefixes
        :param prefix_valid_lifetime: The valid lifetime in seconds for prefixes
        """
        super().__init__()
        self.address_preferred_lifetime = address_preferred_lifetime
        self.address_valid_lifetime = address_valid_lifetime
        self.prefix_preferred_lifetime = prefix_preferred_lifetime
        self.prefix_valid_lifetime = prefix_valid_lifetime

    def get_assignment(self, bundle: TransactionBundle) -> Assignment:
        """
        Subclasses override this method to determine the assignment for the request in the bundle. This MUST return
        an Assignment object, even if no addresses are provided in it.

        :param bundle: The transaction bundle
        :return: The assignment
        """

    @staticmethod
    def find_iana_option_for_address(options: Iterable[IANAOption], address: IPv6Address) -> Optional[IANAOption]:
        """
        Find an IANAOption that contains the given address

        :param options: The list of options to search
        :param address: The address to look for
        :return: The matching option, if any
        """
        options = list(options)

        for option in options:
            for suboption in option.get_options_of_type(IAAddressOption):
                if suboption.address == address:
                    return option

        # Nothing found: default to first
        return options[0] if options else None

    @staticmethod
    def find_iapd_option_for_prefix(options: Iterable[IAPDOption], prefix: IPv6Network) -> Optional[IAPDOption]:
        """
        Find an IAPDOption that contains the given prefix

        :param options: The list of options to search
        :param prefix: The prefix to look for
        :return: The matching option, if any
        """
        options = list(options)

        for option in options:
            for suboption in option.get_options_of_type(IAPrefixOption):
                if suboption.prefix == prefix:
                    return option

        # Nothing found: default to first
        return options[0] if options else None

    def handle(self, bundle: TransactionBundle):
        """
        The handling is so complex that we just delegate the implementation to separate methods.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, (SolicitMessage, RequestMessage)):
            self.handle_request(bundle)
        elif isinstance(bundle.request, ConfirmMessage):
            self.handle_confirm(bundle)
        elif isinstance(bundle.request, (RenewMessage, RebindMessage)):
            self.handle_renew_rebind(bundle)
        elif isinstance(bundle.request, (ReleaseMessage, DeclineMessage)):
            self.handle_release_decline(bundle)

    def handle_request(self, bundle: TransactionBundle):
        """
        Handle a client requesting addresses (also handles SolicitMessage)

        :param bundle: The request bundle
        """
        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Try to assign the prefix first: it's not dependent on the link
        if assignment.prefix:
            unanswered_iapd_options = bundle.get_unhandled_options(IAPDOption)
            found_option = self.find_iapd_option_for_prefix(unanswered_iapd_options, assignment.prefix)
            if found_option:
                # Answer to this option
                logger.log(DEBUG_HANDLING, "Assigning prefix {}".format(assignment.prefix))
                response_option = IAPDOption(found_option.iaid, options=[
                    IAPrefixOption(prefix=assignment.prefix,
                                   preferred_lifetime=self.prefix_preferred_lifetime,
                                   valid_lifetime=self.prefix_valid_lifetime)
                ])
                bundle.response.options.append(response_option)
                bundle.mark_handled(found_option)
            else:
                logger.log(DEBUG_HANDLING,
                           "Prefix {} reserved, but client did not ask for it".format(assignment.prefix))

        if assignment.address:
            unanswered_iana_options = bundle.get_unhandled_options(IANAOption)
            found_option = self.find_iana_option_for_address(unanswered_iana_options, assignment.address)
            if found_option:
                # Answer to this option
                logger.log(DEBUG_HANDLING, "Assigning address {}".format(assignment.address))
                response_option = IANAOption(found_option.iaid, options=[
                    IAAddressOption(address=assignment.address,
                                    preferred_lifetime=self.address_preferred_lifetime,
                                    valid_lifetime=self.address_valid_lifetime)
                ])
                bundle.response.options.append(response_option)
                bundle.mark_handled(found_option)
            else:
                logger.log(DEBUG_HANDLING,
                           "Address {} reserved, but client did not ask for it".format(assignment.address))

    def handle_confirm(self, bundle: TransactionBundle):
        """
        Handle a client requesting confirmation

        :param bundle: The request bundle
        """
        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unhandled_options(IANAOption)

        # See if there are any addresses on a link that I am responsible for
        for option in unanswered_iana_options:
            for suboption in option.get_options_of_type(IAAddressOption):
                if suboption.address == assignment.address:
                    # This is the address from the assignment: it's ok
                    bundle.mark_handled(option)
                    continue

    def handle_renew_rebind(self, bundle: TransactionBundle):
        """
        Handle a client renewing/rebinding addresses

        :param bundle: The request bundle
        """
        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unhandled_options(IANAOption)
        unanswered_iapd_options = bundle.get_unhandled_options(IAPDOption)

        for option in unanswered_iapd_options:
            if assignment.prefix and prefix_overlaps_prefixes(assignment.prefix, option.get_prefixes()):
                # Overlap with our assigned prefix: take responsibility
                response_suboptions = []
                for suboption in option.get_options_of_type(IAPrefixOption):
                    if suboption.prefix == assignment.prefix:
                        # This is the correct option, renew it
                        logger.log(DEBUG_HANDLING, "Renewing prefix {}".format(assignment.prefix))
                        response_suboptions.append(IAPrefixOption(prefix=assignment.prefix,
                                                                  preferred_lifetime=self.prefix_preferred_lifetime,
                                                                  valid_lifetime=self.prefix_valid_lifetime))
                    else:
                        # This isn't right
                        logger.log(DEBUG_HANDLING, "Withdrawing prefix {}".format(suboption.prefix))
                        response_suboptions.append(IAPrefixOption(prefix=suboption.prefix,
                                                                  preferred_lifetime=0, valid_lifetime=0))

                response_option = IAPDOption(option.iaid, options=response_suboptions)
                bundle.response.options.append(response_option)
                bundle.mark_handled(option)

        for option in unanswered_iana_options:
            response_suboptions = []
            for suboption in option.get_options_of_type(IAAddressOption):
                if suboption.address == assignment.address:
                    # This is the correct option, renew it
                    logger.log(DEBUG_HANDLING, "Renewing address {}".format(assignment.address))
                    response_suboptions.append(IAAddressOption(address=assignment.address,
                                                               preferred_lifetime=self.address_preferred_lifetime,
                                                               valid_lifetime=self.address_valid_lifetime))
                else:
                    # This isn't right
                    logger.log(DEBUG_HANDLING, "Withdrawing address {}".format(suboption.address))
                    response_suboptions.append(IAAddressOption(address=suboption.address,
                                                               preferred_lifetime=0, valid_lifetime=0))

            response_option = IANAOption(option.iaid, options=response_suboptions)
            bundle.response.options.append(response_option)
            bundle.mark_handled(option)

    def handle_release_decline(self, bundle: TransactionBundle):
        """
        Handle a client releasing or declining resources. Doesn't really need to do anything because assignments are
        static. Just mark the right options as handled.

        :param bundle: The request bundle
        """
        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unhandled_options(IANAOption)
        unanswered_iapd_options = bundle.get_unhandled_options(IAPDOption)

        for option in unanswered_iapd_options:
            if assignment.prefix and prefix_overlaps_prefixes(assignment.prefix, option.get_prefixes()):
                # Overlap with our assigned prefix: take responsibility
                bundle.mark_handled(option)

        for option in unanswered_iana_options:
            if assignment.address in option.get_addresses():
                bundle.mark_handled(option)
