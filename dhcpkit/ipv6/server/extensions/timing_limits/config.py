"""
Configuration elements for the IANA/IAPD timing limits.
"""
from ZConfig.datatypes import SuffixMultiplier, RangeCheckedConversion
from typing import Optional

from dhcpkit.ipv6 import INFINITY
from dhcpkit.ipv6.server.extensions.timing_limits import IANATimingLimitsHandler, IAPDTimingLimitsHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory

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


def factor_value(value: str) -> Optional[float]:
    """
    Cast the string NONE to the None value, otherwise convert to a float

    :param value: The string to parse
    :return: The float value or None
    """
    if value.upper() == 'NONE':
        return None
    return factor_range_converter(value)


class IANATimingLimitsHandlerFactory(HandlerFactory):
    """
    Create the IANATimingLimitsHandler.
    """

    def create(self) -> IANATimingLimitsHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return IANATimingLimitsHandler(min_t1=self.min_t1, max_t1=self.max_t1, factor_t1=self.factor_t1,
                                       min_t2=self.min_t2, max_t2=self.max_t2, factor_t2=self.factor_t2)


class IAPDTimingLimitsHandlerFactory(HandlerFactory):
    """
    Create the IAPDTimingLimitsHandler.
    """

    def create(self) -> IAPDTimingLimitsHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return IAPDTimingLimitsHandler(min_t1=self.min_t1, max_t1=self.max_t1, factor_t1=self.factor_t1,
                                       min_t2=self.min_t2, max_t2=self.max_t2, factor_t2=self.factor_t2)
