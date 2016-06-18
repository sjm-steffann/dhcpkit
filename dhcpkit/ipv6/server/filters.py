"""
Filters to apply to transaction bundles
"""
import abc
import logging

from cached_property import cached_property

from dhcpkit.common.server.logging import DEBUG_HANDLING
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.utils import camelcase_to_dash

logger = logging.getLogger(__name__)


class Filter(metaclass=abc.ABCMeta):
    """
    Base class for filters
    """

    def __init__(self, filter_condition: object, sub_filters: [object], sub_handlers: [Handler]):
        """
        The main initialisation will be done in the master process. After initialisation the master process will create
        worker processes using the multiprocessing module.  Things that can't be pickled and transmitted to the worker
        processes (think database connections etc) have to be initialised separately. Each worker process will call
        worker_init() to do so. Filters that don't need per-worker initialisation can do everything here in __init__().

        :param filter_condition: The condition to filter on
        :param sub_filters: a list of filters configured inside this filter
        :type sub_filters: [Filter]
        :param sub_handlers: a list of handlers configured inside this filter
        """
        self.filter_condition = filter_condition
        self.sub_filters = sub_filters
        self.sub_handlers = sub_handlers

    def worker_init(self):
        """
        Separate initialisation that will be called in each worker process that is created. Things that can't be forked
        (think database connections etc) have to be initialised here.
        """

        # Cascade to sub-filters and sub-handlers
        for sub_filter in self.sub_filters:
            sub_filter.worker_init()

        for sub_handler in self.sub_handlers:
            sub_handler.worker_init()

    @cached_property
    def filter_description(self) -> str:
        """
        A short description of this filter for log messages.

        :return: The description
        """
        simple_name = camelcase_to_dash(self.__class__.__name__)
        if simple_name.endswith('-filter'):
            simple_name = simple_name[:-7]

        return "{}={}".format(simple_name, self.filter_condition)

    @abc.abstractmethod
    def match(self, bundle: TransactionBundle) -> bool:
        """
        Check whether the given message matches our filter condition.

        :param bundle: The transaction bundle
        :return: Whether our filter condition matches
        """

    def get_handlers(self, bundle: TransactionBundle) -> [Handler]:
        """
        Get all handlers that are going to be applied to the request in the bundle.

        :param bundle: The transaction bundle
        :return: The list of handlers to apply
        """
        if not self.match(bundle):
            return []

        logger.log(DEBUG_HANDLING, "Filter {} matched".format(self.filter_description, bundle))

        # Collect handlers
        handlers = []

        # Apply all sub-filters and collect their handlers. The idea behind this is that handlers on more-specific
        # filters take precedence over handlers on the outer filters.
        for sub_filter in self.sub_filters:
            handlers += sub_filter.get_handlers(bundle)

        # Now add our own handlers
        handlers += self.sub_handlers

        return handlers


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
