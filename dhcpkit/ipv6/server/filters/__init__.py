"""
Filters to apply to transaction bundles
"""
import logging
from typing import Iterable, List, Type

from cached_property import cached_property
from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.common.server.logging import DEBUG_HANDLING
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.utils import camelcase_to_dash

logger = logging.getLogger(__name__)


class Filter:
    """
    Base class for filters
    """

    def __init__(self, filter_condition: object,
                 sub_filters: Iterable['Filter'] = None, sub_handlers: Iterable[Handler] = None):
        """
        The main initialisation will be done in the master process. After initialisation the master process will create
        worker processes using the multiprocessing module.  Things that can't be pickled and transmitted to the worker
        processes (think database connections etc) have to be initialised separately. Each worker process will call
        worker_init() to do so. Filters that don't need per-worker initialisation can do everything here in __init__().

        :param filter_condition: The condition to filter on
        :param sub_filters: a list of filters configured inside this filter
        :param sub_handlers: a list of handlers configured inside this filter
        """
        self.filter_condition = filter_condition
        self.sub_filters = list(sub_filters or [])
        self.sub_handlers = list(sub_handlers or [])

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

    def match(self, bundle: TransactionBundle) -> bool:
        """
        Check whether the given message matches our filter condition.

        :param bundle: The transaction bundle
        :return: Whether our filter condition matches
        """

    def get_handlers(self, bundle: TransactionBundle) -> List[Handler]:
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


class FilterFactory(ConfigElementFactory):
    """
    Base class for filter factories
    """

    @property
    def filter_class(self) -> Type[Filter]:
        """
        Get the class of filter to create

        :return: The class of filter
        """
        raise NotImplementedError("filter_class not implemented for {}".format(self.__class__.__name__))

    def create(self):
        """
        Create the filter and feed it with the sub-filters and sub-handlers.

        :return: The filter
        """
        sub_filters = []
        for filter_factory in self.filter_factories:
            sub_filters.append(filter_factory())

        sub_handlers = []
        for handler_factory in self.handler_factories:
            sub_handlers.append(handler_factory())

        return self.filter_class(self.filter_condition, sub_filters, sub_handlers)

    @property
    def filter_condition(self):
        """
        Return the filter condition, the name of the section by default
        :return: The filter condition
        """
        return self.name
