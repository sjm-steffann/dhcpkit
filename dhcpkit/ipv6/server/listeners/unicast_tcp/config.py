"""
Factory for the implementation of a TCP listener on a unicast address of a local network interface
"""
import logging
import netifaces
import socket
from ipaddress import IPv6Address

from ZConfig.matcher import SectionValue
from dhcpkit.ipv6.server.listeners import Listener
from dhcpkit.ipv6.server.listeners.factories import TCPListenerFactory
from dhcpkit.ipv6.server.listeners.tcp import TCPConnectionListener
from dhcpkit.ipv6.utils import is_global_unicast
from typing import Iterable

logger = logging.getLogger(__name__)


class UnicastTCPListenerFactory(TCPListenerFactory):
    """
    Factory for the implementation of a listener on a unicast address of a local network interface
    """

    def __init__(self, section: SectionValue):
        # Auto-detect the interface name that the specified address is on
        self.found_interface = None

        super().__init__(section)

    def validate_config_section(self):
        """
        Validate the interface information
        """
        # Validate what the user supplied
        if not is_global_unicast(self.address):
            raise ValueError("The listener address must be a global unicast address")

        for interface_name in netifaces.interfaces():
            interface_addresses = [IPv6Address(addr_info['addr'].split('%')[0])
                                   for addr_info
                                   in netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])]

            if self.address in interface_addresses:
                self.found_interface = interface_name
                break

        if not self.found_interface:
            raise ValueError("Cannot find address {} on any interface".format(self.address))

    def create(self, old_listeners: Iterable[Listener] = None) -> TCPConnectionListener:
        """
        Create a listener of this class based on the configuration in the config section.

        :param old_listeners: A list of existing listeners in case we can recycle them
        :return: A listener object
        """
        # Try recycling
        old_listeners = list(old_listeners or [])
        for old_listener in old_listeners:
            if not isinstance(old_listener, TCPConnectionListener):
                continue

            if self.match_socket(sock=old_listener.listen_socket, address=self.address):
                logger.debug("Recycling existing TCP socket for {} on {}".format(self.address, self.found_interface))
                sock = old_listener.listen_socket
                break
        else:
            logger.debug("Creating TCP socket for {} on {}".format(self.address, self.found_interface))
            sock = socket.socket(socket.AF_INET6, self.sock_type, self.sock_proto)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((str(self.address), self.listen_port))
            sock.listen(10)

        return TCPConnectionListener(interface_name=self.found_interface, listen_socket=sock, marks=self.marks,
                                     allow_from=self.allow_from)
