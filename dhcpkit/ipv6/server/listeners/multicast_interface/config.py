"""
Implementation of a listener on a local multicast network interface
"""
import logging
import netifaces
import socket
from ipaddress import IPv6Address
from struct import pack
from typing import Iterable

from dhcpkit.ipv6 import All_DHCP_Relay_Agents_and_Servers
from dhcpkit.ipv6.server.listeners import Listener
from dhcpkit.ipv6.server.listeners.factories import UDPListenerFactory
from dhcpkit.ipv6.server.listeners.udp import UDPListener
from dhcpkit.ipv6.utils import is_global_unicast

logger = logging.getLogger(__name__)


class MulticastInterfaceUDPListenerFactory(UDPListenerFactory):
    """
    Factory for the implementation of a listener on a local multicast network interface
    """

    # noinspection PyTypeChecker
    name_datatype = staticmethod(str)

    def validate_config_section(self):
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

    def create(self, old_listeners: Iterable[Listener] = None) -> UDPListener:
        """
        Create a listener of this class based on the configuration in the config section.

        :param old_listeners: A list of existing listeners in case we can recycle them
        :return: A listener object
        """
        mc_address = All_DHCP_Relay_Agents_and_Servers
        interface_index = socket.if_nametoindex(self.name)

        # Try recycling
        old_listeners = list(old_listeners or [])
        for old_listener in old_listeners:
            if not isinstance(old_listener, UDPListener):
                continue

            if self.match_socket(sock=old_listener.listen_socket, address=mc_address, interface=interface_index):
                logger.debug("Recycling existing multicast socket on {}".format(self.name))
                mc_sock = old_listener.listen_socket
                break
        else:
            logger.debug("Listening for multicast requests on {}".format(self.name))
            mc_sock = socket.socket(socket.AF_INET6, self.sock_type, self.sock_proto)
            mc_sock.bind((str(mc_address), self.listen_port, 0, interface_index))
            mc_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP,
                               pack('16sI', mc_address.packed, interface_index))

        # Set the socket options
        mc_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, self.listen_to_self and 1 or 0)

        for old_listener in old_listeners:
            if not isinstance(old_listener, UDPListener):
                continue

            if self.match_socket(sock=old_listener.listen_socket, address=self.reply_from, interface=interface_index):
                logger.debug("  - Recycling existing reply socket for {} on {}".format(self.reply_from, self.name))
                ll_sock = old_listener.listen_socket
                break

            if self.match_socket(sock=old_listener.reply_socket, address=self.reply_from, interface=interface_index):
                logger.debug("  - Recycling existing reply socket for {} on {}".format(self.reply_from, self.name))
                ll_sock = old_listener.reply_socket
                break
        else:
            logger.debug("  - Sending replies from {}".format(self.reply_from))
            ll_sock = socket.socket(socket.AF_INET6, self.sock_type, self.sock_proto)
            ll_sock.bind((str(self.reply_from), self.listen_port, 0, interface_index))

        return UDPListener(interface_name=self.name, listen_socket=mc_sock, reply_socket=ll_sock,
                           global_address=self.link_address, marks=self.marks)
