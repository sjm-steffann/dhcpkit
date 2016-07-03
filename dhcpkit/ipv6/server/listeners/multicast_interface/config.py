"""
Implementation of a listener on a local multicast network interface
"""
import logging
import netifaces
import socket
from ipaddress import IPv6Address
from struct import pack

from dhcpkit.ipv6 import SERVER_PORT, All_DHCP_Relay_Agents_and_Servers
from dhcpkit.ipv6.server.listeners import Listener, ListenerFactory
from dhcpkit.ipv6.utils import is_global_unicast

logger = logging.getLogger(__name__)


class MulticastInterfaceListenerFactory(ListenerFactory):
    """
    Factory for the implementation of a listener on a local multicast network interface
    """

    name_datatype = staticmethod(str)

    def validate_config(self):
        """
        Validate the interface information
        """

        try:
            socket.if_nametoindex(self.name)
        except OSError:
            raise ValueError("Interface {} not found".format(self.name))

        interface_addresses = [IPv6Address(addr_info['addr'].split('%')[0])
                               for addr_info
                               in netifaces.ifaddresses(self.name).get(netifaces.AF_INET6, [])]

        # Pick the first link-local address as reply-from if none is specified in the configuration
        if not self.section.reply_from:
            for address in interface_addresses:
                if address.is_link_local:
                    self.section.reply_from = address
                    break

            if not self.section.reply_from:
                raise ValueError("No link-local address found on interface {}".format(self.name))

        else:
            # Validate what the user supplied
            if not self.section.reply_from.is_link_local:
                raise ValueError("The reply-from address must be a link-local address")

            if self.section.reply_from not in interface_addresses:
                raise ValueError("Cannot find reply-from address {} on interface {}".format(self.section.reply_from,
                                                                                            self.name))

        # Pick the first global unicast address as link-address if none is specified in the configuration
        if not self.section.link_address:
            for address in interface_addresses:
                if is_global_unicast(address):
                    self.section.link_address = address
                    break

            if not self.section.link_address:
                # Use the unspecified address is we couldn't find anything
                self.section.link_address = IPv6Address('::')

        else:
            # Validate what the user supplied (we don't really care if it exists, it's just extra information for the
            # option handlers
            if not is_global_unicast(self.section.link_address):
                raise ValueError("The link-address must be a global unicast address")

    def create(self) -> Listener:
        """
        Create a listener of this class based on the configuration in the config section.

        :return: A listener object
        """
        mc_address = IPv6Address(All_DHCP_Relay_Agents_and_Servers)

        interface_index = socket.if_nametoindex(self.name)

        logger.debug("Listening for multicast requests on ".format(self.name))

        mc_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        mc_sock.bind((str(mc_address), SERVER_PORT, 0, interface_index))

        if self.section.listen_to_self:
            mc_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)

        mc_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP,
                           pack('16sI', mc_address.packed, interface_index))

        logger.debug("  - Sending replies from {}".format(self.section.reply_from))

        ll_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ll_sock.bind((str(self.section.reply_from), SERVER_PORT, 0, interface_index))

        return Listener(interface_name=self.name, listen_socket=mc_sock, reply_socket=ll_sock,
                        global_address=self.section.link_address, marks=self.marks)
