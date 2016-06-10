"""
Filters: the mechanism to decide which actions apply to which incoming messages
"""
import logging

import abc
from pip.utils import cached_property

from dhcpkit.common.server.config_elements import ConfigSection
from dhcpkit.ipv6.server.config_action import Action
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class Filter(ConfigSection, metaclass=abc.ABCMeta):
    """
    Base class for filters
    """

    def validate_config_section(self):
        """
        Check that a filter condition has been provided.
        """
        if not self.filter_condition:
            section_type = self._section.getSectionType()
            raise ValueError("No filter condition provided in <{}> filter".format(section_type))

    @abc.abstractmethod
    def match(self, bundle: TransactionBundle) -> bool:
        """
        Check whether the given message matches our filter condition.

        :param bundle: The transaction bundle
        :return: Whether our filter condition matches
        """

    @cached_property
    def filter_condition(self):
        """
        Shortcut for the condition string (section name)

        :return: The condition string
        """
        return self._section.getSectionName()

    @cached_property
    def filter_description(self) -> str:
        """
        A short description of this filter for log messages.

        :return: The description
        """

        condition = self._section.getSectionName()
        section_type = self._section.getSectionType()

        return "{}={}".format(section_type, condition)

    def get_actions(self, bundle: TransactionBundle) -> [Action]:
        """
        Get all actions that are going to be applied to the request in the bundle.

        :param bundle: The transaction bundle
        :return: The list of actions to apply
        """
        if not self.match(bundle):
            logger.debug("Filter {} did not match {}".format(self.filter_description, bundle))
            return []

        logger.debug("Filter {} matched {}".format(self.filter_description, bundle))

        # Collect actions
        actions = []

        # Apply all sub-filters and collect their actions. The idea behind this is that actions on more-specific
        # filters take precedence over actions on the outer filters.
        for sub_filter in self._section.filters:
            actions += sub_filter.get_actions(bundle)

        # Now add our own actions
        actions += self._section.actions

        return actions


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
