"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.sol_max_rt
"""

from dhcpkit.ipv6.extensions.sol_max_rt import SolMaxRTOption, InfMaxRTOption
from dhcpkit.ipv6.option_handlers import OverwritingOptionHandler, OptionHandler
from dhcpkit.ipv6.server.config_parser import ConfigError


class SolMaxRTOptionHandler(OverwritingOptionHandler):
    """
    Handler for putting SolMaxRTOption in responses
    """

    def __init__(self, sol_max_rt: int):
        option = SolMaxRTOption(sol_max_rt=sol_max_rt)
        option.validate()

        super().__init__(option)

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        sol_max_rt = section.get('sol-max-rt')
        if sol_max_rt is None:
            raise ConfigError('SolMaxRTOption needs sol-max-rt')

        return cls(int(sol_max_rt))


class InfMaxRTOptionHandler(OverwritingOptionHandler):
    """
    Handler for putting InfMaxRTOption in responses
    """

    def __init__(self, inf_max_rt: int):
        option = InfMaxRTOption(inf_max_rt=inf_max_rt)
        option.validate()

        super().__init__(option)

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        inf_max_rt = section.get('inf-max-rt')
        if inf_max_rt is None:
            raise ConfigError('InfMaxRTOption needs inf-max-rt')

        return cls(int(inf_max_rt))
