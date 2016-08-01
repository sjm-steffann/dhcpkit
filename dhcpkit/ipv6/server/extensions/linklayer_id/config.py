"""
Config processing for a handler to echo a LinkLayerIdOption back to the relay
"""
from dhcpkit.ipv6.server.extensions.linklayer_id import CopyLinkLayerIdOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class CopyLinkLayerIdOptionHandlerFactory(HandlerFactory):
    """
    Config processing for a handler to echo a LinkLayerIdOption back to the relay
    """
    def create(self) -> CopyLinkLayerIdOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return CopyLinkLayerIdOptionHandler()
