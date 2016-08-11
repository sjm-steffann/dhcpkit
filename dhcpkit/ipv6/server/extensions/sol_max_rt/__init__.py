"""
Handlers for the options defined in dhcpkit.ipv6.extensions.sol_max_rt
"""
from dhcpkit.ipv6.extensions.sol_max_rt import InfMaxRTOption, SolMaxRTOption
from dhcpkit.ipv6.server.handlers.basic import OverwriteOptionHandler


class SolMaxRTOptionHandler(OverwriteOptionHandler):
    """
    Handler for putting SolMaxRTOption in responses
    """

    def __init__(self, sol_max_rt: int, always_send: bool = False):
        option = SolMaxRTOption(sol_max_rt=sol_max_rt)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, self.option.sol_max_rt)


class InfMaxRTOptionHandler(OverwriteOptionHandler):
    """
    Handler for putting InfMaxRTOption in responses
    """

    def __init__(self, inf_max_rt: int, always_send: bool = False):
        option = InfMaxRTOption(inf_max_rt=inf_max_rt)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, self.option.inf_max_rt)
