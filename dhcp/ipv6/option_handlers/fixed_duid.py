"""
Option handler for IANAOptions and IAPDOptions where addresses and prefixes are pre-assigned based on DUID
"""
from ipaddress import IPv6Network
import logging

from dhcp.ipv6.option_handlers.fixed_assignment import FixedAssignmentOptionHandler
from dhcp.ipv6.option_handlers.utils import Assignment
from dhcp.ipv6.options import ClientIdOption
from dhcp.ipv6.message_handlers.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class FixedDUIDOptionHandler(FixedAssignmentOptionHandler):
    """
    An option handler that gives a fixed address and/or prefix to clients based on their DUID.
    """

    def __init__(self, mapping: dict, responsible_for_links: [IPv6Network],
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param mapping: The mapping from DUID to address and prefix
        :param responsible_for_links: The IPv6 links that this handler is responsible for
        :type mapping: dict[DUID, Assignment]
        """
        super().__init__(responsible_for_links,
                         address_preferred_lifetime, address_valid_lifetime,
                         prefix_preferred_lifetime, prefix_valid_lifetime)

        self.mapping = mapping

    # noinspection PyDocstring
    def get_assignment(self, bundle: TransactionBundle) -> Assignment:
        # Get the assignment
        client_id_option = bundle.request.get_option_of_type(ClientIdOption)
        return self.mapping.get(client_id_option.duid, Assignment(address=None, prefix=None))
