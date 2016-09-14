"""
A simple handler that tells the server to ignore the request.
"""
import logging

from dhcpkit.ipv6.messages import Message
from dhcpkit.ipv6.server.handlers import CannotRespondError, Handler, HandlerFactory
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from typing import Iterable, Type

logger = logging.getLogger(__name__)


class IgnoreRequestHandler(Handler):
    """
    A simple handler that tells the server to stop processing the request and ignore it
    """

    def __init__(self, message_types: Iterable[Type[Message]] = None):
        super().__init__()
        self.message_types = tuple(set(message_types or []))

    def __str__(self):
        return "{} with {}".format(self.__class__.__name__, ', '.join([message_type.__class__.__name__
                                                                       for message_type in self.message_types]))

    def pre(self, bundle: TransactionBundle):
        """
        Stop processing

        :param bundle: The transaction bundle
        """
        # Ignore when no type specified, or when request matches a specified type
        if not self.message_types or isinstance(bundle.request, self.message_types):
            logging.info("Configured to ignore {}".format(bundle))
            raise CannotRespondError("Configured to ignore request")


class IgnoreRequestHandlerFactory(HandlerFactory):
    """
    Create an IgnoreRequestHandler
    """

    def create(self) -> Handler:
        """
        Create an IgnoreRequestHandler
        """
        return IgnoreRequestHandler(self.message_types)
