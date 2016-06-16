"""
Handlers: the things that take action on an incoming message and possibly update the response
"""
import logging

import abc

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.handlers.basic import IgnoreRequestHandler

logger = logging.getLogger(__name__)


class HandlerFactory(ConfigElementFactory, metaclass=abc.ABCMeta):
    """
    Base class for handler factories
    """


class IgnoreRequestHandlerFactory(HandlerFactory):
    """
    Create an IgnoreRequestHandler
    """

    def create(self) -> Handler:
        """
        Create an IgnoreRequestHandler
        """
        return IgnoreRequestHandler()
