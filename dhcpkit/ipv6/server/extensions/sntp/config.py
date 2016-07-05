"""
Configuration elements for the dns option handlers
"""
from dhcpkit.ipv6.server.extensions.sntp import SNTPServersOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class SNTPServersOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for SNTP servers.
    """

    def create(self) -> SNTPServersOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return SNTPServersOptionHandler(self.addresses, always_send=self.always_send)
