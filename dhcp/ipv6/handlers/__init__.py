from abc import ABC, abstractmethod
import configparser
import logging

from dhcp.ipv6.messages import Message
from dhcp.rwlock import RWLock

logger = logging.getLogger(__name__)


class Handler(ABC):
    """
    This is the base class for all Handlers. Subclassing this provides the most flexibility but it does require the
    most effort to implement correctly as well.
    """
    def __init__(self, config: configparser.ConfigParser):
        """
        Initialise the handler. The config is provided from the configuration file, which is guaranteed to have a
        [handler] section.

        Objects of this class *MUST* be thread-safe.

        :param config: Contents of the configuration file
        """
        self.config = config

        # Provide a lock so that our state can be protected during a reload
        self.lock = RWLock()

    def reload(self, new_config: configparser.ConfigParser) -> None:
        """
        This is called by the server on SIGHUP so the configuration can be reloaded, caches can be cleared etc.

        Subclasses shouldn't overwrite this method but the handle_reload() method, which will automatically be
        protected with a lock.

        :param new_config: The new configuration after the reload
        """
        with self.lock.write_lock():
            self.config = new_config
            self.handle_reload()

    def handle_reload(self) -> None:
        """
        This method can be overwritten by subclasses to handle configuration reloads.
        """
        pass

    @abstractmethod
    def handle(self, received_message: Message, sender: tuple, receiver: tuple) -> Message or None:
        """
        The main dispatcher for incoming messages. Subclasses must overwrite this.

        :param received_message: The parsed incoming request
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """
