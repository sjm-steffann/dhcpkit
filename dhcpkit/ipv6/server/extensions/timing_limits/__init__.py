"""
Handlers that limit the t1/t2 values in replies
"""

from typing import Iterable, List, Optional, Union

from dhcpkit.ipv6 import INFINITY
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.options import IAAddressOption, IANAOption, Option
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class TimingLimitsHandler(Handler):
    """
    A handler that limits the t1/t2 values in an option
    """

    def __init__(self,
                 min_t1: int = 0, max_t1: int = INFINITY, factor_t1: Optional[float] = 0.5,
                 min_t2: int = 0, max_t2: int = INFINITY, factor_t2: Optional[float] = 0.8):
        super().__init__()

        # These are the outer limits
        self.min_t1 = max(0, min_t1)
        self.max_t2 = min(max_t2, INFINITY)

        # If t2 has a max then t1's max must be at least as small
        self.max_t1 = min(max_t1, self.max_t2)

        # If t1 has a min then t2's min must be at least as large
        self.min_t2 = max(self.min_t1, min_t2)

        # Store the factors to auto-calculate t1/t2 based on the shortest preferred lifetime
        if factor_t1 is not None:
            self.factor_t1 = min(max(0.0, factor_t1), 1)
        else:
            self.factor_t1 = None

        if factor_t2 is not None:
            self.factor_t2 = min(max(0.0, factor_t2), 1)
        else:
            self.factor_t2 = None

        # Do some basic checks for impossible values
        if self.min_t1 > self.max_t2:
            raise ValueError("min_t1 must be smaller than max_t2")

        if self.factor_t1 and self.factor_t2 and self.factor_t1 > self.factor_t2:
            raise ValueError("factor_t1 must be smaller than factor_t2")

    def __str__(self):
        return "{} with t1={},{},{} t2={},{},{}".format(self.__class__.__name__,
                                                        self.min_t1, self.max_t1, self.factor_t1,
                                                        self.min_t2, self.max_t2, self.factor_t2)

    @staticmethod
    def filter_options(options: Iterable[Option]) -> List[Union[IANAOption, IAPDOption]]:
        """
        Extract the options that we want to set the t1/t2 values of.

        :param options: The options in the response message
        :returns: The relevant options of the response message
        :rtype: list[IANAOption]
        """
        return []

    @staticmethod
    def extract_preferred_lifetime(option: Option) -> Optional[int]:
        """
        Extract the preferred lifetime from the given (sub)option. Returns None if this option doesn't contain a
        preferred lifetime.

        :param option: The option to extract the preferred lifetime from
        :returns: The preferred lifetime, if any
        """
        return None

    def handle(self, bundle: TransactionBundle):
        """
        Make sure the T1/T2 values are within the set limits.

        :param bundle: The transaction bundle
        """
        # Make a list of IAIDs in the response
        for option in self.filter_options(bundle.response.options):
            # Find the shortest preferred lifetime
            shortest_preferred = INFINITY + 1
            for suboption in option.options:
                preferred_lifetime = self.extract_preferred_lifetime(suboption)
                if preferred_lifetime is not None:
                    shortest_preferred = min(shortest_preferred, preferred_lifetime)

            # Don't mess with the timers if there are no addresses
            if shortest_preferred > INFINITY:
                continue

            # Calculate t1
            if option.t1 == 0 and self.factor_t1 is not None:
                if shortest_preferred == INFINITY:
                    option.t1 = INFINITY
                else:
                    option.t1 = int(shortest_preferred * self.factor_t1)

            # Calculate t2
            if option.t2 == 0 and self.factor_t2 is not None:
                if shortest_preferred == INFINITY:
                    option.t2 = INFINITY
                else:
                    option.t2 = int(shortest_preferred * self.factor_t2)

            # Now limit to the min/max bounds, making sure that t1 is not larger than t2
            # This will ignore the given boundaries if they conflict with shortest_preferred lifetime
            option.t2 = min(max(self.min_t2, option.t2), self.max_t2, shortest_preferred)
            option.t1 = min(max(self.min_t1, option.t1), self.max_t1, option.t2)


class IANATimingLimitsHandler(TimingLimitsHandler):
    """
    A handler that limits the t1/t2 values in an IANAOption
    """

    @staticmethod
    def filter_options(options: Iterable[Option]) -> List[IANAOption]:
        """
        Extract the IANAOptions that we want to set the t1/t2 values of.

        :param options: The options in the response message
        :returns: The relevant options of the response message
        :rtype: list[IANAOption]
        """
        # noinspection PyTypeChecker
        return [option for option in options if isinstance(option, IANAOption)]

    @staticmethod
    def extract_preferred_lifetime(option: Option) -> Optional[int]:
        """
        Extract the preferred lifetime from the given (sub)option. Returns None if this option doesn't contain a
        preferred lifetime.

        :param option: The option to extract the preferred lifetime from
        :returns: The preferred lifetime, if any
        """
        if isinstance(option, IAAddressOption):
            return option.preferred_lifetime
        else:
            return None


class IAPDTimingLimitsHandler(TimingLimitsHandler):
    """
    A handler that limits the t1/t2 values in an IANAOption
    """

    @staticmethod
    def filter_options(options: Iterable[Option]) -> List[IAPDOption]:
        """
        Extract the IAPDOptions that we want to set the t1/t2 values of.

        :param options: The options in the response message
        :returns: The relevant options of the response message
        :rtype: list[IAPDOption]
        """
        # noinspection PyTypeChecker
        return [option for option in options if isinstance(option, IAPDOption)]

    @staticmethod
    def extract_preferred_lifetime(option: Option) -> Optional[int]:
        """
        Extract the preferred lifetime from the given (sub)option. Returns None if this option doesn't contain a
        preferred lifetime.

        :param option: The option to extract the preferred lifetime from
        :returns: The preferred lifetime, if any
        """
        if isinstance(option, IAPrefixOption):
            return option.preferred_lifetime
        else:
            return None
