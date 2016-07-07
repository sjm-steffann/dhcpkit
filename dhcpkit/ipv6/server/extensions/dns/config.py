"""
Configuration elements for the dns option handlers
"""
from dhcpkit.ipv6.server.extensions.dns import DomainSearchListOptionHandler, RecursiveNameServersOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class RecursiveNameServersOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for recursive name servers.
    """

    def create(self) -> RecursiveNameServersOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return RecursiveNameServersOptionHandler(dns_servers=self.addresses, always_send=self.always_send)


class DomainSearchListOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for the domain search list.
    """

    def create(self) -> DomainSearchListOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return DomainSearchListOptionHandler(search_list=self.domain_names, always_send=self.always_send)
