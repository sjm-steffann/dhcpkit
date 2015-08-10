"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.ntp
"""

import configparser
import re

from dhcpkit.ipv6.extensions.ntp import NTPSubOption, NTPServersOption, name_registry
from dhcpkit.ipv6.option_handlers import SimpleOptionHandler, OptionHandler, register_option_handler
from dhcpkit.utils import camelcase_to_dash


class NTPServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, sub_options: [NTPSubOption]):
        option = NTPServersOption(options=sub_options)
        option.validate()

        super().__init__(option)

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        sub_options = []

        for name, value in section.items():
            # Strip numbers from the end, this can be used to supply the same option multiple times
            name = name.rstrip('0123456789-')

            if '-' in name or '_' in name:
                suboption_name = name.replace('_', '-').lower()
            else:
                suboption_name = camelcase_to_dash(name)

            suboption = name_registry.get(suboption_name)
            if not suboption:
                raise configparser.ParsingError("Unknown suboption: {}".format(suboption_name))

            for suboption_value in re.split('[,\t ]+', value):
                if not suboption_value:
                    raise configparser.ParsingError("{} option has no value".format(name))

                sub_options.append(suboption.from_string(suboption_value))

        return cls(sub_options)


register_option_handler(NTPServersOptionHandler)
