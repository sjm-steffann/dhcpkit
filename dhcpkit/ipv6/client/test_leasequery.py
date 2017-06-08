"""
A simple DHCPv6 client to send/receive messages from a DHCPv6 server
"""
import argparse
import gettext
import logging.handlers
import netifaces
import os
import random
import socket
import sys
import time
from argparse import ArgumentDefaultsHelpFormatter
from ipaddress import IPv6Address
from struct import pack, unpack
from typing import Iterable, Tuple

from dhcpkit.common.logging.verbosity import set_verbosity_logger
from dhcpkit.ipv6 import All_DHCP_Relay_Agents_and_Servers, CLIENT_PORT, SERVER_PORT
from dhcpkit.ipv6.duids import DUID, EnterpriseDUID, LinkLayerDUID, LinkLayerTimeDUID
from dhcpkit.ipv6.extensions.bulk_leasequery import LeasequeryDoneMessage, QUERY_BY_LINK_ADDRESS, QUERY_BY_RELAY_ID, \
    QUERY_BY_REMOTE_ID, RelayIdOption
from dhcpkit.ipv6.extensions.leasequery import ClientDataOption, LQQueryOption, LeasequeryMessage, \
    LeasequeryReplyMessage, OPTION_LQ_RELAY_DATA, QUERY_BY_ADDRESS, QUERY_BY_CLIENT_ID
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.messages import Message
from dhcpkit.ipv6.options import ClientIdOption, IAAddressOption, OptionRequestOption

logger = logging.getLogger()


def create_client_address_query(options) -> LQQueryOption:
    """
    Create query option for address query.

    :param options: Options from the main argument parser
    :return: The Leasequery
    """
    return LQQueryOption(QUERY_BY_ADDRESS, options.link_address, [
        IAAddressOption(options.address)
    ])


def create_client_id_query(options) -> LQQueryOption:
    """
    Create query option for client-id query.

    :param options: Options from the main argument parser
    :return: The Leasequery
    """
    return LQQueryOption(QUERY_BY_CLIENT_ID, options.link_address, [
        ClientIdOption(parse_duid(options.duid))
    ])


def create_relay_id_query(options) -> LQQueryOption:
    """
    Create query option for relay-id query.

    :param options: Options from the main argument parser
    :return: The Leasequery
    """
    return LQQueryOption(QUERY_BY_RELAY_ID, options.link_address, [
        RelayIdOption(parse_duid(options.duid))
    ])


def create_link_address_query(options) -> LQQueryOption:
    """
    Create query option for link-address query.

    :param options: Options from the main argument parser
    :return: The Leasequery
    """
    return LQQueryOption(QUERY_BY_LINK_ADDRESS, options.link_address)


def create_remote_id_query(options) -> LQQueryOption:
    """
    Create query option for remote-id query.

    :param options: Options from the main argument parser
    :return: The Leasequery
    """
    return LQQueryOption(QUERY_BY_REMOTE_ID, options.link_address, [
        RemoteIdOption(int(options.enterprise_nr), bytes.fromhex(options.remote_id))
    ])


