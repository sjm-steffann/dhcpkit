"""
Configuration elements for the SOL_MAX_RT option handlers
"""
from dhcpkit.ipv6.server.extensions.sol_max_rt import InfMaxRTOptionHandler, SolMaxRTOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


def max_rt(value: str) -> int:
    """
    Convert the name of the section to the number of seconds, and validate the range

    :param value: Config section name
    :return: Number of seconds
    """
    seconds = int(value)

    if not (60 <= seconds <= 86400):
        raise ValueError("MAX_RT must be between 60 and 86400 seconds")

    return seconds


class SolMaxRTOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for the SolMaxRTOption.
    """

    def create(self) -> SolMaxRTOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return SolMaxRTOptionHandler(self.limit, always_send=self.always_send)


class InfMaxRTOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for the InfMaxRTOption.
    """

    def create(self) -> InfMaxRTOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return InfMaxRTOptionHandler(self.limit, always_send=self.always_send)
