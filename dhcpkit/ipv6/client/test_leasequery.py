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

from dhcpkit.common.logging.verbosity import set_verbosity_logger
from dhcpkit.ipv6 import All_DHCP_Relay_Agents_and_Servers, CLIENT_PORT, SERVER_PORT
from dhcpkit.ipv6.duids import EnterpriseDUID, LinkLayerDUID, LinkLayerTimeDUID
from dhcpkit.ipv6.extensions.leasequery import LQQueryOption, LeasequeryMessage
from dhcpkit.ipv6.messages import Message
from dhcpkit.ipv6.options import ClientIdOption
from typing import Iterable

logger = logging.getLogger()

# Query types
query_types = {
    'address': 1,
    'client_id': 2
}


def handle_args(args: Iterable[str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="A command line client to test a DHCPv6 server's Leasequery implementation",
        formatter_class=ArgumentDefaultsHelpFormatter,
        epilog="Use the command 'help' to see which commands this tool supports."
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

    parser.add_argument("-v", "--verbosity", action="count", default=2,
                        help="increase output verbosity")
    parser.add_argument("-s", "--server", action="store", metavar="ADDR", type=IPv6Address,
                        default=All_DHCP_Relay_Agents_and_Servers,
                        help="server address to send message to")
    parser.add_argument("-i", "--interface", action="store", metavar="INTF", choices=interface_names,
                        default=default_interface_name,
                        help="interface to send multicast messages on")

    parser.add_argument("-D", "--duid", action="store",
                        default="enterprise:40208:TestClient",
                        help="client DUID")

    parser.add_argument("query_type", action="store", choices=query_types.keys(),
                        help="query type")

    parser.add_argument("-L", "--link-address", action="store", type=IPv6Address,
                        default="::",
                        help="link address")

    args = parser.parse_args(args)

    return args


def main(args: Iterable[str]) -> int:
    """
    The main program

    :param args: Command line arguments
    :return: The program exit code
    """
    # Handle command line arguments
    args = handle_args(args)
    set_verbosity_logger(logger, args.verbosity)

    # Check permission
    if os.getuid() != 0:
        raise RuntimeError("This tool needs to be run as root")

    # Build DUID
    duid_parts = args.duid.split(':')
    duid_type = duid_parts[0]
    if duid_type == 'enterprise':
        if len(duid_parts) == 3:
            hardware_type = int(duid_parts[1], 10)
            if duid_parts[2][:2] == '0x':
                identifier = bytes.fromhex(duid_parts[2][2:])
            else:
                identifier = duid_parts[2].encode('utf-8')
            duid = EnterpriseDUID(hardware_type, identifier)
        else:
            logger.critical("Enterprise DUIDs must have format 'enterprise:<enterprise-nr>:<identifier>'")
            return 1

    elif duid_type == 'linklayer':
        if len(duid_parts) == 3:
            hardware_type = int(duid_parts[1], 10)
            address = bytes.fromhex(duid_parts[2])
            duid = LinkLayerDUID(hardware_type, address)
        else:
            logger.critical("Enterprise DUIDs must have format 'linklayer:<hardware-type>:<address-hex>'")
            return 1

    elif duid_type == 'linklayer-time':
        if len(duid_parts) == 4:
            hardware_type = int(duid_parts[1], 10)
            timestamp = int(duid_parts[2], 10)
            address = bytes.fromhex(duid_parts[3])
            duid = LinkLayerTimeDUID(hardware_type, timestamp, address)
        else:
            logger.critical("Enterprise DUIDs must have format 'linklayer-time:<hardware-type>:<time>:<address-hex>'")
            return 1

    else:
        logger.critical("Unknown DUID type: {}".format(duid_type))
        return 1

    # Create client socket
    if_index = socket.if_nametoindex(args.interface)
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client_socket.bind(('::', CLIENT_PORT, 0, if_index))

    # Generate the outgoing message
    transaction_id = random.getrandbits(24).to_bytes(3, 'big')
    message_out = LeasequeryMessage(transaction_id, [
        ClientIdOption(duid),
        LQQueryOption(query_types[args.query_type], args.link_address, [])
    ])
    packet_out = message_out.save()

    client_socket.sendto(packet_out, (str(args.server), SERVER_PORT, 0, if_index))

    logger.info("Sent:\n{}".format(message_out))

    # Wait for responses
    wait_for_multiple = args.server.is_multicast

    start = time.time()
    deadline = start + 2

    received = 0

    while time.time() < deadline:
        client_socket.settimeout(deadline - time.time())
        try:
            packet_in, sender = client_socket.recvfrom(65535)
            message_length, message_in = Message.parse(packet_in)
            received += 1

            logger.info("Received:\n{}".format(message_in))

            if not wait_for_multiple:
                break
        except socket.timeout:
            pass

    logger.info(gettext.ngettext("{} response received",
                                 "{} responses received",
                                 received).format(received))


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
