from ZConfig.datatypes import SuffixMultiplier, RangeCheckedConversion

from dhcpkit.ipv6 import INFINITY
from dhcpkit.ipv6.extensions.timing_limits.option_handlers import IANATimingLimitsOptionHandler, \
    IAPDTimingLimitsOptionHandler
from dhcpkit.ipv6.server.config import ConfigElementFactory

time_interval_converter = SuffixMultiplier({
    's': 1,
    'm': 60,
    'h': 60 * 60,
    'd': 60 * 60 * 24,
    'w': 60 * 60 * 24 * 7,
})

time_range_converter = RangeCheckedConversion(conversion=time_interval_converter, min=0, max=INFINITY)


def time_value(value: str) -> int:
    """
    Cast the string INFINITY to the infinity value, otherwise convert to an integer

    :param value: The string to parse
    :return: The integer value
    """
    if value.upper() == 'INFINITY':
        return INFINITY
    return time_range_converter(value)


factor_range_converter = RangeCheckedConversion(conversion=float, min=0.0, max=1.0)


def factor_value(value: str) -> float or None:
    """
    Cast the string NONE to the None value, otherwise convert to a float

    :param value: The string to parse
    :return: The float value or None
    """
    if value.upper() == 'NONE':
        return None
    return factor_range_converter(value)


class IANATimingLimitsOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> IANATimingLimitsOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the limits and factors
        min_t1 = self.section.min_ti
        max_t1 = self.section.max_t1
        factor_t1 = self.section.factor_t1

        min_t2 = self.section.min_t2
        max_t2 = self.section.max_t2
        factor_t2 = self.section.factor_t2

        return IANATimingLimitsOptionHandler(min_t1, max_t1, factor_t1, min_t2, max_t2, factor_t2)


class IAPDTimingLimitsOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> IAPDTimingLimitsOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the limits and factors
        min_t1 = self.section.min_ti
        max_t1 = self.section.max_t1
        factor_t1 = self.section.factor_t1

        min_t2 = self.section.min_t2
        max_t2 = self.section.max_t2
        factor_t2 = self.section.factor_t2

        return IAPDTimingLimitsOptionHandler(min_t1, max_t1, factor_t1, min_t2, max_t2, factor_t2)