def handle_args(args: Iterable[str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="A command line client to test a DHCPv6 server's Leasequery implementation",
        formatter_class=ArgumentDefaultsHelpFormatter
    )

    # Find usable interfaces
    interface_names = []
    for interface_name in netifaces.interfaces():
        addresses = netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])

        # Skip loopback
        if any([IPv6Address(address['addr'].split('%')[0]).is_loopback for address in addresses]):
            continue

        if any([IPv6Address(address['addr'].split('%')[0]).is_link_local for address in addresses]):
            # This interface has a link-local address, it'll do
            interface_names.append(interface_name)

    # First one is the default
    default_interface_name = interface_names[0] if interface_names else None

    # Common options
    parser.add_argument("-v", "--verbosity", action="count", default=2,
                        help="increase output verbosity")
    parser.add_argument("-s", "--server", action="store", metavar="ADDR", type=IPv6Address,
                        default=All_DHCP_Relay_Agents_and_Servers.compressed,
                        help="server address to send message to")
    parser.add_argument("-i", "--interface", action="store", metavar="INTF", choices=interface_names,
                        default=default_interface_name,
                        help="interface to send multicast messages on")
    parser.add_argument("-t", "--tcp", action="store_true",
                        help="Use bulk leasequery over TCP")
    parser.add_argument("-L", "--link-address", action="store", type=IPv6Address,
                        default="::",
                        help="link address")
    parser.add_argument("-R", "--relay-data", action="store_true",
                        help="Request the relay data")

    subparsers = parser.add_subparsers(title="Query types", dest="query-type",
                                       description="Specify what kind of query you want to send to the DHCPv6 server")
    subparsers.required = True

    # Query by client address
    parser_query_client_address = subparsers.add_parser('client-address',
                                                        help='query by client address')
    parser_query_client_address.add_argument("address", action="store", type=IPv6Address,
                                             help="client address")
    parser_query_client_address.set_defaults(create=create_client_address_query)

    # Query by client ID
    parser_query_client_id = subparsers.add_parser('client-id',
                                                   help='query by client id')
    parser_query_client_id.add_argument("duid", action="store",
                                        help="client DUID")
    parser_query_client_id.set_defaults(create=create_client_id_query)

    # Query by relay ID
    parser_query_relay_id = subparsers.add_parser('relay-id',
                                                  help='query by relay id')
    parser_query_relay_id.add_argument("duid", action="store",
                                       help="client DUID")
    parser_query_relay_id.set_defaults(create=create_relay_id_query)

    # Query by client ID
    parser_query_link_address = subparsers.add_parser('link-address',
                                                      help='query by link address')
    parser_query_link_address.set_defaults(create=create_link_address_query)

    # Query by remote ID
    parser_query_remote_id = subparsers.add_parser('remote-id',
                                                   help='query by remote id')
    parser_query_remote_id.add_argument("enterprise-nr", action="store",
                                        help="Enterprise number")
    parser_query_remote_id.add_argument("remote-id", action="store",
                                        help="Remote ID")
    parser_query_remote_id.set_defaults(create=create_remote_id_query)

    # Parse
    options = parser.parse_args(args)

    return options


def parse_duid(duid_str: str) -> DUID:
    """
    Parse a string representing a DUID into a real DUID

    :param duid_str: The string representation
    :return: The DUID object
    """
    duid_parts = duid_str.split(':')
    duid_type = duid_parts[0]
    if duid_type == 'enterprise':
        if len(duid_parts) == 3:
            hardware_type = int(duid_parts[1], 10)
            if duid_parts[2][:2] == '0x':
                identifier = bytes.fromhex(duid_parts[2][2:])
            else:
                identifier = duid_parts[2].encode('utf-8')
            return EnterpriseDUID(hardware_type, identifier)
        else:
            logger.critical("Enterprise DUIDs must have format 'enterprise:<enterprise-nr>:<identifier>'")
            raise ValueError

    elif duid_type == 'linklayer':
        if len(duid_parts) == 3:
            hardware_type = int(duid_parts[1], 10)
            address = bytes.fromhex(duid_parts[2])
            return LinkLayerDUID(hardware_type, address)
        else:
            logger.critical("Link Layer DUIDs must have format 'linklayer:<hardware-type>:<address-hex>'")
            raise ValueError

    elif duid_type == 'linklayer-time':
        if len(duid_parts) == 4:
            hardware_type = int(duid_parts[1], 10)
            timestamp = int(duid_parts[2], 10)
            address = bytes.fromhex(duid_parts[3])
            return LinkLayerTimeDUID(hardware_type, timestamp, address)
        else:
            logger.critical("Link Layer + Time DUIDs must have format "
                            "'linklayer-time:<hardware-type>:<time>:<address-hex>'")
            raise ValueError

    else:
        logger.critical("Unknown DUID type: {}".format(duid_type))
        raise ValueError


class ClientSocket:
    """
    Base class for client sockets
    """

    def send(self, message: Message) -> IPv6Address:
        """
        Send a DHCPv6 message

        :param message: The message
        """
        raise NotImplementedError

    def recv(self) -> Tuple[IPv6Address, Message]:
        """
        Receive a DHCPv6 message

        :return: The message
        """
        raise NotImplementedError

    def set_timeout(self, timeout: float):
        """
        Set the timeout on the socket

        :param timeout: Timeout in seconds
        """
        raise NotImplementedError


