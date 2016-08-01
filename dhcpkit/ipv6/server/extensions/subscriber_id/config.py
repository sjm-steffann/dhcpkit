"""
Config processing for a handler to echo a SubscriberIdOption back to the relay
"""
from dhcpkit.ipv6.server.extensions.subscriber_id import CopySubscriberIdOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class CopySubscriberIdOptionHandlerFactory(HandlerFactory):
    """
    Config processing for a handler to echo a SubscriberIdOption back to the relay
    """
    def create(self) -> CopySubscriberIdOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """
        return CopySubscriberIdOptionHandler()
