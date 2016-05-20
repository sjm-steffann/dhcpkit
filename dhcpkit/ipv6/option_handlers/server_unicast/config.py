from dhcpkit.ipv6.option_handlers.server_unicast.option_handlers import ServerUnicastOptionHandler
from dhcpkit.ipv6.server.config import ConfigElementFactory


class ServerUnicastOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> ServerUnicastOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        return ServerUnicastOptionHandler(self.section.address)
