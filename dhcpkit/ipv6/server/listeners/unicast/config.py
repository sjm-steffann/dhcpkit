"""
Factory for the implementation of a listener on a unicast address of a local network interface
"""
import logging
import netifaces
import socket
from ipaddress import IPv6Address

from ZConfig.matcher import SectionValue

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6 import SERVER_PORT
from dhcpkit.ipv6.server.listeners import Listener
from dhcpkit.ipv6.utils import is_global_unicast

logger = logging.getLogger(__name__)


class UnicastListenerFactory(ConfigElementFactory):
    """
    Factory for the implementation of a listener on a unicast address of a local network interface
    """

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
        if not is_global_unicast(self.name):
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

    def create(self) -> Listener:
        """
        Create a listener of this class based on the configuration in the config section.

        :return: A listener object
        """
        logger.debug("Creating socket for {} on {}".format(self.name, self.found_interface))

        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.bind((str(self.name), SERVER_PORT))
        return Listener(self.found_interface, sock, marks=self.marks)
