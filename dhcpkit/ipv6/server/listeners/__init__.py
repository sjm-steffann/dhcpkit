"""
Code to keep the receiving and sending sockets together. When receiving traffic on a link-local multicast address
the reply should be sent from a link-local address on the receiving interface. This class makes it easy to keep those
together.
"""
import abc
import logging
import socket
from ipaddress import IPv6Address

from typing import Iterable

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.common.server.logging import DEBUG_PACKETS
from dhcpkit.ipv6 import SERVER_PORT, CLIENT_PORT

logger = logging.getLogger(__name__)

# A global counter for log message correlation
message_counter = 0


class ListeningSocketError(Exception):
    """
    Signal that the listening socket could not be created.
    """


# Create optimised classes to store packets and metadata in
class IncomingPacketBundle:
    """
    A class that is very efficient to pickle because this is what will be sent to worker processes.

    Using a class instead of a namedtuple makes it easier to extend it in the future. To make this possible all
    properties should have a default value, and the constructor must be called with keyword arguments only.
    """

    def __init__(self, *, message_id: str = '????', data: bytes = b'', sender: IPv6Address = None,
                 link_address: IPv6Address = None, interface_id: bytes = b'', received_over_multicast: bool = False,
                 marks: Iterable[str] = None):
        """
        Store the provided data

        :param message_id: An identifier for logging to correlate log-messages
        :param data: The bytes received from the listener
        :param sender: The IPv6 address of the sender
        :param link_address: The IPv6 address to identify the link that the packet was received over
        :param interface_id: The interface-ID  to identify the link that the packet was received over
        :param received_over_multicast: Whether this packet was received over multicast
        :param marks: A list of marks, usually set by the listener based on the configuration
        """
        self.message_id = message_id
        self.data = data
        self.sender = sender
        self.link_address = link_address or IPv6Address(0)
        self.interface_id = interface_id
        self.received_over_multicast = received_over_multicast,
        self.marks = list(marks or [])

    def __getstate__(self):
        return (self.message_id, self.data, self.sender, self.link_address, self.interface_id,
                self.received_over_multicast, self.marks)

    def __setstate__(self, state):
        (self.message_id, self.data, self.sender, self.link_address, self.interface_id,
         self.received_over_multicast, self.marks) = state


class OutgoingPacketBundle:
    """
    A class that is very efficient to pickle because this is what will be received back from worker processes.

    Using a class instead of a namedtuple makes it easier to extend it in the future. To make this possible all
    properties should have a default value, and the constructor must be called with keyword arguments only.
    """

    def __init__(self, *, message_id: str = '????', data: bytes = b'', destination: IPv6Address = None,
                 port: int = CLIENT_PORT):
        """
        Store the provided data

        :param message_id: An identifier for logging to correlate log-messages
        :param data: The bytes that should be sent by the listener
        :param destination: The IPv6 address of the destination
        :param port: The port number the packet should be sent to
        """
        self.message_id = message_id
        self.data = data
        self.destination = destination
        self.port = port

    def __getstate__(self):
        """
        Pickle the state as a tuple.
        """
        return self.message_id, self.data, self.destination, self.port

    def __setstate__(self, state):
        """
        Parse the state as a tuple.
        """
        self.message_id, self.data, self.destination, self.port = state


