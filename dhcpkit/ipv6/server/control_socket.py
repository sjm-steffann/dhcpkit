"""
A socket to control the DHCPKit server
"""
import errno
import logging
import os
import socket
import time
from typing import List, Optional, Union

import dhcpkit

logger = logging.getLogger(__name__)


class ControlConnection:
    """
    A connection of the remote control socket
    """

    def __init__(self, sock: socket.socket):
        logger.debug("Starting new control connection")

        self.sock = sock
        self.buffer = b''
        self.last_activity = time.time()

        # Set socket options
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 100 * 1024)

        # Send welcome
        self.send("DHCPKit DHCPv6 Server {}".format(dhcpkit.__version__))

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        return self.sock.fileno()

    def get_commands(self) -> List[Union[str, None]]:
        """
        Receive data until the next newline and return the result

        :return: A list of commands
        """
        received = None
        try:
            # Receive little bits so the remote end can't overload us with control commands
            received = self.sock.recv(64)
            self.buffer += received

            # We had activity
            self.last_activity = time.time()
        except BlockingIOError:
            # Nothing to read? Fine...
            pass

        if received == b'':
            # The other end closed the connection
            logger.debug("Control connection closed without saying goodbye")
            return [None]

        # Search for commands
        commands = []
        while True:
            parts = self.buffer.split(b'\n', maxsplit=1)
            if len(parts) < 2:
                break

            # Found one, keep the remaining buffer and return the command lowercase
            self.buffer = parts[1]
            try:
                command = parts[0].decode('utf-8').lower()
            except UnicodeError:
                # Ignore non-UTF-8 input
                continue

            if command:
                commands.append(command)

        return commands

    def send(self, output: str, eol=b'\n'):
        """
        Send data over the socket

        :param output: The data to send
        :param eol: The end-of-line character
        """
        try:
            self.sock.send(output.encode('utf-8') + eol)
        except BrokenPipeError:
            # They have gone away, fine
            pass

    def close(self):
        """
        Close the socket nicely
        """
        logger.debug("Closing control connection")
        self.sock.close()

    def acknowledge(self, feedback: str = None):
        """
        Acknowledge the command
        """
        if feedback:
            self.send('OK: {}'.format(feedback))
        else:
            self.send('OK')

    def reject(self):
        """
        Reject the command
        """
        self.send('UNKNOWN')


class ControlSocket:
    """
    Remote control of the DHCPKit server
    """

    def __init__(self, socket_path: str):
        self.socket_path = socket_path

        # Create the socket and listen on it
        self.listen_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listen_socket.setblocking(False)

        try:
            logger.info("Creating control socket {}".format(socket_path))
            self.listen_socket.bind(socket_path)
        except FileNotFoundError:
            raise RuntimeError("The path to control socket {} doesn't exist".format(socket_path)) from None
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                logger.debug("Control socket at {} exists, trying to see if it's still alive".format(socket_path))

                # Is this an old socket? Try to connect
                try:
                    test_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    test_socket.connect(socket_path)
                except OSError as e2:
                    if e2.errno == errno.ECONNREFUSED:
                        # Nobody listening, just delete it and try again
                        logger.debug("Replacing old control socket {}".format(socket_path))
                        os.unlink(socket_path)
                        self.listen_socket.bind(socket_path)
                    elif e2.errno == errno.ENOTSOCK:
                        raise RuntimeError("Control socket {} is unusable".format(socket_path)) from None

        if not self.listen_socket.getsockname():
            raise RuntimeError("Cannot create control socket {}".format(socket_path)) from None

        self.listen_socket.listen(32)

    def close(self):
        """
        Close the socket nicely
        """
        self.listen_socket.close()

    def fileno(self) -> int:
        """
        The fileno of the listening socket, so this object can be used by select()

        :return: The file descriptor
        """
        return self.listen_socket.fileno()

    def accept(self) -> Optional[ControlConnection]:
        """
        Accept a new connection

        :return: The new connection
        """
        try:
            sock = self.listen_socket.accept()[0]
            return ControlConnection(sock)
        except OSError:
            logger.debug("Control connection broken after connecting, ignoring")
            return None
