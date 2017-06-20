"""
The main server process
"""
import argparse
import atexit
import fcntl
import json
import logging.handlers
import multiprocessing
import multiprocessing.queues
import os
import pwd
import selectors
import signal
import sys
import time
from multiprocessing import forkserver
from multiprocessing.util import get_logger
from urllib.parse import urlparse

import dhcpkit
from ZConfig import ConfigurationSyntaxError, DataConversionError
from dhcpkit.common.privileges import drop_privileges, restore_privileges
from dhcpkit.common.server.logging.config_elements import set_verbosity_logger
from dhcpkit.ipv6.server import config_parser, queue_logger
from dhcpkit.ipv6.server.config_elements import MainConfig
from dhcpkit.ipv6.server.control_socket import ControlConnection, ControlSocket
from dhcpkit.ipv6.server.listeners import ClosedListener, IgnoreMessage, Listener, ListenerCreator
from dhcpkit.ipv6.server.nonblocking_pool import NonBlockingPool
from dhcpkit.ipv6.server.queue_logger import WorkerQueueHandler
from dhcpkit.ipv6.server.statistics import ServerStatistics
from dhcpkit.ipv6.server.worker import handle_message, setup_worker
from typing import Iterable, Optional

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


def error_callback(exception):
    """
    Show exceptions that occur while handling messages

    :param exception: The exception that occurred
    """
    message = "Unexpected exception while delegating handling to worker {}".format(exception)
    if exception.__cause__:
        message += ":" + str(exception.__cause__)

    logger.error(message)


