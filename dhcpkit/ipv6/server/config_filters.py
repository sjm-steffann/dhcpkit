"""
Filters: the mechanism to decide which handlers apply to which incoming messages
"""
import abc
import logging
from ipaddress import IPv6Network

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6.server.filters import MarkedWithFilter, SubnetFilter

logger = logging.getLogger(__name__)


class FilterFactory(ConfigElementFactory, metaclass=abc.ABCMeta):
    """
    Base class for filter factories
    """

    @property
    @abc.abstractmethod
    def filter_class(self) -> type:
        """
        Get the class of filter to create

        :return: The class of filter
        """

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


class MarkedWithFilterFactory(FilterFactory):
    """
    Create a MarkedWithFilter
    """
    name_datatype = staticmethod(str)
    filter_class = MarkedWithFilter


class SubnetFilterFactory(FilterFactory):
    """
    Create a subnet filter
    """
    name_datatype = staticmethod(IPv6Network)
    filter_class = SubnetFilter

    @property
    def filter_condition(self):
        """
        Return the filter condition, the list of prefixes
        :return: The filter condition
        """
        return [self.name]


class SubnetGroupFilterFactory(FilterFactory):
    """
    Create a subnet filter
    """
    filter_class = SubnetFilter

    @property
    def filter_condition(self):
        """
        Return the filter condition, the list of prefixes
        :return: The filter condition
        """
        return self.prefixes