class UDPClientSocket(ClientSocket):
    """
    Client socket for UDP connections
    """

    def __init__(self, options):
        self.options = options

        self.if_index = socket.if_nametoindex(self.options.interface)
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.socket.bind(('::', CLIENT_PORT, 0, self.if_index))

    def send(self, message: Message) -> IPv6Address:
        """
        Send a DHCPv6 message

        :param message: The message
        """
        packet = message.save()
        self.socket.sendto(packet, (str(self.options.server), SERVER_PORT, 0, self.if_index))
        return self.options.server

    def recv(self) -> Tuple[IPv6Address, Message]:
        """
        Receive a DHCPv6 message

        :return: The message
        """
        packet, sender = self.socket.recvfrom(65535)
        message_length, message = Message.parse(packet)
        return IPv6Address(sender[0].split('%')[0]), message

    def set_timeout(self, timeout: float):
        """
        Set the timeout on the socket

        :param timeout: Timeout in seconds
        """
        self.socket.settimeout(timeout)


class TCPClientSocket(ClientSocket):
    """
    Client socket for TCP connections
    """

    def __init__(self, options):
        self.options = options

        if self.options.server.is_multicast:
            raise RuntimeError("You must specify a unicast server address when using bulk leasequery")

        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.socket.connect((str(options.server), SERVER_PORT))

    def send(self, message: Message) -> IPv6Address:
        """
        Send a DHCPv6 message

        :param message: The message
        """
        packet = message.save()
        self.socket.sendall(pack("!H", len(packet)) + packet)
        return self.options.server

    def recv(self) -> Tuple[IPv6Address, Message]:
        """
        Receive a DHCPv6 message

        :return: The message
        """
        # Receive message length
        packet = b''
        while len(packet) < 2:
            packet += self.socket.recv(2 - len(packet))
        message_length = unpack('!H', packet)[0]

        # Receive message
        packet = b''
        while len(packet) < message_length:
            packet += self.socket.recv(message_length - len(packet))
        read_length, message = Message.parse(packet)

        return self.options.server, message

    def set_timeout(self, timeout: float):
        """
        Set the timeout on the socket

        :param timeout: Timeout in seconds
        """
        self.socket.settimeout(timeout)


def main(args: Iterable[str]) -> int:
    """
    The main program

    :param args: Command line arguments
    :return: The program exit code
    """
    # Handle command line arguments
    options = handle_args(args)
    set_verbosity_logger(logger, options.verbosity)

    query = options.create(options)

    # Add ORO for relay data
    if options.relay_data:
        query.options.append(OptionRequestOption([OPTION_LQ_RELAY_DATA]))

    # Generate the outgoing message
    transaction_id = random.getrandbits(24).to_bytes(3, 'big')
    message_out = LeasequeryMessage(transaction_id, [
        ClientIdOption(EnterpriseDUID(40208, b'LeaseQueryTester')),
        query
    ])

    # Create client socket
    if options.tcp:
        client = TCPClientSocket(options)
    else:
        # Check permission
        if os.getuid() != 0:
            raise RuntimeError("This tool needs to be run as root")

        client = UDPClientSocket(options)

    destination = client.send(message_out)
    logger.info("Sent to {}:\n{}".format(destination, message_out))

    # Wait for responses
    wait_for_multiple = options.server.is_multicast or options.tcp

    start = time.time()
    deadline = start + 3

    received = 0

    while time.time() < deadline:
        client.set_timeout(deadline - time.time())
        try:
            sender, message_in = client.recv()
            received += 1

            logger.info("Received from {}:\n{}".format(sender, message_in))

            if options.tcp:
                # Check bulk leasequery ending
                if isinstance(message_in, LeasequeryReplyMessage):
                    if not message_in.get_option_of_type(ClientDataOption):
                        # Reply without data, the end
                        break

                if isinstance(message_in, LeasequeryDoneMessage):
                    break

            if not wait_for_multiple:
                break
        except socket.timeout:
            pass

    logger.info(gettext.ngettext("{} response received",
                                 "{} responses received",
                                 received).format(received))

    return 0


def run() -> int:
    """
    Run the main program and handle exceptions

    :return: The program exit code
    """
    try:
        # Run the server
        return main(sys.argv[1:])
    except Exception as e:
        logger.critical("Error: {}".format(e))
        return 1


if __name__ == '__main__':
    sys.exit(run())
