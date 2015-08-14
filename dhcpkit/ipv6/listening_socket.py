"""
A class to keep the receiving and sending sockets together. When receiving traffic on a link-local multicast address
the reply should be sent from a link-local address on the receiving interface. This class makes it easy to keep those
together.
"""
from ipaddress import IPv6Address
import logging
import socket

from dhcpkit.ipv6 import SERVER_PORT, CLIENT_PORT
from dhcpkit.ipv6.exceptions import ListeningSocketError, InvalidPacketError
from dhcpkit.ipv6.messages import Message, RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.options import RelayMessageOption, InterfaceIdOption

logger = logging.getLogger(__name__)


class ListeningSocket:
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

    def __init__(self, interface_name: str, listen_socket: socket.socket, reply_socket: socket.socket=None,
                 global_address: IPv6Address=None):
        self.interface_name = interface_name
        self.interface_id = interface_name.encode('utf-8')
        self.listen_socket = listen_socket
        self.reply_socket = reply_socket
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
        elif not self.listen_address.is_link_local:
            self.global_address = self.listen_address
        elif not self.reply_address.is_link_local:
            self.global_address = self.reply_address
        else:
            raise ListeningSocketError("Cannot determine global address on interface {}".format(self.interface_name))

        # We only support fixed address binding
        if self.listen_address.is_unspecified or self.reply_address.is_unspecified:
            raise ListeningSocketError("This server only supports listening on explicit address, not on wildcard")

        # Multicast listeners must have link-local reply addresses
        if self.listen_address.is_multicast and not self.reply_address.is_link_local:
            raise ListeningSocketError("Multicast listening addresses need link-local reply address")

        # Non-multicast listeners need to use a single address
        if not self.listen_address.is_multicast and self.reply_socket != self.listen_socket:
            raise ListeningSocketError("Unicast listening addresses can't use separate reply sockets")

    def recv_request(self) -> RelayForwardMessage:
        """
        Receive incoming messages

        :return: The address of the sender of the message and the received message
        """
        pkt, sender = self.listen_socket.recvfrom(65536)
        try:
            length, msg_in = Message.parse(pkt)
        except ValueError as e:
            raise InvalidPacketError(str(e), sender=sender)

        # Determine the next hop count
        if isinstance(msg_in, RelayForwardMessage):
            next_hop_count = msg_in.hop_count + 1
        else:
            next_hop_count = 0

        # Construct useful log messages
        if isinstance(msg_in, RelayForwardMessage):
            inner_relay_message = msg_in.inner_relay_message
            inner_message = inner_relay_message.relayed_message

            relay_interface_id_option = inner_relay_message.get_option_of_type(InterfaceIdOption)
            if relay_interface_id_option:
                interface_id = relay_interface_id_option.interface_id
                try:
                    interface_id = interface_id.decode('ascii')
                except ValueError:
                    pass

                interface_id_str = '{} of '.format(interface_id)
            else:
                interface_id_str = ''

            logger.debug("Received {msg_type} from {client_addr} via {interface}relay {relay_addr}".format(
                msg_type=type(inner_message).__name__,
                client_addr=inner_relay_message.peer_address,
                relay_addr=sender[0],
                interface=interface_id_str))
        else:
            logger.debug("Received {msg_type} from {client_addr}".format(
                msg_type=type(msg_in).__name__,
                client_addr=sender[0]))

        # Pretend to be an internal relay and wrap the message like a relay would
        return RelayForwardMessage(hop_count=next_hop_count,
                                   link_address=self.global_address,
                                   peer_address=IPv6Address(sender[0].split('%')[0]),
                                   options=[
                                       InterfaceIdOption(interface_id=self.interface_id),
                                       RelayMessageOption(relayed_message=msg_in)
                                   ])

    def send_reply(self, message: RelayReplyMessage) -> bool:
        """
        Send a reply using the information in the outer RelayReplyMessage

        :param message: The message to reply with
        :return: Whether sending has succeeded
        """

        # Verify that the outer relay message makes sense
        if not isinstance(message, RelayReplyMessage):
            raise ValueError("The reply has to be wrapped in a RelayReplyMessage")

        if message.link_address != self.global_address:
            raise ValueError("The relay-reply link-address does not match the relay-forward link-address")

        interface_id_option = message.get_option_of_type(InterfaceIdOption)
        if interface_id_option and interface_id_option.interface_id != self.interface_id:
            # If there is an interface-id option its contents have to match
            raise ValueError("The interface-id in the reply does not match the interface-id of the request")

        reply = message.relayed_message
        if not reply:
            raise ValueError("The RelayReplyMessage does not contain a message")

        # Down to network addresses and bytes
        port = isinstance(reply, RelayReplyMessage) and SERVER_PORT or CLIENT_PORT
        destination = (str(message.peer_address), port, 0, self.interface_index)
        data = reply.save()

        data_length = len(data)
        sent_length = self.reply_socket.sendto(data, destination)
        success = data_length == sent_length

        # Construct useful log messages
        if isinstance(reply, RelayReplyMessage):
            inner_relay_message = reply.inner_relay_message
            inner_message = inner_relay_message.relayed_message

            relay_interface_id_option = inner_relay_message.get_option_of_type(InterfaceIdOption)
            if relay_interface_id_option:
                interface_id = relay_interface_id_option.interface_id
                try:
                    interface_id = interface_id.decode('ascii')
                except ValueError:
                    pass

                interface_id_str = '{} of '.format(interface_id)
            else:
                interface_id_str = ''

            if success:
                logger.debug("Sent {msg_type} to {client_addr} via {interface}relay {relay_addr}".format(
                    msg_type=type(inner_message).__name__,
                    client_addr=inner_relay_message.peer_address,
                    relay_addr=destination[0],
                    interface=interface_id_str))
            else:
                logger.error("{msg_type} to {client_addr} via {interface}relay {relay_addr} could not be sent".format(
                    msg_type=type(inner_message).__name__,
                    client_addr=inner_relay_message.peer_address,
                    relay_addr=destination[0],
                    interface=interface_id_str))
        else:
            if success:
                logger.debug("Sent {msg_type} to {client_addr}".format(
                    msg_type=type(reply).__name__,
                    client_addr=destination[0]))
            else:
                logger.error("{msg_type} to {client_addr} could not be sent".format(
                    msg_type=type(reply).__name__,
                    client_addr=destination[0]))

        return success

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        return self.listen_socket.fileno()
