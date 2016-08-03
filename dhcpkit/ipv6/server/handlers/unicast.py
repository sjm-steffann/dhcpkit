"""
A simple handler that tells the client to use multicast to reach this server.
"""
import logging
from ipaddress import IPv6Address

from dhcpkit.ipv6.options import ServerUnicastOption
from dhcpkit.ipv6.server.handlers import Handler, HandlerFactory, UseMulticastError
from dhcpkit.ipv6.server.handlers.basic import SimpleOptionHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class RejectUnwantedUnicastHandler(Handler):
    """
    A simple handler that tells the client to use multicast to reach this server.
    """

    def pre(self, bundle: TransactionBundle):
        """
        Reject unicast messages

        :param bundle: The transaction bundle
        """
        # Check if unicast is allowed, otherwise check if we received the message over multicast or through a relay
        if not bundle.allow_unicast and not bundle.received_over_multicast and len(bundle.incoming_relay_messages) < 2:
            logging.info("Rejecting unicast {}".format(bundle))
            raise UseMulticastError("This server does not support unicast requests")


class ServerUnicastOptionHandler(SimpleOptionHandler):
    """
    A simple handler that tells the client that it may use unicast to contact this server.
    """

    def __init__(self, address: IPv6Address):
        # This option remains constant, so create a singleton that can be re-used
        option = ServerUnicastOption(server_address=address)
        option.validate()

        super().__init__(option, always_send=True)

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, self.option.server_address)

    def pre(self, bundle: TransactionBundle):
        """
        Set flag to let the server know that unicast is ok, otherwise RejectUnwantedUnicastHandler will reject it later.

        :param bundle: The transaction bundle
        """
        bundle.allow_unicast = True


class ServerUnicastOptionHandlerFactory(HandlerFactory):
    """
    Create a ServerUnicastOptionHandler
    """

    def create(self) -> ServerUnicastOptionHandler:
        """
        Create a RequireMulticastHandler
        """
        return ServerUnicastOptionHandler(self.address)
