"""
A class to keep the receiving and sending sockets together. When receiving traffic on a link-local multicast address
the reply should be sent from a link-local address on the receiving interface. This class makes it easy to keep those
together.
"""
from ipaddress import IPv6Address
import socket


class ListeningSocketError(Exception):
    pass


class ListeningSocket:
    def __init__(self, listen_socket: socket.socket, reply_socket: socket.socket=None):
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
            raise ListeningSocketError("Listen and reply sockets have to be on port 547, the DHCPv6 server port")

        # Check that they are both on the same interface
        if listen_sockname[3] != reply_sockname[3]:
            raise ListeningSocketError("Listen and reply sockets have to be on the same interface")

        self.listen_address = IPv6Address(listen_sockname[0].split('%')[0])
        self.reply_address = IPv6Address(reply_sockname[0].split('%')[0])

        # We only support fixed address binding
        if self.listen_address.is_unspecified or self.reply_address.is_unspecified:
            raise ListeningSocketError("This server only supports listening on explicit addresses, not on the wildcard")

        # Multicast listeners must have link-local reply addresses
        if self.listen_address.is_multicast and not self.reply_address.is_link_local:
            raise ListeningSocketError("Multicast listening addresses need a link-local reply address")

        # Non-multicast listeners need to use a single address
        if not self.listen_address.is_multicast and self.reply_socket != self.listen_socket:
            raise ListeningSocketError("Unicast listening addresses can't use a separate reply sockets")

    def recv_request(self) -> (tuple, bytes):
        return self.listen_socket.recvfrom(65535)

    def send_reply(self, data: bytes, address: tuple) -> bool:
        data_length = len(data)
        sent_length = self.reply_socket.sendto(data, address)
        return data_length == sent_length

    def fileno(self):
        return self.listen_socket.fileno()
