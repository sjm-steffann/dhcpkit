"""
Option handlers that inserts a PreferenceOption in replies
"""

from dhcpkit.ipv6.option_handlers import SimpleOptionHandler
from dhcpkit.ipv6.options import PreferenceOption


class PreferenceOptionHandler(SimpleOptionHandler):
    """
    The handler for PreferenceOption which adds a preference option to appropriate responses
    """

    def __init__(self, preference: int):
        # This option remains constant, so create a singleton that can be re-used
        option = PreferenceOption(preference=preference)
        option.validate()

        super().__init__(option, always_send=True)
