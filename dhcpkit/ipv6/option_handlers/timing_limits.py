"""
Option handlers that limit the t1/t2 values in replies
"""

from abc import ABCMeta, abstractmethod

from dhcpkit.ipv6 import INFINITY
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.options import Option, IANAOption, IAAddressOption
from dhcpkit.ipv6.transaction_bundle import TransactionBundle


class TimingLimitsOptionHandler(OptionHandler, metaclass=ABCMeta):
    """
    A handler that limits the t1/t2 values in an option

    :type min_t1: int
    :type max_t1: int
    :type factor_t1: float or None
    :type min_t2: int
    :type max_t2: int
    :type factor_t2: float or None
    """

    def __init__(self,
                 min_t1=0, max_t1=INFINITY, factor_t1=0.5,
                 min_t2=0, max_t2=INFINITY, factor_t2=0.8):

        # These are the outer limits
        self.min_t1 = max(0, min_t1)
        self.max_t2 = min(max_t2, INFINITY)

        # If t2 has a max then t1's max must be at least as small
        self.max_t1 = min(max_t1, self.max_t2)

        # If t1 has a min then t2's min must be at least as large
        self.min_t2 = max(self.min_t1, min_t2)

        # Store the factors to auto-calculate t1/t2 based on the shortest preferred lifetime
        if factor_t1 is not None:
            self.factor_t1 = min(max(0, factor_t1), 1)
        else:
            self.factor_t1 = None

        if factor_t2 is not None:
            self.factor_t2 = min(max(0, factor_t2), 1)
        else:
            self.factor_t2 = None

        # Do some basic checks for impossible values
        if self.min_t1 > self.max_t2:
            raise ValueError("t1 must be able to be smaller than t2")

        if self.factor_t1 and self.factor_t2 and self.factor_t1 > self.factor_t2:
            raise ValueError("t1 factor must be smaller than t2 factor")

    @staticmethod
    def str_to_time(value: str) -> int:
        """
        Cast the string INFINITY to the infinity value, otherwise convert to an integer

        :param value: The string to parse
        :return: The integer value
        """
        if value.upper() == 'INFINITY':
            return INFINITY
        return int(value)

    @staticmethod
    def str_to_factor(value: str) -> float or None:
        """
        Cast the string NONE to the None value, otherwise convert to a float

        :param value: The string to parse
        :return: The float value or None
        """
        if value.upper() == 'NONE':
            return None
        return float(value)

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        min_t1 = cls.str_to_time(section.get('min-t1', '0'))
        max_t1 = cls.str_to_time(section.get('max-t1', 'INFINITY'))
        factor_t1 = cls.str_to_factor(section.get('factor-t1', '0.5'))

        min_t2 = cls.str_to_time(section.get('min-t2', '0'))
        max_t2 = cls.str_to_time(section.get('max-t2', 'INFINITY'))
        factor_t2 = cls.str_to_factor(section.get('factor-t2', '0.8'))

        return cls(min_t1, max_t1, factor_t1, min_t2, max_t2, factor_t2)

    @staticmethod
    @abstractmethod
    def filter_options(options: [Option]) -> [Option]:
        """
        Extract the options that we want to set the t1/t2 values of.

        :param options: The options in the response message
        :returns: The relevant options of the response message
        :rtype: list[IANAOption]
        """

    @staticmethod
    @abstractmethod
    def extract_preferred_lifetime(option: Option) -> int or None:
        """
        Extract the preferred lifetime from the given (sub)option. Returns None if this option doesn't contain a
        preferred lifetime.

        :param option: The option to extract the preferred lifetime from
        :returns: The preferred lifetime, if any
        """

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


class IANATimingLimitsOptionHandler(TimingLimitsOptionHandler):
    """
    A handler that limits the t1/t2 values in an IANAOption
    """

    @staticmethod
    def filter_options(options: [Option]) -> [IANAOption]:
        """
        Extract the IANAOptions that we want to set the t1/t2 values of.

        :param options: The options in the response message
        :returns: The relevant options of the response message
        :rtype: list[IANAOption]
        """
        return [option for option in options if isinstance(option, IANAOption)]

    @staticmethod
    def extract_preferred_lifetime(option: Option) -> int or None:
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


class IAPDTimingLimitsOptionHandler(TimingLimitsOptionHandler):
    """
    A handler that limits the t1/t2 values in an IANAOption
    """

    @staticmethod
    def filter_options(options: [Option]) -> [IAPDOption]:
        """
        Extract the IAPDOptions that we want to set the t1/t2 values of.

        :param options: The options in the response message
        :returns: The relevant options of the response message
        :rtype: list[IAPDOption]
        """
        return [option for option in options if isinstance(option, IAPDOption)]

    @staticmethod
    def extract_preferred_lifetime(option: Option) -> int or None:
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
