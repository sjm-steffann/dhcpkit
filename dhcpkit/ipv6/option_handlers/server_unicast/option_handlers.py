"""
Option handlers that inserts a ServerUnicastOption in replies
"""

from ipaddress import IPv6Address

from dhcpkit.ipv6.option_handlers import SimpleOptionHandler
from dhcpkit.ipv6.options import ServerUnicastOption


class ServerUnicastOptionHandler(SimpleOptionHandler):
    """
    The handler for inserting ServerUniCastOptions into responses
    """

    def __init__(self, address: IPv6Address):
        # This option remains constant, so create a singleton that can be re-used
        option = ServerUnicastOption(server_address=address)
        option.validate()

        super().__init__(option, always_send=True)
