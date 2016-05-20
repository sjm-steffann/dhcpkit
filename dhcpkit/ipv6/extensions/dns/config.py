from dhcpkit.ipv6.extensions.dns.option_handlers import RecursiveNameServersOptionHandler, DomainSearchListOptionHandler
from dhcpkit.ipv6.server.config import ConfigElementFactory


class RecursiveNameServersOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> RecursiveNameServersOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        return RecursiveNameServersOptionHandler(dns_servers=self.section.addresses)


class DomainSearchListOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> DomainSearchListOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        return DomainSearchListOptionHandler(search_list=self.section.domain_names)
