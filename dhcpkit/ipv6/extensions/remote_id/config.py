from dhcpkit.ipv6.extensions.remote_id.option_handlers import CopyRemoteIdOptionHandler
from dhcpkit.ipv6.server.config import ConfigElementFactory


class CopyRemoteIdOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> CopyRemoteIdOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Nothing special
        return CopyRemoteIdOptionHandler()
