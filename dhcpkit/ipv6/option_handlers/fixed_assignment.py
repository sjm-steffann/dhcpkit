"""
Option handler for IANAOptions and IAPDOptions where addresses and prefixes are pre-assigned based on DUID
"""
from abc import ABCMeta, abstractmethod
from ipaddress import IPv6Network, IPv6Address
import logging

from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.messages import SolicitMessage, RequestMessage, ConfirmMessage, RenewMessage, RebindMessage, \
    ReleaseMessage, DeclineMessage
from dhcpkit.ipv6.option_handlers.utils import Assignment, force_status
from dhcpkit.ipv6.options import IANAOption, IAAddressOption, StatusCodeOption, STATUS_NOTONLINK, ClientIdOption
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.utils import address_in_prefixes, prefix_overlaps_prefixes

logger = logging.getLogger(__name__)


class FixedAssignmentOptionHandler(OptionHandler, metaclass=ABCMeta):
    """
    An option handler that gives a fixed address and/or prefix to clients
    """

    def __init__(self, responsible_for_links: [IPv6Network],
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param responsible_for_links: The IPv6 links that this handler is responsible for
        :param address_preferred_lifetime: The preferred lifetime in seconds for addresses
        :param address_valid_lifetime: The valid lifetime in seconds for addresses
        :param prefix_preferred_lifetime: The preferred lifetime in seconds for prefixes
        :param prefix_valid_lifetime: The valid lifetime in seconds for prefixes
        """
        self.responsible_for_links = responsible_for_links
        self.address_preferred_lifetime = address_preferred_lifetime
        self.address_valid_lifetime = address_valid_lifetime
        self.prefix_preferred_lifetime = prefix_preferred_lifetime
        self.prefix_valid_lifetime = prefix_valid_lifetime

    @abstractmethod
    def get_assignment(self, bundle: TransactionBundle) -> Assignment:
        """
        Subclasses override this method to determine the assignment for the request in the bundle. This MUST return
        an Assignment object, even if no addresses are provided in it.

        :param bundle: The transaction bundle
        :return: The assignment
        """

    @staticmethod
    def find_iana_option_for_address(options: [IANAOption], address: IPv6Address) -> IANAOption or None:
        """
        Find an IANAOption that contains the given address

        :param options: The list of options to search
        :param address: The address to look for
        :return: The matching option, if any
        """
        for option in options:
            for suboption in option.get_options_of_type(IAAddressOption):
                if suboption.address == address:
                    return option

        # Nothing found: default to first
        return options[0] if options else None

    @staticmethod
    def find_iapd_option_for_prefix(options: [IAPDOption], prefix: IPv6Network) -> IAPDOption or None:
        """
        Find an IAPDOption that contains the given prefix

        :param options: The list of options to search
        :param prefix: The prefix to look for
        :return: The matching option, if any
        """
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

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unanswered_iana_options()
        unanswered_iapd_options = bundle.get_unanswered_iapd_options()

        # Try to assign the prefix first: it's not dependent on the link
        if assignment.prefix:
            found_option = self.find_iapd_option_for_prefix(unanswered_iapd_options, assignment.prefix)
            if found_option:
                # Answer to this option
                logger.info("Assigning {} to {!r}".format(assignment.prefix,
                                                          bundle.request.get_option_of_type(ClientIdOption).duid))
                response_option = IAPDOption(found_option.iaid, options=[
                    IAPrefixOption(prefix=assignment.prefix,
                                   preferred_lifetime=self.prefix_preferred_lifetime,
                                   valid_lifetime=self.prefix_valid_lifetime)
                ])
                bundle.response.options.append(response_option)
                bundle.mark_handled(found_option)

        # Make sure we are responsible for this link
        link_address = bundle.get_link_address()
        if not address_in_prefixes(link_address, self.responsible_for_links):
            logger.debug("Not assigning to link {}: "
                         "doesn't match {}".format(link_address, ', '.join(map(str, self.responsible_for_links))))
            return

        if assignment.address:
            found_option = self.find_iana_option_for_address(unanswered_iana_options, assignment.address)
            if found_option:
                # Answer to this option
                logger.info("Assigning {} to {!r}".format(assignment.address,
                                                          bundle.request.get_option_of_type(ClientIdOption).duid))
                response_option = IANAOption(found_option.iaid, options=[
                    IAAddressOption(address=assignment.address,
                                    preferred_lifetime=self.address_preferred_lifetime,
                                    valid_lifetime=self.address_valid_lifetime)
                ])
                bundle.response.options.append(response_option)
                bundle.mark_handled(found_option)

    def handle_confirm(self, bundle: TransactionBundle):
        """
        Handle a client requesting confirmation

        :param bundle: The request bundle
        """
        # Make sure we are responsible for this link
        link_address = bundle.get_link_address()
        if not address_in_prefixes(link_address, self.responsible_for_links):
            logger.debug("Not confirming to link {}: "
                         "doesn't match {}".format(link_address, ', '.join(map(str, self.responsible_for_links))))
            return

        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unanswered_iana_options()

        # See if there are any addresses on a link that I am responsible for
        for option in unanswered_iana_options:
            for suboption in option.get_options_of_type(IAAddressOption):
                if suboption.address == assignment.address:
                    # This is the address from the assignment: it's ok
                    bundle.mark_handled(option)
                    continue

                if address_in_prefixes(suboption.address, self.responsible_for_links):
                    # Oops, an address on a link that I am responsible for, but it's the wrong one...
                    force_status(bundle.response.options,
                                 StatusCodeOption(STATUS_NOTONLINK,
                                                  "{} is not assigned to you".format(suboption.address)))
                    bundle.mark_handled(option)
                    return

    def handle_renew_rebind(self, bundle: TransactionBundle):
        """
        Handle a client renewing/rebinding addresses

        :param bundle: The request bundle
        """
        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Client ID for logging
        client_id_option = bundle.request.get_option_of_type(ClientIdOption)

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unanswered_iana_options()
        unanswered_iapd_options = bundle.get_unanswered_iapd_options()

        for option in unanswered_iapd_options:
            if assignment.prefix and prefix_overlaps_prefixes(assignment.prefix, option.get_prefixes()):
                # Overlap with our assigned prefix: take responsibility
                response_suboptions = []
                for suboption in option.get_options_of_type(IAPrefixOption):
                    if suboption.prefix == assignment.prefix:
                        # This is the correct option, renew it
                        logger.info("Renewing {} for {!r}".format(assignment.prefix, client_id_option.duid))
                        response_suboptions.append(IAPrefixOption(prefix=assignment.prefix,
                                                                  preferred_lifetime=self.address_preferred_lifetime,
                                                                  valid_lifetime=self.address_valid_lifetime))
                    else:
                        # This isn't right
                        logger.info("Withdrawing {} from {!r}".format(suboption.prefix, client_id_option.duid))
                        response_suboptions.append(IAPrefixOption(prefix=suboption.prefix,
                                                                  preferred_lifetime=0, valid_lifetime=0))

                response_option = IAPDOption(option.iaid, options=response_suboptions)
                bundle.response.options.append(response_option)
                bundle.mark_handled(option)

        for option in unanswered_iana_options:
            if any([address_in_prefixes(address, self.responsible_for_links) for address in option.get_addresses()]):
                # Overlap with our addresses: take responsibility
                response_suboptions = []
                for suboption in option.get_options_of_type(IAAddressOption):
                    if suboption.address == assignment.address:
                        # This is the correct option, renew it
                        logger.info("Renewing {} for {!r}".format(assignment.address, client_id_option.duid))
                        response_suboptions.append(IAAddressOption(address=assignment.address,
                                                                   preferred_lifetime=self.address_preferred_lifetime,
                                                                   valid_lifetime=self.address_valid_lifetime))
                    else:
                        # This isn't right
                        logger.info("Withdrawing {} from {!r}".format(suboption.address, client_id_option.duid))
                        response_suboptions.append(IAAddressOption(address=suboption.address,
                                                                   preferred_lifetime=0, valid_lifetime=0))

                response_option = IANAOption(option.iaid, options=response_suboptions)
                bundle.response.options.append(response_option)
                bundle.mark_handled(option)

    def handle_release_decline(self, bundle: TransactionBundle):
        """
        Handle a client releasing or declining resources. Doesn't really need to do anything because assignments are
        fixed. Just mark the right options as handled.

        :param bundle: The request bundle
        """
        # Get the assignment
        assignment = self.get_assignment(bundle)

        # Collect unanswered options
        unanswered_iana_options = bundle.get_unanswered_iana_options()
        unanswered_iapd_options = bundle.get_unanswered_iapd_options()

        for option in unanswered_iapd_options:
            if assignment.prefix and prefix_overlaps_prefixes(assignment.prefix, option.get_prefixes()):
                # Overlap with our assigned prefix: take responsibility
                bundle.mark_handled(option)

        for option in unanswered_iana_options:
            if any([address_in_prefixes(address, self.responsible_for_links) for address in option.get_addresses()]):
                # Overlap with our addresses: take responsibility
                bundle.mark_handled(option)
