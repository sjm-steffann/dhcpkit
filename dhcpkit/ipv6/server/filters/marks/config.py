"""
Filter on marks that have been placed on the incoming message
"""
from dhcpkit.ipv6.server.filters import Filter, FilterFactory
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class MarkedWithFilter(Filter):
    """
    Filter on marks that have been placed on the incoming message
    """

    def match(self, bundle: TransactionBundle) -> bool:
        """
        Check if the configured mark is in the set

        :param bundle: The transaction bundle
        :return: Whether the configured mark is present
        """
        return self.filter_condition in bundle.marks


class MarkedWithFilterFactory(FilterFactory):
    """
    Create a MarkedWithFilter
    """
    name_datatype = staticmethod(lambda value: str(value))
    filter_class = MarkedWithFilter
