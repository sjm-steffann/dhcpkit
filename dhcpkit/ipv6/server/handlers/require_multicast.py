"""
A simple handler that tells the client to use multicast to reach this server.
"""
import logging

from dhcpkit.ipv6.server.handlers import Handler, HandlerFactory, UseMulticastError
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class RequireMulticastHandler(Handler):
    """
    A simple handler that tells the client to use multicast to reach this server.
    """

    def pre(self, bundle: TransactionBundle):
        """
        Reject unicast messages

        :param bundle: The transaction bundle
        """
        if not bundle.received_over_multicast:
            logging.info("Rejecting unicast {}".format(bundle))
            raise UseMulticastError("This server does not support unicast requests")


class RequireMulticastHandlerFactory(HandlerFactory):
    """
    Create a RequireMulticastHandler
    """

    def create(self) -> Handler:
        """
        Create a RequireMulticastHandler
        """
        return RequireMulticastHandler()
