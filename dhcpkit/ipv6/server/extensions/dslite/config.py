"""
Configuration elements for the DS-Lite server option handlers
"""
from dhcpkit.ipv6.server.extensions.dslite import AFTRNameOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class AFTRNameOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for the AFTR tunnel endpoint.
    """

    def create(self) -> AFTRNameOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return AFTRNameOptionHandler(fqdn=self.fqdn, always_send=self.always_send)
