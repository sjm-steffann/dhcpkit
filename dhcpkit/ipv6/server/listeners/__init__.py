"""
Code to keep the receiving and sending sockets together. When receiving traffic on a link-local multicast address
the reply should be sent from a link-local address on the receiving interface. This class makes it easy to keep those
together.
"""
import logging
from ipaddress import IPv6Address

from dhcpkit.ipv6.messages import RelayReplyMessage
from dhcpkit.ipv6.options import Option
from typing import Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

# A global counter for log message correlation
message_counter = 0


def increase_message_counter():
    """
    Increase the message counter and return the new value

    :return: The new value of the message counter
    """
    global message_counter

    # Update the message counter and wrap it if necessary
    message_counter += 1
    if message_counter > 0xFFFFFF:
        message_counter = 1

    return message_counter


class ListenerError(Exception):
    """
    Base class for listener errors
    """


class ListeningSocketError(ListenerError):
    """
    Signal that the listening socket could not be created.
    """


class IgnoreMessage(ListeningSocketError):
    """
    Signal that this message should be ignored
    """


class IncompleteMessage(IgnoreMessage):
    """
    Signal that the socket isn't done receiving yet
    """


class ClosedListener(ListeningSocketError):
    """
    Signal that the socket isn't done receiving yet
    """


# Create optimised classes to store packets and metadata in
class IncomingPacketBundle:
    """
    A class that is very efficient to pickle because this is what will be sent to worker processes.

    Using a class instead of a namedtuple makes it easier to extend it in the future. To make this possible all
    properties should have a default value, and the constructor must be called with keyword arguments only.
    """

    def __init__(self, *, message_id: str = '??????', data: bytes = b'',
                 source_address: IPv6Address = None, link_address: IPv6Address = None, interface_index: int = -1,
                 received_over_multicast: bool = False, received_over_tcp: bool = False, marks: Iterable[str] = None,
                 relay_options: Iterable[Option] = None):
        """
        Store the provided data

        :param message_id: An identifier for logging to correlate log-messages
        :param data: The bytes received from the listener
        :param source_address: The IPv6 address of the sender
        :param link_address: The IPv6 address to identify the link that the packet was received over
        :param interface_index: The numerical interface-ID to send the reply on
        :param received_over_multicast: Whether this packet was received over multicast
        :param received_over_tcp: Whether this packet was received over TCP
        :param marks: A list of marks, usually set by the listener based on the configuration
        :param relay_options: Extra relay options from the interface
        """
        self.message_id = message_id
        self.data = data
        self.source_address = source_address
        self.link_address = link_address or IPv6Address(0)
        self.interface_index = interface_index
        self.received_over_multicast = received_over_multicast
        self.received_over_tcp = received_over_tcp
        self.marks = list(marks or [])
        self.relay_options = list(relay_options or [])

    def __getstate__(self):
        return (self.message_id, self.data, self.source_address, self.link_address, self.interface_index,
                self.received_over_multicast, self.received_over_tcp, self.marks, self.relay_options)

    def __setstate__(self, state):
        (self.message_id, self.data, self.source_address, self.link_address, self.interface_index,
         self.received_over_multicast, self.received_over_tcp, self.marks, self.relay_options) = state


class Replier:
    """
    A class to send replies to the client
    """

    # Whether multiple replies can be sent over this replier
    can_send_multiple = False

    def send_reply(self, outgoing_message: RelayReplyMessage) -> bool:
        """
        Send a reply to the client

        :param outgoing_message: The message to send, including a wrapping RelayReplyMessage
        :return: Whether sending was successful
        """
        raise NotImplementedError


class Listener:
    """
    A class to represent something listening for incoming requests.
    """

    def recv_request(self) -> Tuple[IncomingPacketBundle, Replier]:
        """
        Receive incoming messages

        :return: The incoming packet data and a replier object
        """
        raise NotImplementedError

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        raise NotImplementedError


class ListenerCreator:
    """
    A class to represent something that creates something to listen for incoming requests.
    """

    def create_listener(self) -> Optional[Listener]:
        """
        Receive incoming messages

        :return: The incoming packet data and a replier object
        """
        raise NotImplementedError

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        raise NotImplementedError