class Listener:
    """
    A wrapper for a normal socket that bundles a socket to listen on with a (potentially different) socket
    to send replies from.

    :param interface_name: The name of the interface
    :param listen_socket: The socket we are listening on, may be a unicast or multicast socket
    :param reply_socket: The socket replies are sent from, must be a unicast socket
    :param global_address: The global address on the listening interface

    :type interface_name: str
    :type interface_index: int
    :type listen_socket: socket.socket
    :type listen_address: IPv6Address
    :type reply_socket: socket.socket
    :type reply_address: IPv6Address
    :type global_address: IPv6Address
    """

    def __init__(self, interface_name: str, listen_socket: socket.socket, reply_socket: socket.socket = None,
                 global_address: IPv6Address = None, marks: Iterable[str] = None):
        self.interface_name = interface_name
        self.interface_id = interface_name.encode('utf-8')
        self.listen_socket = listen_socket
        self.reply_socket = reply_socket
        self.marks = list(marks or [])
        if self.reply_socket is None:
            self.reply_socket = self.listen_socket

        # Check that we have IPv6 UDP sockets
        if self.listen_socket.family != socket.AF_INET6 or self.listen_socket.proto != socket.IPPROTO_UDP \
                or self.reply_socket.family != socket.AF_INET6 or self.reply_socket.proto != socket.IPPROTO_UDP:
            raise ListeningSocketError("Listen and reply sockets have to be IPv6 UDP sockets")

        listen_sockname = self.listen_socket.getsockname()
        reply_sockname = self.reply_socket.getsockname()

        # Check that we are on the right port
        if listen_sockname[1] != SERVER_PORT or reply_sockname[1] != SERVER_PORT:
            raise ListeningSocketError("Listen and reply sockets have to be on port {}".format(SERVER_PORT))

        # Check that they are both on the same interface
        if listen_sockname[3] != reply_sockname[3]:
            raise ListeningSocketError("Listen and reply sockets have to be on same interface")

        self.interface_index = listen_sockname[3]
        self.listen_address = IPv6Address(listen_sockname[0].split('%')[0])
        self.reply_address = IPv6Address(reply_sockname[0].split('%')[0])

        if global_address:
            self.global_address = global_address
        elif not self.listen_address.is_link_local and not self.listen_address.is_multicast:
            self.global_address = self.listen_address
        else:
            raise ListeningSocketError("Cannot determine global address on interface {}".format(self.interface_name))

        # We only support fixed address binding
        if self.listen_address.is_unspecified or self.reply_address.is_unspecified:
            raise ListeningSocketError("This server only supports listening on explicit address, not on wildcard")

        # Multicast listeners must have link-local reply addresses
        if self.listen_address.is_multicast and not self.reply_address.is_link_local:
            raise ListeningSocketError("Multicast listening addresses need link-local reply socket")

        # Non-multicast listeners need to use a single address
        if not self.listen_address.is_multicast and self.reply_socket != self.listen_socket:
            raise ListeningSocketError("Unicast listening addresses can't use separate reply sockets")

    def recv_request(self) -> IncomingPacketBundle:
        """
        Receive incoming messages

        :return: The address of the sender of the message and the received message
        """
        data, sender = self.listen_socket.recvfrom(65536)

        # Update the message counter and wrap it if necessary
        global message_counter
        message_counter += 1
        if message_counter > 0xFFFFFF:
            message_counter = 1

        # Create the message-ID
        message_id = '#{:06X}'.format(message_counter)

        logger.log(DEBUG_PACKETS, "{message_id}: Received message from {client_addr} port {port} on {interface}".format(
            message_id=message_id,
            client_addr=sender[0],
            port=sender[1],
            interface=self.interface_name))

        return IncomingPacketBundle(message_id=message_id,
                                    data=data,
                                    sender=IPv6Address(sender[0].split('%')[0]),
                                    link_address=self.global_address,
                                    interface_id=self.interface_id,
                                    received_over_multicast=self.listen_address.is_multicast,
                                    marks=self.marks)

    def send_reply(self, packet: OutgoingPacketBundle) -> bool:
        """
        Send a reply using the information in the outer RelayReplyMessage

        :param packet: The packet to reply with
        :return: Whether sending has succeeded
        """

        destination = (str(packet.destination), packet.port, 0, self.interface_index)

        sent_length = self.reply_socket.sendto(packet.data, destination)
        success = len(packet.data) == sent_length

        if success:
            logger.log(DEBUG_PACKETS, "{message_id}: Sent message to {client_addr} port {port} on {interface}".format(
                message_id=packet.message_id,
                client_addr=packet.destination,
                port=packet.port,
                interface=self.interface_name))
        else:
            logger.error("{message_id}: Could not send message to {client_addr} port {port} on {interface}".format(
                message_id=packet.message_id,
                client_addr=packet.destination,
                port=packet.port,
                interface=self.interface_name))

        return success

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        return self.listen_socket.fileno()


class ListenerFactory(ConfigElementFactory, metaclass=abc.ABCMeta):
    """
    Base class for listener factories
    """

    @staticmethod
    def match_socket(sock: socket.socket, address: IPv6Address, interface: int = 0) -> bool:
        """
        Determine if we can recycle this socket

        :param sock: An existing socket
        :param address: The address we want
        :param interface: The interface number we want
        :return: Whether the socket is suitable
        """
        if sock.family != socket.AF_INET6 or sock.type != socket.SOCK_DGRAM or sock.proto != socket.IPPROTO_UDP:
            # Different protocol
            return False

        sockname = sock.getsockname()
        if IPv6Address(sockname[0].split('%')[0]) != address or sockname[1] != SERVER_PORT or sockname[3] != interface:
            # Wrong address
            return False

        # Amazing! This one seems to match
        return True
