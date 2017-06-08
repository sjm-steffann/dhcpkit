"""
Configuration elements for the MAP server option handlers
"""
import math

from cached_property import cached_property
from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6.extensions.map import S46PortParametersOption, S46RuleOption
from dhcpkit.ipv6.server.extensions.map import MapEOptionHandler, MapTOptionHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory


def power_of_two(value: str) -> int:
    """
    Validate whether this is an integer that is a power of two.

    :param value: The config string
    :return: The integer value
    """
    value = int(value)
    if value <= 0 or ((value & (value - 1)) != 0):
        raise ValueError("Value is not a power of 2")
    return value


class MapRule(ConfigElementFactory):
    """
    Representation of a single MAP rule
    """

    @cached_property
    def k_bits(self):
        """
        k bits: length in bits of the PSID (2^k == sharing_ratio)

        :return: Number of bits
        """
        return int(math.log(self.sharing_ratio, 2))

    @cached_property
    def m_bits(self):
        """
        m bits: number of bits after the PSID (2^m == contiguous ports)

        :return: Number of bits
        """
        return int(math.log(self.contiguous_ports, 2))

    @cached_property
    def a_bits(self):
        """
        a bits: offset of the PSID bits

        :return: Number of bits
        """
        return 16 - self.k_bits - self.m_bits

    @cached_property
    def ea_len(self):
        """
        Calculate the number of Embedded Address bits.

        :return: Number of bits
        """
        ipv4_bits = 32 - self.ipv4_prefix.prefixlen
        return ipv4_bits + self.k_bits

    def validate_config_section(self):
        """
        Check whether the combination of parameters make sense.
        """
        if self.a_bits < 0:
            raise ValueError("There are not enough bits in a port number for a sharing ratio of {}"
                             "with {} contiguous ports".format(self.sharing_ratio, self.contiguous_ports))

        if self.ipv6_prefix.prefixlen + self.ea_len > 64:
            raise ValueError("An IPv6 prefix length of {} is too short"
                             "for {} Embedded Address bits".format(self.ipv6_prefix.prefixlen, self.ea_len))

    def create(self) -> S46RuleOption:
        """
        Create a MAP rule option based on the configuration.

        :return: The mapping rule
        """

        option = S46RuleOption(ea_len=self.ea_len, ipv4_prefix=self.ipv4_prefix, ipv6_prefix=self.ipv6_prefix, options=[
            S46PortParametersOption(offset=self.a_bits)
        ])
        option.fmr = self.forwarding_mapping
        return option


class MapEOptionHandlerFactory(HandlerFactory):
    """
    Create a handler for putting an S46MapEContainerOption in responses
    """

    def create(self) -> MapEOptionHandler:
        """
        Create a handler for putting an S46MapEContainerOption in responses

        :return: A handler object
        """
        return MapEOptionHandler(br_addresses=self.br_addresses, rules=self.map_rules, always_send=self.always_send)


class MapTOptionHandlerFactory(HandlerFactory):
    """
    Create a handler for putting an S46MapTContainerOption in responses
    """

    def create(self) -> MapTOptionHandler:
        """
        Create a handler for putting an S46MapTContainerOption in responses

        :return: A handler object
        """
        return MapTOptionHandler(dmr_prefix=self.default_mapping, rules=self.map_rules, always_send=self.always_send)
