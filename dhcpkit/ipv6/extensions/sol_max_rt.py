"""
Classes and constants for the options defined in http://www.iana.org/go/rfc7083
"""

import configparser
from struct import unpack_from, pack

from dhcpkit.ipv6 import option_registry, option_handler_registry
from dhcpkit.ipv6.option_handlers import OverwritingOptionHandler, OptionHandler
from dhcpkit.ipv6.options import Option

OPTION_SOL_MAX_RT = 82
OPTION_INF_MAX_RT = 83


class SolMaxRTOption(Option):
    """
    http://tools.ietf.org/html/rfc7083#section-4

    A DHCPv6 server sends the SOL_MAX_RT option to a client to override
    the default value of SOL_MAX_RT.  The value of SOL_MAX_RT in the
    option replaces the default value defined in Section 3.  One use for
    the SOL_MAX_RT option is to set a longer value for SOL_MAX_RT, which
    reduces the Solicit traffic from a client that has not received a
    response to its Solicit messages.

    The format of the SOL_MAX_RT option is:

        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |          option-code          |         option-len            |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                       SOL_MAX_RT value                        |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

         option-code          OPTION_SOL_MAX_RT (82)

         option-len           4

         SOL_MAX_RT value     Overriding value for SOL_MAX_RT
                              in seconds; MUST be in range:
                                60 <= "value" <= 86400 (1 day)

                    Figure 1: SOL_MAX_RT Option Format

    :type sol_max_rt: int
    """

    option_type = OPTION_SOL_MAX_RT

    def __init__(self, sol_max_rt: int=0):
        self.sol_max_rt = sol_max_rt

    # noinspection PyDocstring
    def validate(self):
        if not isinstance(self.sol_max_rt, int) or not (0 <= self.sol_max_rt < 2 ** 32):
            raise ValueError("SOL_MAX_RT must be an unsigned 32 bit integer")

    # noinspection PyDocstring
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        if option_len != 4:
            raise ValueError('SOL_MAX_RT Options must have length 4')

        self.sol_max_rt = unpack_from('!I', buffer, offset=offset + my_offset)
        my_offset += 4

        self.validate()

        return my_offset

    # noinspection PyDocstring
    def save(self) -> bytes:
        self.validate()
        return pack('!HHI', self.option_type, 4, self.sol_max_rt)


class SolMaxRTOptionHandler(OverwritingOptionHandler):
    """
    Handler for putting SolMaxRTOption in responses
    """

    def __init__(self, sol_max_rt: int):
        option = SolMaxRTOption(sol_max_rt=sol_max_rt)
        option.validate()

        super().__init__(option)

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        sol_max_rt = section.getint('sol-max-rt')
        if sol_max_rt is None:
            raise configparser.NoOptionError('sol-max-rt', section.name)

        return cls(sol_max_rt)


class InfMaxRTOption(Option):
    """
    http://tools.ietf.org/html/rfc7083#section-5

    A DHCPv6 server sends the INF_MAX_RT option to a client to override
    the default value of INF_MAX_RT.  The value of INF_MAX_RT in the
    option replaces the default value defined in Section 3.  One use for
    the INF_MAX_RT option is to set a longer value for INF_MAX_RT, which
    reduces the Information-request traffic from a client that has not
    received a response to its Information-request messages.

    The format of the INF_MAX_RT option is:
        0                   1                   2                   3
        0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |          option-code          |         option-len            |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
       |                       INF_MAX_RT value                        |
       +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

         option-code          OPTION_INF_MAX_RT (83)

         option-len           4

         INF_MAX_RT value     Overriding value for INF_MAX_RT
                              in seconds; MUST be in range:
                                60 <= "value" <= 86400 (1 day)

                    Figure 2: INF_MAX_RT Option Format

    :type inf_max_rt: int
    """

    option_type = OPTION_INF_MAX_RT

    def __init__(self, inf_max_rt: int=0):
        self.inf_max_rt = inf_max_rt

    # noinspection PyDocstring
    def validate(self):
        if not isinstance(self.inf_max_rt, int) or not (0 <= self.inf_max_rt < 2 ** 32):
            raise ValueError("INF_MAX_RT must be an unsigned 32 bit integer")

    # noinspection PyDocstring
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        if option_len != 4:
            raise ValueError('INF_MAX_RT Options must have length 4')

        self.inf_max_rt = unpack_from('!I', buffer, offset=offset + my_offset)
        my_offset += 4

        self.validate()

        return my_offset

    # noinspection PyDocstring
    def save(self) -> bytes:
        self.validate()
        return pack('!HHI', self.option_type, 4, self.inf_max_rt)


class InfMaxRTOptionHandler(OverwritingOptionHandler):
    """
    Handler for putting InfMaxRTOption in responses
    """

    def __init__(self, inf_max_rt: int):
        option = InfMaxRTOption(inf_max_rt=inf_max_rt)
        option.validate()

        super().__init__(option)

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        inf_max_rt = section.getint('inf-max-rt')
        if inf_max_rt is None:
            raise configparser.NoOptionError('inf-max-rt', section.name)

        return cls(inf_max_rt)


option_registry.register(SolMaxRTOption)
option_registry.register(InfMaxRTOption)

option_handler_registry.register(SolMaxRTOptionHandler)
option_handler_registry.register(InfMaxRTOptionHandler)
