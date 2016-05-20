"""
Option handlers for the DNS options defined in dhcpkit.ipv6.extensions.ntp
"""

from dhcpkit.ipv6.extensions.ntp.options import NTPSubOption, NTPServersOption
from dhcpkit.ipv6.option_handlers import SimpleOptionHandler


class NTPServersOptionHandler(SimpleOptionHandler):
    """
    Handler for putting RecursiveNameServersOption in responses
    """

    def __init__(self, sub_options: [NTPSubOption]):
        option = NTPServersOption(options=sub_options)
        option.validate()

        super().__init__(option)
