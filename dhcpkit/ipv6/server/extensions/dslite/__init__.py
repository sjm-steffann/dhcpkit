"""
Handlers for the options defined in dhcpkit.ipv6.extensions.dslite
"""

from dhcpkit.ipv6.extensions.dslite import AFTRNameOption

from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler


class AFTRNameOptionHandler(SimpleOptionHandler):
    """
    Handler for putting an AFTRNameOption in responses
    """

    def __init__(self, fqdn: str, always_send: bool = False):
        option = AFTRNameOption(fqdn=fqdn)
        option.validate()

        super().__init__(option, always_send=always_send)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, self.option.fqdn)
