"""
Factory base classes for listener factories
"""

import socket
from ipaddress import IPv6Address

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6 import SERVER_PORT


class ListenerFactory(ConfigElementFactory):
    """
    Base class for listener factories
    """
    sock_type = None
    sock_proto = None
    listen_port = SERVER_PORT

    def match_socket(self, sock: socket.socket, address: IPv6Address, interface: int = 0) -> bool:
        """
        Determine if we can recycle this socket

        :param sock: An existing socket
        :param address: The address we want
        :param interface: The interface number we want
        :return: Whether the socket is suitable
        """
        if sock.family != socket.AF_INET6 or sock.type != self.sock_type or sock.proto != self.sock_proto:
            # Different protocol
            return False

        sockname = sock.getsockname()
        if IPv6Address(sockname[0].split('%')[0]) != address \
                or sockname[1] != self.listen_port \
                or sockname[3] != interface:
            # Wrong address
            return False

        # Amazing! This one seems to match
        return True


class UDPListenerFactory(ListenerFactory):
    """
    Base class for UDP listener factories
    """
    sock_type = socket.SOCK_DGRAM
    sock_proto = socket.IPPROTO_UDP


class TCPListenerFactory(ListenerFactory):
    """
    Base class for TCP listener factories
    """
    sock_type = socket.SOCK_STREAM
    sock_proto = socket.IPPROTO_TCP
