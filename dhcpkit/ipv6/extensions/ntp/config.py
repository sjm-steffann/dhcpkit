from dhcpkit.ipv6.extensions.ntp.option_handlers import NTPServersOptionHandler
from dhcpkit.ipv6.extensions.ntp.options import name_registry, NTPSubOption
from dhcpkit.ipv6.server.config import ConfigElementFactory


def ntp_suboption_key(value: str) -> {NTPSubOption: [str]}:
    # Lower-case the key so we have a canonical name
    value_lower = value.lower()

    # Check if the type exists
    if value_lower not in name_registry:
        raise ValueError("'{}' is not a known NTP server type".format(value))

    # Save the canonical name for now
    return value_lower


class NTPServersOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> NTPServersOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Create the real suboptions
        suboptions = []
        for suboption_type, suboption_values in self.section.suboptions.items():
            suboption_class = name_registry[suboption_type]
            for suboption_value in suboption_values:
                suboption = suboption_class.from_string(suboption_value)
                suboptions.append(suboption)

        return NTPServersOptionHandler(suboptions)
