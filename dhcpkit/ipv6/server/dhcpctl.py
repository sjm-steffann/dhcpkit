"""
The remote control app for the server process
"""
import argparse
import logging.handlers
import socket
import sys
from argparse import ArgumentDefaultsHelpFormatter
from struct import pack

from typing import Iterable, Optional

from dhcpkit.common.logging.verbosity import set_verbosity_logger

logger = logging.getLogger()


class ControlClientError(Exception):
    """
    Base class for DHCPKit Control Client errors
    """


class UnknownCommandError(ControlClientError):
    """
    The server doesn't understand the command we sent
    """


class WrongServerError(ControlClientError):
    """
    The socket we connected to doesn't seem to be a DHCPKit server
    """


class CommunicationError(ControlClientError):
    """
    There was a problem communicating
    """


class DHCPKitControlClient:
    """
    A class for communicating with a DHCPKit DHCPv6 server
    """

    def __init__(self, control_socket: str):
        # Open socket
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, pack('ll', 10, 0))
        self.sock.connect(control_socket)

        # Create a buffer for receiving data into
        self.buffer = b''

        # Make sure we are actually connected
        line = self.receive_line()
        if not line.startswith('DHCPKit '):
            raise WrongServerError("Socket doesn't seem to be for DHCPKit")

    def receive_line(self, optional: bool=False) -> Optional[str]:
        """
        Receive one line of output from the server

        :param optional: Whether we care about this command being properly executed
        :return: The received line
        """
        # Stop if the socket is gone
        if not self.sock:
            if optional:
                return None
            else:
                raise CommunicationError("Reading from a closed connection")

        while True:
            parts = self.buffer.split(b'\n', maxsplit=1)
            if len(parts) == 2:
                # There is a full line in the buffer, return it
                self.buffer = parts[1]
                return parts[0].decode('utf-8')

            # No full line in the buffer, try to get some more data
            try:
                received = self.sock.recv(1024)
                self.buffer += received
            except OSError:
                if optional:
                    received = b''
                else:
                    raise CommunicationError("No response from server")

            # Nothing received: close connection
            if not received:
                self.sock.close()
                self.sock = None
                return None

    def send_command(self, command: str, optional: bool=False):
        """
        Send a command to the server

        :param command: The command
        :param optional: Whether we care about this command being properly executed
        """
        # Stop if the socket is gone
        if not self.sock:
            if optional:
                return
            else:
                raise CommunicationError("Writing to a closed connection")

        self.sock.send(command.encode('utf-8') + b"\n")

    def execute_command(self, command: str, optional: bool=False) -> Iterable[str]:
        """
        Send a command and parse the response

        :param command: The command
        :param optional: Whether we care about this command being properly executed
        :return: The output
        """
        self.send_command(command, optional=optional)

        while True:
            line = self.receive_line(optional=optional)
            if line is None:
                # No more data, the connection is closed
                return ''

            if line == 'UNKNOWN':
                raise UnknownCommandError("Server doesn't understand '{}'".format(command))

            elif line.startswith('OK:'):
                # Return the information after the OK: tag
                yield line[3:]
                return ''

            elif line == 'OK':
                return ''

            else:
                yield line


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


def main(args: Iterable[str]):
    """
    The main program loop

    :param args: Command line arguments
    :return: The program exit code
    """
    # Handle command line arguments
    args = handle_args(args)
    set_verbosity_logger(logger, args.verbosity)

    conn = DHCPKitControlClient(args.control_socket)
    output = conn.execute_command(args.command)
    for line in output:
        print(line)

    try:
        output = list(conn.execute_command('quit', optional=True))
        if output:
            raise CommunicationError("Unexpected reply from server: {}".format(output[0]))
    except BrokenPipeError:
        pass


def run() -> int:
    """
    Run the main program and handle exceptions

    :return: The program exit code
    """
    try:
        # Run the server
        main(sys.argv[1:])
        return 0
    except Exception as e:
        logger.critical("Error: {}".format(e))
        return 1


if __name__ == '__main__':
    sys.exit(run())
