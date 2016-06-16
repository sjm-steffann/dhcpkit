"""
Implementation of a listener on a local multicast network interface
"""
import logging
import netifaces
import socket
from ipaddress import IPv6Address

from struct import pack

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6 import SERVER_PORT, All_DHCP_Relay_Agents_and_Servers
from dhcpkit.ipv6.server.listeners import Listener
from dhcpkit.ipv6.utils import is_global_unicast

logger = logging.getLogger()


class MulticastInterfaceListenerFactory(ConfigElementFactory):
    """
    Factory for the implementation of a listener on a local multicast network interface
    """

    def validate_config(self):
        """
        Validate the interface information
        """

        interface_name = self._section.getSectionName()
        try:
            socket.if_nametoindex(interface_name)
        except OSError:
            raise ValueError("Interface {} not found".format(interface_name))

        interface_addresses = [IPv6Address(addr_info['addr'].split('%')[0])
                               for addr_info
                               in netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])]

        # Pick the first link-local address as reply-from if none is specified in the configuration
        if not self._section.reply_from:
            for address in interface_addresses:
                if address.is_link_local:
                    self._section.reply_from = address
                    break

            if not self._section.reply_from:
                raise ValueError("No link-local address found on interface {}".format(interface_name))

        else:
            # Validate what the user supplied
            if not self._section.reply_from.is_link_local:
                raise ValueError("The reply-from address must be a link-local address")

            if self._section.reply_from not in interface_addresses:
                raise ValueError("Cannot find reply-from address {} on interface {}".format(self._section.reply_from,
                                                                                            interface_name))

        # Pick the first global unicast address as link-address if none is specified in the configuration
        if not self._section.link_address:
            for address in interface_addresses:
                print('test {}'.format(address))
                if is_global_unicast(address):
                    print('choose {}'.format(address))
                    self._section.link_address = address
                    break

            if not self._section.link_address:
                raise ValueError("No global unicast address found on interface {}".format(interface_name))

        else:
            # Validate what the user supplied (we don't really care if it exists, it's just extra information for the
            # option handlers
            if not is_global_unicast(self._section.link_address):
                raise ValueError("The link-address must be a global unicast address")

    def create(self) -> Listener:
        """
        Create a listener of this class based on the configuration in the config section.

        :return: A listener object
        """
        mc_address = IPv6Address(All_DHCP_Relay_Agents_and_Servers)

        interface_name = self._section.getSectionName()
        interface_index = socket.if_nametoindex(interface_name)

        logger.debug("Listening for multicast requests on ".format(interface_name))

        mc_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        mc_sock.bind((str(mc_address), SERVER_PORT, 0, interface_index))

        if self._section.listen_to_self:
            mc_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)

        mc_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP,
                           pack('16sI', mc_address.packed, interface_index))

        logger.debug("  - Sending replies from {}".format(self._section.reply_from))

        ll_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ll_sock.bind((str(self._section.reply_from), SERVER_PORT, 0, interface_index))

        return Listener(interface_name=interface_name, listen_socket=mc_sock, reply_socket=ll_sock,
                        global_address=self._section.link_address)
