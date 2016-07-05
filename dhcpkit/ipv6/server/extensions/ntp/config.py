"""
Configuration elements for the NTP option handlers
"""
from dhcpkit.ipv6.extensions.ntp_suboption_registry import ntp_suboption_registry
from dhcpkit.ipv6.server.extensions.ntp import NTPServersOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


class NTPServersOptionHandlerFactory(HandlerFactory):
    """
    Create the handler for NTP servers.
    """

    def clean_config_section(self):
        """
        Convert the data to the right types
        """
        converted_suboptions = {}

        for suboption_type, suboption_values in self.section.suboptions.items():
            suboption_class = ntp_suboption_registry.by_name[suboption_type]

            # See if this option supports loading from configuration
            datatype = suboption_class.config_datatype
            if not datatype:
                raise ValueError("{} cannot be used in the configuration".format(suboption_type))

            # Convert the values and store
            converted_suboption_values = [datatype(value) for value in suboption_values]
            converted_suboptions[suboption_type] = converted_suboption_values

        # And replace the string versions
        self.section.suboptions = converted_suboptions

    def validate_config_section(self):
        """
        Make sure the keys refer to actual NTP sub-options
        """
        for key in self.suboptions:
            # Lower-case the key so we have a canonical name
            key_lower = key.lower()

            # Check if the type exists
            if key_lower not in ntp_suboption_registry.by_name:
                raise ValueError("'{}' is not a known NTP server type".format(key))

    def create(self) -> NTPServersOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Create the real suboptions. I think that usually one suboption type will be used, but in case someone uses
        # different types let's sort them alphabetically to at least have consistency. Unfortunately we can't know the
        # original order in the config file anymore :(
        suboptions = []
        suboption_types = sorted(self.suboptions.keys())
        for suboption_type in suboption_types:
            suboption_class = ntp_suboption_registry.by_name[suboption_type]
            suboption_values = self.suboptions[suboption_type]
            for suboption_value in suboption_values:
                suboption = suboption_class(suboption_value)
                suboptions.append(suboption)

        return NTPServersOptionHandler(suboptions, always_send=self.always_send)
