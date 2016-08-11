"""
Handlers for the options defined in dhcpkit.ipv6.extensions.map
"""
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.extensions.map import S46BROption, S46DMROption, S46MapEContainerOption, S46MapTContainerOption, \
    S46RuleOption
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler
from typing import Iterable


class MapEOptionHandler(SimpleOptionHandler):
    """
    Handler for putting an S46MapEContainerOption in responses
    """

    def __init__(self, br_addresses: Iterable[IPv6Address], rules: Iterable, always_send: bool = False):
        options = list()
        options += [rule() for rule in rules]
        options += [S46BROption(br_address=br_address) for br_address in br_addresses]

        option = S46MapEContainerOption(options=options)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        mappings = self.option.get_options_of_type(S46RuleOption)
        brs = self.option.get_options_of_type(S46BROption)
        return "{} with {} mapping(s) and {} BR(s)".format(self.__class__.__name__, len(mappings), len(brs))


class MapTOptionHandler(SimpleOptionHandler):
    """
    Handler for putting an S46MapTContainerOption in responses
    """

    def __init__(self, dmr_prefix: IPv6Network, rules: Iterable, always_send: bool = False):
        options = list()
        options += [rule() for rule in rules]
        options += [S46DMROption(dmr_prefix=dmr_prefix)]

        option = S46MapTContainerOption(options=options)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        mappings = self.option.get_options_of_type(S46RuleOption)
        return "{} with {} mapping(s)".format(self.__class__.__name__, len(mappings))