def handle_args(args: Iterable[str]):
    """
    Handle the command line arguments.

    :param args: Command line arguments
    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="A flexible IPv6 DHCP server written in Python.",
    )

    parser.add_argument("config",
                        help="the configuration file")
    parser.add_argument("-v", "--verbosity", action="count", default=0,
                        help="increase output verbosity")
    parser.add_argument("-c", "--control-socket", action="store", metavar="FILENAME",
                        help="location of domain socket for server control")
    parser.add_argument("-p", "--pidfile", action="store",
                        help="save the server's PID to this file")

    args = parser.parse_args(args)

    return args


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
        # A different umask for here
        old_umask = os.umask(0o022)
        try:
            os.unlink(pid_filename)
        except OSError:
            pass

        with open(pid_filename, 'w') as pidfile:
            logger.info("Writing PID-file {}".format(pid_filename))
            pidfile.write("{}\n".format(os.getpid()))
        os.umask(old_umask)

    return pid_filename


def create_control_socket(args, config: MainConfig) -> ControlSocket:
    """
    Create a control socket when configured to do so.

    :param args: The command line arguments
    :param config: The server configuration
    :return: The name of the created control socket
    """
    if args.control_socket:
        socket_filename = os.path.realpath(args.control_socket)
    elif config.control_socket:
        socket_filename = os.path.realpath(config.control_socket)
    else:
        socket_filename = None

    if socket_filename:
        # Default to the user that started the server
        control_socket_user = config.control_socket_user if config.control_socket_user else pwd.getpwuid(os.getuid())
        uid = control_socket_user.pw_uid
        gid = config.control_socket_group.gr_gid if config.control_socket_group else control_socket_user.pw_gid

        # A different umask for here
        old_umask = os.umask(0o117)
        control_socket = ControlSocket(socket_filename)

        # Change owner if necessary
        if uid != os.geteuid() or gid != os.getegid():
            os.chown(socket_filename, uid, gid)

        os.umask(old_umask)
        return control_socket


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
    signal.signal(signal.SIGUSR1, lambda signum, frame: None)

    # Excessive exception catcher
    exception_history = []

    # Some stats
    message_count = 0

    # Create a queue for our children to log to
    logging_queue = multiprocessing.Queue()

    statistics = ServerStatistics()
    listeners = []
    control_socket = None
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

        # Use the logging queue in the main process as well so messages don't get out of order
        logging_handler = WorkerQueueHandler(logging_queue)
        logging_handler.setLevel(lowest_log_level)
        logger.handlers = [logging_handler]

        # Restore our privileges while we write the PID file and open network listeners
        restore_privileges()

        # Open the network listeners
        old_listeners = listeners
        listeners = []
        for listener_factory in config.listener_factories:
            # Create new listener while trying to re-use existing sockets
            listeners.append(listener_factory(old_listeners + listeners))

        # Forget old listeners
        del old_listeners

        # Write the PID file
        pid_filename = create_pidfile(args=args, config=config)

        # Create a control socket
        if control_socket:
            sel.unregister(control_socket)
            control_socket.close()

        control_socket = create_control_socket(args=args, config=config)
        if control_socket:
            sel.register(control_socket, selectors.EVENT_READ)

        # And Drop privileges again
        drop_privileges(config.user, config.group, permanent=False)

        # Remove any file descriptors from the previous config
        for fd, key in list(sel.get_map().items()):
            # Don't remove our signal handling pipe, control socket, still existing listeners and control connections
            if key.fileobj is signal_r \
                    or (control_socket and key.fileobj is control_socket) \
                    or key.fileobj in listeners \
                    or isinstance(key.fileobj, ControlConnection):
                continue

            # Seems we don't need this one anymore
            sel.unregister(key.fileobj)

        # Collect all the file descriptors we want to listen to
        existing_listeners = [key.fileobj for key in sel.get_map().values()]
        for listener in listeners:
            if listener not in existing_listeners:
                sel.register(listener, selectors.EVENT_READ)

        # Configuration tree
        try:
            message_handler = config.create_message_handler()
        except Exception as e:
            if args.verbosity >= 3:
                logger.exception("Error initialising DHCPv6 server")
            else:
                logger.critical("Error initialising DHCPv6 server: {}".format(e))
            return 1

        # Make sure we have space to store all the interface statistics
        statistics.set_categories(config.statistics)

        # Start worker processes
        my_pid = os.getpid()
        with NonBlockingPool(processes=config.workers,
                             initializer=setup_worker,
                             initargs=(message_handler, logging_queue, lowest_log_level, statistics, my_pid)) as pool:

            logger.info("Python DHCPv6 server is ready to handle requests")

            running = True
            while running:
                count_exception = False

                # noinspection PyBroadException
                try:
                    events = sel.select()
                    for key, mask in events:
                        if isinstance(key.fileobj, Listener):
                            try:
                                packet, replier = key.fileobj.recv_request()

                                # Update stats
                                message_count += 1

                                # Dispatch
                                pool.apply_async(handle_message, args=(packet, replier), error_callback=error_callback)
                            except IgnoreMessage:
                                # Message isn't complete, leave it for now
                                pass
                            except ClosedListener:
                                # This listener is closed (at least TCP shutdown for incoming data), so forget about it
                                sel.unregister(key.fileobj)
                                listeners.remove(key.fileobj)

                        elif isinstance(key.fileobj, ListenerCreator):
                            # Activity on this object means we have a new listener
                            new_listener = key.fileobj.create_listener()
                            if new_listener:
                                sel.register(new_listener, selectors.EVENT_READ)
                                listeners.append(new_listener)

                        # Handle signal notifications
                        elif key.fileobj == signal_r:
                            signal_nr = os.read(signal_r, 1)
                            if signal_nr[0] in (signal.SIGHUP,):
                                # SIGHUP tells the server to reload
                                try:
                                    # Read the new configuration
                                    config = config_parser.load_config(config_file)
                                except (ConfigurationSyntaxError, DataConversionError) as e:
                                    # Make the config exceptions a bit more readable
                                    msg = "Not reloading: " + str(e.message)
                                    if e.lineno and e.lineno != -1:
                                        msg += ' on line {}'.format(e.lineno)
                                    if e.url:
                                        parts = urlparse(e.url)
                                        msg += ' in {}'.format(parts.path)
                                    logger.critical(msg)
                                    continue

                                except ValueError as e:
                                    logger.critical("Not reloading: " + str(e))
                                    continue

                                logger.info("DHCPv6 server restarting after configuration change")
                                running = False
                                stopping = False
                                continue

                            elif signal_nr[0] in (signal.SIGINT, signal.SIGTERM):
                                logger.debug("Received termination request")

                                running = False
                                stopping = True
                                break

                            elif signal_nr[0] in (signal.SIGUSR1,):
                                # The USR1 signal is used to indicate initialisation errors in worker processes
                                count_exception = True

                        elif isinstance(key.fileobj, ControlSocket):
                            # A new control connection request
                            control_connection = key.fileobj.accept()
                            if control_connection:
                                # We got a connection, listen to events
                                sel.register(control_connection, selectors.EVENT_READ)

                        elif isinstance(key.fileobj, ControlConnection):
                            # Let the connection handle received data
                            control_connection = key.fileobj
                            commands = control_connection.get_commands()
                            for command in commands:
                                if command:
                                    logger.debug("Received control command '{}'".format(command))

                                if command == 'help':
                                    control_connection.send("Recognised commands:")
                                    control_connection.send("  help")
                                    control_connection.send("  stats")
                                    control_connection.send("  stats-json")
                                    control_connection.send("  reload")
                                    control_connection.send("  shutdown")
                                    control_connection.send("  quit")
                                    control_connection.acknowledge()

                                elif command == 'stats':
                                    control_connection.send(str(statistics))
                                    control_connection.acknowledge()

                                elif command == 'stats-json':
                                    control_connection.send(json.dumps(statistics.export()))
                                    control_connection.acknowledge()

                                elif command == 'reload':
                                    # Simulate a SIGHUP to reload
                                    os.write(signal_w, bytes([signal.SIGHUP]))
                                    control_connection.acknowledge('Reloading')

                                elif command == 'shutdown':
                                    # Simulate a SIGTERM to reload
                                    control_connection.acknowledge('Shutting down')
                                    control_connection.close()
                                    sel.unregister(control_connection)

                                    os.write(signal_w, bytes([signal.SIGTERM]))
                                    break

                                elif command == 'quit' or command is None:
                                    if command == 'quit':
                                        # User nicely signing off
                                        control_connection.acknowledge()

                                    control_connection.close()
                                    sel.unregister(control_connection)
                                    break

                                else:
                                    logger.warning("Rejecting unknown control command '{}'".format(command))
                                    control_connection.reject()

                except Exception as e:
                    # Catch-all exception handler
                    logger.exception("Caught unexpected exception {!r}".format(e))
                    count_exception = True

                if count_exception:
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

        # Regain root so we can delete the PID file and control socket
        restore_privileges()
        try:
            if pid_filename:
                os.unlink(pid_filename)
                logger.info("Removing PID-file {}".format(pid_filename))
        except OSError:
            pass

        try:
            if control_socket:
                os.unlink(control_socket.socket_path)
                logger.info("Removing control socket {}".format(control_socket.socket_path))
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
        logger.exception("Error: {}".format(e))
        return 1


if __name__ == '__main__':
    sys.exit(run())
