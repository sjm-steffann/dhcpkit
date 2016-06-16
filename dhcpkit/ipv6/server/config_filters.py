"""
Filters: the mechanism to decide which handlers apply to which incoming messages
"""
import logging

import abc

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6.server.filters import MarkedWithFilter

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

        filter_condition = self._section.getSectionName()
        return self.filter_class(filter_condition, sub_filters, sub_handlers)

    def validate_config_section(self):
        """
        Check that a filter condition has been provided.
        """
        filter_condition = self._section.getSectionName()
        if not filter_condition:
            section_type = self._section.getSectionType()
            raise ValueError("No filter condition provided in <{}> filter".format(section_type))


class MarkedWithFilterFactory(FilterFactory):
    """
    Create a MarkedWithFilter
    """
    filter_class = MarkedWithFilter
