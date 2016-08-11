"""
Configuration elements for the SIP server option handlers
"""
from dhcpkit.ipv6.server.extensions.sip_servers import SIPServersAddressListOptionHandler, \
    SIPServersDomainNameListOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class SIPServersDomainNameListOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for SIP servers.
    """

    def create(self) -> SIPServersDomainNameListOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return SIPServersDomainNameListOptionHandler(domain_names=self.domain_names, always_send=self.always_send)


class SIPServersAddressListOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for SIP servers.
    """

    def create(self) -> SIPServersAddressListOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return SIPServersAddressListOptionHandler(sip_servers=self.addresses, always_send=self.always_send)
