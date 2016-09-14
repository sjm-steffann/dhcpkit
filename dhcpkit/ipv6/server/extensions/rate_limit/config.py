"""
Config processing for a handler to rate limit clients
"""
from types import FunctionType

from dhcpkit.ipv6.server.extensions.rate_limit import RateLimitHandler
from dhcpkit.ipv6.server.extensions.rate_limit.key_functions import key_function_map
from dhcpkit.ipv6.server.handlers import HandlerFactory


def key_function(key_name: str) -> FunctionType:
    """
    Map from name to key extraction function.

    :param key_name: The name of the function
    :return: The specified function
    """
    try:
        return key_function_map[key_name.lower()]
    except KeyError:
        raise ValueError("Unknown key function '{}'".format(key_name))


def rate(configured_rate: str) -> int:
    """
    Convert the config rate to an integer.

    :param configured_rate: The number of messages as a string
    :return: The number of messages as an integer
    """
    my_rate = int(configured_rate)
    if my_rate < 2:
        raise ValueError("The configured rate must be at least 2")
    return my_rate


def duration(config_duration: str) -> int:
    """
    Convert the config duration to an integer.

    :param config_duration: The duration as a string
    :return: The duration as an integer
    """
    my_duration = int(config_duration)
    if my_duration < 1:
        raise ValueError("A slot must be at least 1 second long")
    return my_duration


class RateLimitHandlerFactory(HandlerFactory):
    """
    Config processing for a handler to rate limit clients
    """

    def create(self) -> RateLimitHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return RateLimitHandler(key=self.section.key,
                                rate=self.section.rate, per=self.section.per, burst=self.section.burst)
