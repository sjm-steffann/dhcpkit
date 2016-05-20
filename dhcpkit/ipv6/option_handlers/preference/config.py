from ZConfig.datatypes import RangeCheckedConversion

from dhcpkit.ipv6.option_handlers.preference.option_handlers import PreferenceOptionHandler
from dhcpkit.ipv6.server.config import ConfigElementFactory

preference = RangeCheckedConversion(int, 0, 2 ** 8 - 1)


class PreferenceOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> PreferenceOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        return PreferenceOptionHandler(self.section.preference)
