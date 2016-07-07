"""
Option handlers that inserts a PreferenceOption in replies
"""
from dhcpkit.ipv6.options import PreferenceOption
from dhcpkit.ipv6.server.handlers import HandlerFactory
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler


class PreferenceOptionHandler(SimpleOptionHandler):
    """
    The handler for PreferenceOption which adds a preference option to appropriate responses
    """

    def __init__(self, preference: int):
        # This option remains constant, so create a singleton that can be re-used
        option = PreferenceOption(preference=preference)
        option.validate()

        super().__init__(option, always_send=True)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, self.option.preference)


class PreferenceOptionHandlerFactory(HandlerFactory):
    """
    Create an IgnoreRequestHandler
    """

    def create(self) -> PreferenceOptionHandler:
        """
        Create an IgnoreRequestHandler
        """
        return PreferenceOptionHandler(preference=self.level)
