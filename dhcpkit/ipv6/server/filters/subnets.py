"""
Filter on subnet that the link address is in
"""
from cached_property import cached_property

from dhcpkit.ipv6.server.filters import Filter
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.utils import camelcase_to_dash


class SubnetFilter(Filter):
    """
    Filter on subnet that the link address is in
    """

    @cached_property
    def filter_description(self) -> str:
        """
        A short description of this filter for log messages.

        :return: The description
        """
        simple_name = camelcase_to_dash(self.__class__.__name__)
        if simple_name.endswith('-filter'):
            simple_name = simple_name[:-7]

        return "{} in {}".format(simple_name, [str(prefix) for prefix in self.filter_condition])

    def match(self, bundle: TransactionBundle) -> bool:
        """
        Check if the link-address is in the subnet

        :param bundle: The transaction bundle
        :return: Whether the link-address matches
        """
        # Check if the link-address is in any of the prefixes
        return any([bundle.link_address in prefix for prefix in self.filter_condition])
