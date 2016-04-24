"""
Base classes for DHCP message handlers
"""

import logging
from abc import ABC, abstractmethod

from dhcpkit.ipv6.messages import RelayServerMessage, Message
from dhcpkit.rwlock import RWLock

logger = logging.getLogger(__name__)


class MessageHandler(ABC):
    """
    This is the base class for all message handlers. Subclassing this provides the most flexibility but it does require
    the most effort to implement correctly as well.
    """

    def __init__(self, config: dict):
        """
        Initialise the handler. The config is provided from the configuration file, which is guaranteed to have a
        [handler] section.

        Objects of this class *MUST* be thread-safe.

        :param config: Contents of the configuration file
        """
        self.config = config

        # Provide a lock so that our state can be protected during a reload
        self.lock = RWLock()

        # Implement initialisation as a reload
        self.handle_reload()

    def reload(self, new_config: dict):
        """
        This is called by the server on SIGHUP so the configuration can be reloaded, caches can be cleared etc.

        Subclasses shouldn't overwrite this method but the handle_reload() method, which will automatically be
        protected with a lock.

        :param new_config: The new configuration after the reload
        """
        with self.lock.write_lock():
            self.config = new_config
            self.handle_reload()

    # noinspection PyMethodMayBeStatic
    def handle_reload(self):
        """
        This method can be overwritten by subclasses to handle configuration reloads.
        """
        pass

    @abstractmethod
    def handle(self, received_message: RelayServerMessage, received_over_multicast: bool) -> Message or None:
        """
        The main dispatcher for incoming messages. Subclasses must overwrite this. The incoming message is always
        wrapped in a RelayForwardMessage. That is: our server acts like an 'internal' relay. This way the interface
        information is captured for processing without having to differentiate between relayed and non-relayed
        messages in the handling logic.

        :param received_message: The parsed incoming request, wrapped in an 'internal' RelayServerMessage
        :param received_over_multicast: Whether the request was received over multicast
        :returns: The message to reply with
        """
