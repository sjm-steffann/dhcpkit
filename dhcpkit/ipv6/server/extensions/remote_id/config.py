"""
Config processing for a handler to echo a RemoteIdOption back to the relay
"""
from dhcpkit.ipv6.server.extensions.remote_id import CopyRemoteIdOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class CopyRemoteIdOptionHandlerFactory(HandlerFactory):
    """
    Config processing for a handler to echo a RemoteIdOption back to the relay
    """
    def create(self) -> CopyRemoteIdOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return CopyRemoteIdOptionHandler()
