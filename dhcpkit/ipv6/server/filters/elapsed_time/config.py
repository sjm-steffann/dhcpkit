"""
Filter on elapsed time indicated by the client
"""
import operator
from collections import namedtuple

from cached_property import cached_property
from dhcpkit.ipv6.options import ElapsedTimeOption
from dhcpkit.ipv6.server.filters import Filter, FilterFactory
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.utils import camelcase_to_dash
from typing import List

TimeLimit = namedtuple('TimeLimit', ['operator', 'limit'])


class ElapsedTimeFilter(Filter):
    """
    Filter on marks that have been placed on the incoming message
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

        return simple_name + ' ' + ' and '.join(["{operator} {value}".format(operator=condition.operator.__name__,
                                                                             value=condition.limit)
                                                 for condition in self.filter_condition])

    def match(self, bundle: TransactionBundle) -> bool:
        """
        Check if the elapsed time is within the configured limits

        :param bundle: The transaction bundle
        :return: Whether the elapsed time is within the limits
        """
        elapsed_time_option = bundle.request.get_option_of_type(ElapsedTimeOption)
        if not elapsed_time_option:
            # If there is no elapsed time then ignore the request
            return False

        for time_limit in self.filter_condition:
            if not time_limit.operator(elapsed_time_option.elapsed_time, time_limit.limit):
                # It failed the check
                return False

        # Apparently they all match
        return True


class ElapsedTimeFilterFactory(FilterFactory):
    """
    Create a MarkedWithFilter
    """
    filter_class = ElapsedTimeFilter

    def validate_config_section(self):
        """
        Check that at least one filter condition is provided, and that if multiple conditions are provided they are
        compatible with each other.
        """
        if not self.less_than and not self.more_than:
            raise ValueError("At least one time limit ('more-than' or 'less-than') must be configured")

        if self.less_than and self.more_than and self.less_than <= self.more_than:
            raise ValueError("The timing limits of 'more-than' and 'less-than' conflict")

    @property
    def filter_condition(self) -> List[TimeLimit]:
        """
        The filter condition is based on the configured time limits.

        :return: A list of time limits
        """
        limits = []
        if self.more_than:
            # ElapsedTime contains the time in 1/100 of a second, but we just use second precision, so multiply
            limits.append(TimeLimit(operator=operator.gt, limit=self.more_than * 100))
        if self.less_than:
            # ElapsedTime contains the time in 1/100 of a second, but we just use second precision, so multiply
            limits.append(TimeLimit(operator=operator.lt, limit=self.less_than * 100))

        return limits
