"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.sol_max_rt
"""

import configparser

from dhcpkit.ipv6.extensions.sol_max_rt_technicolor import SolMaxRTTechnicolorOption
from dhcpkit.ipv6.option_handlers import OverwritingOptionHandler, OptionHandler, register_option_handler


class SolMaxRTTechnicolorOptionHandler(OverwritingOptionHandler):
    """
    Handler for putting SolMaxRTTechnicolorOption in responses
    """

    def __init__(self, sol_max_rt: int):
        option = SolMaxRTTechnicolorOption(sol_max_rt=sol_max_rt)
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
        sol_max_rt = section.getint('sol-max-rt')
        if sol_max_rt is None:
            raise configparser.NoOptionError('sol-max-rt', section.name)

        return cls(sol_max_rt)


register_option_handler(SolMaxRTTechnicolorOptionHandler)
