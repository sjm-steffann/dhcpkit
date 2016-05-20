import logging
import netifaces
import socket
from ipaddress import IPv6Address

from dhcpkit.ipv6 import SERVER_PORT
from dhcpkit.ipv6.listening_socket import ListeningSocket
from dhcpkit.ipv6.server.config import ConfigElementFactory

logger = logging.getLogger()


class GlobalAddressListenerFactory(ConfigElementFactory):
    def create(self) -> ListeningSocket:
        """
        Create a listener of this class based on the configuration in the config section.

        :return: A listener object
        """
        address = IPv6Address(self.section.getSectionName())
        interface_name = self.section.interface
        interface_addresses = [IPv6Address(addr_info['addr'].split('%')[0])
                               for addr_info
                               in netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])]

        if address not in interface_addresses:
            raise ValueError("Cannot find address {} on interface {}".format(address, interface_name))

        logger.debug("- Creating socket for {} on {}".format(address, self.section.interface))

        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.bind((str(address), SERVER_PORT))
        return ListeningSocket(self.section.interface, sock)
