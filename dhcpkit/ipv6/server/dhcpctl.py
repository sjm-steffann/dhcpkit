"""
The remote control app for the server process
"""
import argparse
import logging.handlers
import socket
import sys
from argparse import ArgumentDefaultsHelpFormatter
from struct import pack

from dhcpkit.common.server.logging.config_elements import set_verbosity_logger
from typing import Iterable

logger = logging.getLogger()

# Some states
STATE_CONNECTING = 0
STATE_RESPONSE_RECEIVING = 10
STATE_RESPONSE_RECEIVED = 20
STATE_QUITTING = 30
STATE_QUIT = 40


def handle_args(args: Iterable[str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="A remote control utility that allows you to send commands to the DHCPv6 server.",
        formatter_class=ArgumentDefaultsHelpFormatter,
        epilog="Use the command 'help' to see which commands the server supports."
    )

    parser.add_argument("command", action="store",
                        help="The command to send to the server")
    parser.add_argument("-v", "--verbosity", action="count", default=0,
                        help="increase output verbosity")
    parser.add_argument("-c", "--control-socket", action="store", metavar="FILENAME",
                        default="/var/run/ipv6-dhcpd.sock",
                        help="location of domain socket for server control")

    args = parser.parse_args(args)

    return args


def main(args: Iterable[str]) -> int:
    """
    The main program loop

    :param args: Command line arguments
    :return: The program exit code
    """
    # Handle command line arguments
    args = handle_args(args)
    set_verbosity_logger(logger, args.verbosity)

    # Open socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, pack('ll', 10, 0))
    sock.connect(args.control_socket)

    state = STATE_CONNECTING
    buffer = b''
    while True:
        try:
            received = sock.recv(1024)
            buffer += received
        except OSError:
            logger.error("No response from server")
            received = b''

        # Nothing received: close connection
        if not received:
            return 1

        while buffer:
            parts = buffer.split(b'\n', maxsplit=1)
            if len(parts) < 2:
                # No full response line, continue buffering
                break

            # Store the split parts
            line = parts[0].decode('utf-8')
            buffer = parts[1]

            if state == STATE_CONNECTING:
                if not line.startswith('DHCPKit '):
                    logger.critical("Socket doesn't seem to be for DHCPKit")
                    return 1

                # Send the command
                sock.send(args.command.encode('utf-8') + b"\n")
                state = STATE_RESPONSE_RECEIVING

            elif state == STATE_RESPONSE_RECEIVING:
                if line == 'UNKNOWN':
                    logger.error("Server doesn't understand '{}'".format(args.command))
                    state = STATE_QUITTING
                elif line.startswith('OK:'):
                    print(line[3:].strip())
                    state = STATE_QUITTING
                elif line == 'OK':
                    state = STATE_QUITTING
                else:
                    print(line)

            if state == STATE_QUITTING:
                sock.send(b"quit\n")
                state = STATE_QUIT

            elif state == STATE_QUIT:
                if line == 'OK':
                    # Done
                    sock.close()
                    return 0
                else:
                    logger.error("Unexpected reply from server: {}".format(line))
                    return 1

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
