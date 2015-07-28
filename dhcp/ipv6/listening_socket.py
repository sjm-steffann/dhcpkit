"""
A class to keep the receiving and sending sockets together. When receiving traffic on a link-local multicast address
the reply should be sent from a link-local address on the receiving interface. This class makes it easy to keep those
together.
"""
from ipaddress import IPv6Address
import logging
import socket

from dhcp.ipv6.exceptions import ListeningSocketError, InvalidPacketError
from dhcp.ipv6.messages import Message, RelayForwardMessage, RelayReplyMessage
from dhcp.ipv6.options import RelayMessageOption, InterfaceIdOption

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
        if listen_sockname[1] != 547 or reply_sockname[1] != 547:
            raise ListeningSocketError("Listen and reply sockets have to be on port 547")

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
        pkt, sender = self.listen_socket.recvfrom(65535)
        try:
            length, msg_in = Message.parse(pkt)

            # Determine the next hop count
            if isinstance(msg_in, RelayForwardMessage):
                next_hop_count = msg_in.hop_count + 1
            else:
                next_hop_count = 0

            # Log
            inner_message = msg_in
            while isinstance(inner_message, RelayForwardMessage):
                inner_message = inner_message.relayed_message

            logger.debug("Received {} from {}{}".format(type(inner_message).__name__,
                                                        isinstance(msg_in, RelayForwardMessage) and 'relay ' or '',
                                                        sender[0]))

            # Pretend to be an internal relay and wrap the message like a relay would
            return RelayForwardMessage(hop_count=next_hop_count,
                                       link_address=self.global_address,
                                       peer_address=IPv6Address(sender[0].split('%')[0]),
                                       options=[
                                           InterfaceIdOption(interface_id=self.interface_id),
                                           RelayMessageOption(relayed_message=msg_in)
                                       ])
        except ValueError as e:
            raise InvalidPacketError(str(e), sender=sender)

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

        relay_reply = message.get_option_of_type(RelayMessageOption)
        if not relay_reply:
            raise ValueError("The RelayReplyMessage does not contain a message")

        reply = relay_reply.relayed_message

        # Down to network addresses and bytes
        port = isinstance(reply, RelayReplyMessage) and 547 or 546
        destination = (str(message.peer_address), port, 0, self.interface_index)
        data = reply.save()

        data_length = len(data)
        sent_length = self.reply_socket.sendto(data, destination)
        success = data_length == sent_length

        if success:
            logger.debug("Sent {} to {}{}".format(type(reply).__name__,
                                                  isinstance(reply, RelayReplyMessage) and 'relay ' or '',
                                                  destination[0]))
        else:
            logger.error("{} to {}{} could not be sent".format(type(reply).__name__, data_length,
                                                               isinstance(reply, RelayReplyMessage) and 'relay ' or '',
                                                               destination[0]))

        return success

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        return self.listen_socket.fileno()
