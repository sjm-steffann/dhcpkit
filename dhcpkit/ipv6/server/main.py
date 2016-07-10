"""
The main server process
"""
import argparse
import atexit
import fcntl
import grp
import logging.handlers
import multiprocessing
import multiprocessing.queues
import os
import pwd
import selectors
import signal
import sys
import time
import types
from multiprocessing import forkserver
from multiprocessing.util import get_logger
from urllib.parse import urlparse

from ZConfig import ConfigurationSyntaxError, DataConversionError
from typing import Tuple, Iterable, Optional

import dhcpkit
from dhcpkit.common.server.logging.config_elements import set_verbosity_logger
from dhcpkit.ipv6.server import config_parser, queue_logger
from dhcpkit.ipv6.server.config_elements import MainConfig
from dhcpkit.ipv6.server.listeners import Listener, OutgoingPacketBundle
from dhcpkit.ipv6.server.worker import setup_worker, handle_message

logger = logging.getLogger()

logging_thread = None


@atexit.register
def stop_logging_thread():
    """
    Stop the logging thread from the global
    """
    global logging_thread
    if logging_thread:
        logging_thread.stop()


def handle_args(args: Iterable[str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="A flexible IPv6 DHCP server written in Python.",
    )

    parser.add_argument("config", help="the configuration file")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")
    parser.add_argument("-p", "--pidfile", action="store", help="save the server's PID to this file")

    args = parser.parse_args(args)

    return args


def drop_privileges(user: pwd.struct_passwd, group: grp.struct_group, permanent: bool = True):
    """
    Drop root privileges and change to something more safe.

    :param user: The tuple with user info
    :param group: The tuple with group info
    :param permanent: Whether we want to drop just the euid (temporary), or all uids (permanent)
    """
    # Restore euid=0 if we have previously changed it
    if os.geteuid() != 0 and os.getuid() == 0:
        restore_privileges()

    if os.geteuid() != 0:
        raise RuntimeError("Not running as root: cannot change uid/gid to {}/{}".format(user.pw_name, group.gr_name))

    # Remove group privileges
    os.setgroups([])

    if permanent:
        os.setgid(group.gr_gid)
        os.setuid(user.pw_uid)
    else:
        os.setegid(group.gr_gid)
        os.seteuid(user.pw_uid)

    # Ensure a very conservative umask
    os.umask(0o077)

    if permanent:
        logger.debug("Permanently dropped privileges to {}/{}".format(user.pw_name, group.gr_name))
    else:
        logger.debug("Dropped privileges to {}/{}".format(user.pw_name, group.gr_name))


def restore_privileges():
    """
    Restore root privileges
    """
    if os.getuid() != 0:
        raise RuntimeError("Privileges have been permanently dropped, cannot restore them")

    os.seteuid(0)
    os.setegid(0)

    logger.debug("Restored root privileges")


def create_pidfile(args, config: MainConfig) -> Optional[str]:
    """
    Create a PID file when configured to do so.

    :param args: The command line arguments
    :param config: The server configuration
    :return: The name of the created PID file
    """
    # Create the PID file while we are root
    if args.pidfile:
        pid_filename = os.path.realpath(args.pidfile)
    elif config.pid_file:
        pid_filename = os.path.realpath(config.pid_file)
    else:
        pid_filename = None

    if pid_filename:
        # A different umask for here, drop_privileges will overrule it again later
        old_umask = os.umask(0o022)
        with open(pid_filename, 'w') as pidfile:
            logger.info("Writing PID-file {}".format(pid_filename))
            pidfile.write("{}\n".format(os.getpid()))
        os.umask(old_umask)

    return pid_filename


def create_handler_callbacks(listening_socket: Listener, message_id: str) -> Tuple[types.FunctionType,
                                                                                   types.FunctionType]:
    """
    Create a callback for the handler method that still knows the listening socket and the sender

    :param listening_socket: The listening socket to remember
    :param message_id: An identifier for logging to correlate log-messages
    :return: A callback function with the listening socket and sender enclosed
    """

    def callback(reply):
        """
        A callback that handles the result of a handler

        :param reply: The result from the handler
        """
        try:
            if reply is None:
                # No reply: we're done with this request
                return

            if not isinstance(reply, OutgoingPacketBundle):
                logger.error("{}: Handler returned invalid result, not sending a reply".format(message_id))
                return

            try:
                listening_socket.send_reply(reply)
            except ValueError as e:
                logger.error("{}: Handler returned invalid message: {}".format(message_id, e))
                return

        except Exception as e:
            # Catch-all exception handler
            logger.exception("{}: Caught unexpected exception {!r}".format(message_id, e))

    def error_callback(e: Exception):
        """
        Log an error about this exception

        :param e: The exception from the worker
        """
        logger.error("{}: Caught unexpected exception {!r}".format(message_id, e))

    return callback, error_callback


def main(args: Iterable[str]) -> int:
    """
    The main program loop

    :param args: Command line arguments
    :return: The program exit code
    """
    # Handle command line arguments
    args = handle_args(args)
    set_verbosity_logger(logger, args.verbosity)

    # Go to the working directory
    config_file = os.path.realpath(args.config)
    os.chdir(os.path.dirname(config_file))

    try:
        # Read the configuration
        config = config_parser.load_config(config_file)
    except (ConfigurationSyntaxError, DataConversionError) as e:
        # Make the config exceptions a bit more readable
        msg = e.message
        if e.lineno and e.lineno != -1:
            msg += ' on line {}'.format(e.lineno)
        if e.url:
            parts = urlparse(e.url)
            msg += ' in {}'.format(parts.path)
        logger.critical(msg)
        return 1
    except ValueError as e:
        logger.critical(e)
        return 1

    # Immediately drop privileges in a non-permanent way so we create logs with the correct owner
    drop_privileges(config.user, config.group, permanent=False)

    # Trigger the forkserver at this point, with dropped privileges, and ignoring KeyboardInterrupt
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    multiprocessing.set_start_method('forkserver')
    forkserver.ensure_running()

    # Initialise the logger
    config.logging.configure(logger, verbosity=args.verbosity)
    logger.info("Starting Python DHCPv6 server v{}".format(dhcpkit.__version__))

    # Create our selector
    sel = selectors.DefaultSelector()

    # Convert signals to messages on a pipe
    signal_r, signal_w = os.pipe()
    flags = fcntl.fcntl(signal_w, fcntl.F_GETFL, 0)
    flags = flags | os.O_NONBLOCK
    fcntl.fcntl(signal_w, fcntl.F_SETFL, flags)
    signal.set_wakeup_fd(signal_w)
    sel.register(signal_r, selectors.EVENT_READ)

    # Ignore normal signal handling by attaching dummy handlers (SIG_IGN will not put messages on the pipe)
    signal.signal(signal.SIGINT, lambda signum, frame: None)
    signal.signal(signal.SIGTERM, lambda signum, frame: None)
    signal.signal(signal.SIGHUP, lambda signum, frame: None)
    signal.signal(signal.SIGINFO, lambda signum, frame: None)

    # Excessive exception catcher
    exception_history = []

    # Some stats
    message_count = 0

    # Create a queue for our children to log to
    logging_queue = multiprocessing.Queue()

    # This will be where we store the new config after a reload
    listeners = []
    stopping = False
    while not stopping:
        # Safety first: assume we want to quit when we break the inner loop unless told otherwise
        stopping = True

        # Initialise the logger again
        lowest_log_level = config.logging.configure(logger, verbosity=args.verbosity)

        # Enable multiprocessing logging, mostly useful for development
        mp_logger = get_logger()
        mp_logger.propagate = config.logging.log_multiprocessing

        global logging_thread
        if logging_thread:
            logging_thread.stop()
        logging_thread = queue_logger.QueueLevelListener(logging_queue, *logger.handlers)
        logging_thread.start()

        # Restore our privileges while we write the PID file and open network listeners
        restore_privileges()

        # Open the network listeners
        old_listeners = listeners
        listeners = []
        for listener_factory in config.listener_factories:
            # Create new listener while trying to re-use existing sockets
            listeners.append(listener_factory(old_listeners + listeners))

        # Write the PID file
        pid_filename = create_pidfile(args=args, config=config)

        # And Drop privileges again
        drop_privileges(config.user, config.group, permanent=False)

        # Remove any file descriptors from the previous config
        for fd, key in list(sel.get_map().items()):
            # Don't remove our signal handling pipe and still existing listeners
            if key.fileobj == signal_r or key.fileobj in listeners:
                continue

            # Seems we don't need this one anymore
            sel.unregister(key.fileobj)

        # Collect all the file descriptors we want to listen to
        existing_listeners = [key.fileobj for key in sel.get_map().values()]
        for listener in listeners:
            if listener not in existing_listeners:
                sel.register(listener, selectors.EVENT_READ)

        # Configuration tree
        message_handler = config.create_message_handler()

        # Start worker processes
        with multiprocessing.Pool(processes=config.workers,
                                  initializer=setup_worker,
                                  initargs=(message_handler, logging_queue, lowest_log_level)) as pool:

            logger.info("Python DHCPv6 server is ready to handle requests")

            running = True
            while running:
                # noinspection PyBroadException
                try:
                    events = sel.select()
                    for key, mask in events:
                        # Handle signal notifications
                        if key.fileobj == signal_r:
                            signal_nr = os.read(signal_r, 1)
                            if signal_nr[0] in (signal.SIGHUP,):
                                # SIGHUP tells the server to reload
                                try:
                                    # Read the new configuration
                                    config = config_parser.load_config(config_file)

                                    running = False
                                    stopping = False

                                    logger.info("DHCPv6 server restarting after configuration change")

                                    break

                                except (ConfigurationSyntaxError, DataConversionError) as e:
                                    # Make the config exceptions a bit more readable
                                    msg = "Not reloading: " + str(e.message)
                                    if e.lineno and e.lineno != -1:
                                        msg += ' on line {}'.format(e.lineno)
                                    if e.url:
                                        parts = urlparse(e.url)
                                        msg += ' in {}'.format(parts.path)
                                    logger.critical(msg)
                                    return 1
                                except ValueError as e:
                                    logger.critical("Not reloading: " + str(e))
                                    return 1

                            elif signal_nr[0] in (signal.SIGINT, signal.SIGTERM):
                                logger.debug("Received termination request")

                                running = False
                                stopping = True
                                break

                            elif signal_nr[0] in (signal.SIGINFO,):
                                logger.info("Server has processed {} messages".format(message_count))

                            # Unknown signal: ignore
                            continue

                        elif isinstance(key.fileobj, Listener):
                            packet = key.fileobj.recv_request()

                            # Update stats
                            message_count += 1

                            # Create the callback
                            callback, error_callback = create_handler_callbacks(key.fileobj, packet.message_id)

                            # Dispatch
                            pool.apply_async(handle_message, args=(packet,),
                                             callback=callback, error_callback=error_callback)

                except Exception as e:
                    # Catch-all exception handler
                    logger.exception("Caught unexpected exception {!r}".format(e))

                    now = time.monotonic()

                    # Add new exception time to the history
                    exception_history.append(now)

                    # Remove exceptions outside the window from the history
                    cutoff = now - config.exception_window
                    while exception_history and exception_history[0] < cutoff:
                        exception_history.pop(0)

                    # Did we receive too many exceptions shortly after each other?
                    if len(exception_history) > config.max_exceptions:
                        logger.critical("Received more than {} exceptions in {} seconds, "
                                        "exiting".format(config.max_exceptions, config.exception_window))
                        running = False
                        stopping = True

            pool.close()
            pool.join()

        # Regain root so we can delete the PID file
        restore_privileges()
        try:
            if pid_filename:
                os.unlink(pid_filename)
                logger.info("Removing PID-file {}".format(pid_filename))
        except OSError:
            pass

    logger.info("Shutting down Python DHCPv6 server v{}".format(dhcpkit.__version__))

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
