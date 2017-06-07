"""
Factory for the implementation of a listener on a unicast address of a local network interface
"""
import logging
import netifaces
import socket
from ipaddress import IPv6Address

from ZConfig.matcher import SectionValue
from typing import Iterable

from dhcpkit.ipv6.server.listeners import Listener
from dhcpkit.ipv6.server.listeners.factories import UDPListenerFactory
from dhcpkit.ipv6.server.listeners.udp import UDPListener
from dhcpkit.ipv6.utils import is_global_unicast

logger = logging.getLogger(__name__)


class UnicastUDPListenerFactory(UDPListenerFactory):
    """
    Factory for the implementation of a listener on a unicast address of a local network interface
    """

    # noinspection PyTypeChecker
    name_datatype = staticmethod(IPv6Address)

    def __init__(self, section: SectionValue):
        # Auto-detect the interface name that the specified address is on
        self.found_interface = None

        super().__init__(section)

    def validate_config_section(self):
        """
        Validate the interface information
        """
        # Validate what the user supplied
        if not is_global_unicast(self.name) and self.name != IPv6Address('::1'):
            raise ValueError("The listener address must be a global unicast address")

        for interface_name in netifaces.interfaces():
            interface_addresses = [IPv6Address(addr_info['addr'].split('%')[0])
                                   for addr_info
                                   in netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])]

            if self.name in interface_addresses:
                self.found_interface = interface_name
                break

        if not self.found_interface:
            raise ValueError("Cannot find address {} on any interface".format(self.name))

    def create(self, old_listeners: Iterable[Listener] = None) -> UDPListener:
        """
        Create a listener of this class based on the configuration in the config section.

        :param old_listeners: A list of existing listeners in case we can recycle them
        :return: A listener object
        """
        # Try recycling
        old_listeners = list(old_listeners or [])
        for old_listener in old_listeners:
            if not isinstance(old_listener, UDPListener):
                continue

            if self.match_socket(sock=old_listener.listen_socket, address=self.name):
                logger.debug("Recycling existing socket for {} on {}".format(self.name, self.found_interface))
                sock = old_listener.listen_socket
                break
        else:
            logger.debug("Creating socket for {} on {}".format(self.name, self.found_interface))
            sock = socket.socket(socket.AF_INET6, self.sock_type, self.sock_proto)
            sock.bind((str(self.name), self.listen_port))

        return UDPListener(self.found_interface, sock, marks=self.marks)
