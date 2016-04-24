"""
The main IPv6 DHCPd
"""

import argparse
import codecs
import concurrent.futures
import fcntl
import grp
import importlib
import logging
import logging.handlers
import netifaces
import os
import pwd
import re
import selectors
import signal
import socket
import sys
import time
import types
from ipaddress import IPv6Address, AddressValueError
from logging.handlers import SysLogHandler
from struct import pack

import dhcpkit
from dhcpkit.ipv6.duids import DUID, LinkLayerDUID
from dhcpkit.ipv6.exceptions import InvalidPacketError, ListeningSocketError
from dhcpkit.ipv6.listening_socket import ListeningSocket
from dhcpkit.ipv6.message_handlers import MessageHandler
from dhcpkit.ipv6.messages import RelayReplyMessage
from dhcpkit.ipv6.server import config_parser
from dhcpkit.ipv6.server.config_parser import BOOLEAN_STATES, str_to_bool

logger = logging.getLogger()


def handle_args():
    """
    Handle the command line arguments.

    :return: The arguments object
    """
    parser = argparse.ArgumentParser(
        description="A flexible IPv6 DHCP server written in Python.",
    )

    parser.add_argument("config", help="the configuration file")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")

    args = parser.parse_args()

    return args


def set_up_logger(config: dict, verbosity: int = 0):
    """
    Set up logging based on the information in the configuration.

    :param config: The configuration
    :param verbosity: The verbosity level given as command line argument
    """
    # Don't filter on level in the root logger
    logger.setLevel(logging.NOTSET)

    # Determine syslog facility
    facility_name = config['logging']['facility'].lower()
    facility = logging.handlers.SysLogHandler.facility_names.get(facility_name)
    if not facility:
        logger.critical("Invalid logging facility: {}".format(facility_name))
        sys.exit(1)

    # Create the syslog handler
    syslog_handler = SysLogHandler(facility=facility)
    logger.addHandler(syslog_handler)

    # Also output to sys.stdout
    stdout_handler = logging.StreamHandler(stream=sys.stdout)

    # Set level according to verbosity
    if verbosity >= 3:
        stdout_handler.setLevel(logging.DEBUG)
    elif verbosity == 2:
        stdout_handler.setLevel(logging.INFO)
    elif verbosity >= 1:
        stdout_handler.setLevel(logging.WARNING)
    else:
        stdout_handler.setLevel(logging.CRITICAL)

    # Try using colourised output
    try:
        # noinspection PyPackageRequirements
        import colorlog
    except ImportError:
        colorlog = None

    if colorlog:
        if verbosity >= 3:
            # The color names are black, red, green, yellow, blue, purple, cyan and white.
            formatter = colorlog.ColoredFormatter('{yellow}{asctime}{reset} '
                                                  '[{threadName}] '
                                                  '{cyan}{name}#{lineno}{reset} '
                                                  '[{log_color}{levelname}{reset}] '
                                                  '{message}', style='{')
        elif verbosity == 2:
            formatter = colorlog.ColoredFormatter('{yellow}{asctime}{reset} '
                                                  '[{log_color}{levelname}{reset}] '
                                                  '{message}', datefmt=logging.Formatter.default_time_format, style='{')
        else:
            formatter = None

    else:
        # Set output style according to verbosity
        if verbosity >= 3:
            formatter = logging.Formatter('{asctime} [{threadName}] {name}#{lineno} [{levelname}] {message}', style='{')
        elif verbosity == 2:
            formatter = logging.Formatter('{asctime} [{levelname}] {message}',
                                          datefmt=logging.Formatter.default_time_format,
                                          style='{')
        else:
            formatter = None

    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)


def get_handler(config: dict) -> MessageHandler:
    """
    Get the request handler specified in the configuration file.

    :param config: The configuration
    :return: The handler
    """
    handler_module_name = config['server'].get('message-handler')

    if not handler_module_name:
        logger.critical("No message handler configured")
        sys.exit(1)

    try:
        logger.debug("Trying to import message handler from {}".format(handler_module_name))
        handler_module = importlib.import_module(handler_module_name)
        logger.info("Imported message handler from {}".format(handler_module_name))
    except ImportError as e:
        if '.' in handler_module_name:
            # It was a qualified name, and it didn't work...
            logger.critical(str(e))
            sys.exit(1)

        # No dots, try to prepend the default module path
        try:
            handler_module_name = 'dhcpkit.ipv6.message_handlers.' + handler_module_name

            logger.debug("Trying to import message handler from {}".format(handler_module_name))
            handler_module = importlib.import_module(handler_module_name)
            logger.info("Imported message handler from {}".format(handler_module_name))
        except ImportError as e:
            logger.critical(str(e))
            sys.exit(1)

    try:
        handler = handler_module.handler(config)

        if not isinstance(handler, MessageHandler):
            logger.critical("{}.handler is not a subclass of MessageHandler".format(handler_module_name))
            sys.exit(1)
    except (AttributeError, TypeError) as e:
        logger.critical("Cannot initialise message handler from module {}: {}".format(handler_module_name, e))
        sys.exit(1)

    return handler


def determine_interface_configs(config: dict):
    """
    Refine the config sections about interfaces. This will expand wildcards, resolve addresses etc.

    :param config: the config parser object
    :return: the list of configured interface names
    """
    interface_names = netifaces.interfaces()

    # Check the interface sections
    for section_name in config:
        parts = section_name.split(' ')

        # Skip non-interface sections
        if parts[0] != 'interface':
            continue

        # Check interface existence
        interface_name = parts[1]
        if interface_name != '*' and interface_name not in interface_names:
            logger.critical("Interface '{}' not found".format(interface_name))
            sys.exit(1)

        section = config[section_name]

        # Add some defaults if necessary
        section.setdefault('multicast', 'no')
        section.setdefault('listen-to-self', 'no')
        if str_to_bool(section['multicast']):
            # Multicast interfaces need a link-local address
            section.setdefault('link-local-addresses', 'auto')
        else:
            section.setdefault('link-local-addresses', '')
        section.setdefault('global-unicast-addresses', '')

        # Make sure that these are 'all', 'auto', or a sequence of addresses
        for option_name in ('link-local-addresses', 'global-unicast-addresses'):
            option_value = section[option_name].lower().strip()

            if option_value not in ('all', 'auto'):
                option_values = set()
                for addr_str in re.split('[,\t ]+', option_value):
                    if not addr_str:
                        # Empty is ok
                        continue

                    try:
                        addr = IPv6Address(addr_str)

                        if option_name == 'link-local-addresses' and not addr.is_link_local:
                            logger.critical("Interface {} option {} must contain "
                                            "link-local addresses".format(interface_name, option_name))
                            sys.exit(1)

                        if option_name == 'global-unicast-addresses' and not (addr.is_global or addr.is_private) \
                                or addr.is_multicast:
                            logger.critical("Interface {} option {} must contain "
                                            "global unicast addresses".format(interface_name, option_name))
                            sys.exit(1)

                        option_values.add(addr)

                    except AddressValueError:
                        logger.critical("Interface {} option {} must contain "
                                        "valid IPv6 addresses".format(interface_name, option_name))
                        sys.exit(1)

                section[option_name] = ' '.join(map(str, option_values))

    # Apply default to unconfigured interfaces
    if 'interface *' in config:
        interface_template = config['interface *']

        # Copy from wildcard to other interfaces
        for interface_name in interface_names:
            section_name = 'interface {}'.format(interface_name)
            if section_name in config:
                # Don't touch it
                pass
            else:
                config[section_name] = {}
                for option_name, option_value in interface_template.items():
                    config[section_name][option_name] = option_value

        # Forget about the wildcard
        del config['interface *']

    # Expand 'all' and 'auto' and validate the result
    interface_names = [section_name.split(' ')[1] for section_name in config
                       if section_name.split(' ')[0] == 'interface']
    interface_count = 0
    for interface_name in interface_names:
        section_name = 'interface {}'.format(interface_name)
        section = config[section_name]

        for option_name in ('link-local-addresses', 'global-unicast-addresses'):
            option_value = section[option_name].lower()

            if option_value in ('auto', 'all'):
                logger.debug("Discovering {} on interface {}".format(option_name, interface_name))

                # Get all addresses
                available_addresses_info = netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])
                available_address_strings = [address_info['addr'] for address_info in available_addresses_info]
                available_addresses = [IPv6Address(address.split('%')[0]) for address in available_address_strings]
                available_addresses.sort()

                # Filter on type
                if option_name == 'link-local-addresses':
                    available_addresses = [address for address in available_addresses if address.is_link_local]
                elif option_name == 'global-unicast-addresses':
                    available_addresses = [address for address in available_addresses if not address.is_link_local]

                for address in available_addresses:
                    logger.debug("- Found {}".format(address))

                if option_value == 'all':
                    if available_addresses:
                        logger.debug("= Using all of them")
                    else:
                        logger.debug("= No {} on interface {}: skipping".format(option_name, interface_name))

                elif option_value == 'auto':
                    # Pick the 'best' one if the config says 'auto'
                    # TODO: need to take autoconf/temporary/etc into account once netifaces implements those

                    # First try to find an address with the universal bit set
                    universal_addresses = [address for address in available_addresses if address.packed[8] & 2]
                    if universal_addresses:
                        # Take the lowest universal address
                        available_addresses = [min(universal_addresses)]

                    elif available_addresses:
                        # Take the lowest available address
                        available_addresses = [min(available_addresses)]

                    if available_addresses:
                        logger.debug("= Chose {} as 'best' address".format(available_addresses[0]))
                    else:
                        logger.debug("= No {} on interface {}: skipping".format(option_name, interface_name))

                # Store list of addresses as strings. Yes, this means we probably have to parse them again later but I
                # want to keep the config as clean strings.
                section[option_name] = ' '.join(map(str, available_addresses))

        # Remove interfaces without addresses
        if not section['link-local-addresses'] and not section['global-unicast-addresses']:
            del config[section_name]
            continue

        # Remove loopback interfaces
        if section['global-unicast-addresses']:
            global_addresses = [IPv6Address(address) for address in section['global-unicast-addresses'].split(' ')]
            if any([address.is_loopback for address in global_addresses]):
                # We don't want loopback interfaces
                logger.warning("Not listening on interface {}: it is a loopback interface".format(interface_name))
                del config[section_name]
                continue

        # Check that multicast interfaces have a link-local address
        if str_to_bool(section['multicast']) and not section['link-local-addresses']:
            logger.critical("Interface {} listens for multicast requests "
                            "but has no link-local address to reply from".format(interface_name))
            sys.exit(1)

        # Count this one
        interface_count += 1

    if interface_count == 0:
        logger.critical("This server is not configured to listen on any interfaces")
        sys.exit(1)


def determine_server_duid(config: dict):
    """
    Make sure we have a server DUID.

    :param config: The configuration
    """
    # Try to get the server DUID from the configuration
    config_duid = config['server']['duid']
    if config_duid.lower() not in ('', 'auto'):
        config_duid = config_duid.strip()
        try:
            duid = bytes.fromhex(config_duid.strip())
        except ValueError:
            logger.critical("Configured hex DUID contains invalid characters")
            sys.exit(1)

        # Check if we can parse this DUID
        length, duid = DUID.parse(duid, length=len(duid))
        if not isinstance(duid, DUID):
            logger.critical("Configured DUID is invalid")
            sys.exit(1)

        logger.debug("Using server DUID from configuration: {}".format(config_duid))

        config['server']['duid'] = codecs.encode(duid.save(), 'hex').decode('ascii')
        return

    # Use the first interface's MAC address as default
    if config:
        interface_names = [section_name.split(' ')[1] for section_name in config
                           if section_name.split(' ')[0] == 'interface']
        interface_names.sort()

        for interface_name in interface_names:
            link_addresses = netifaces.ifaddresses(interface_name).get(netifaces.AF_LINK, [])
            link_addresses = [link_address['addr'] for link_address in link_addresses if link_address.get('addr')]
            link_addresses.sort()

            for link_address in link_addresses:
                # Try to decode
                try:
                    ll_addr = bytes.fromhex(link_address.replace(':', ''))

                    duid = LinkLayerDUID(hardware_type=1, link_layer_address=ll_addr).save()

                    logger.debug("Using server DUID based on {} link address: "
                                 "{}".format(interface_name, codecs.encode(duid, 'hex').decode('ascii')))

                    config['server']['duid'] = codecs.encode(duid, 'hex').decode('ascii')
                    return
                except ValueError:
                    # Try the next one
                    pass

    # We didn't find a useful server DUID
    logger.critical("Cannot find a usable DUID")
    sys.exit(1)


def get_sockets(config: dict) -> [ListeningSocket]:
    """
    Set up the network sockets.

    :param config: The configuration
    :return: The list of sockets
    """
    logger.debug("Creating sockets")

    mc_address = dhcpkit.ipv6.All_DHCP_Relay_Agents_and_Servers
    port = dhcpkit.ipv6.SERVER_PORT

    # Placeholders for exception message
    interface_name = 'unknown'
    address = 'unknown'

    try:
        sockets = []

        interface_names = [section_name.split(' ')[1] for section_name in config
                           if section_name.split(' ')[0] == 'interface']
        for interface_name in interface_names:
            section_name = 'interface {}'.format(interface_name)
            section = config[section_name]

            interface_index = socket.if_nametoindex(interface_name)

            first_global = None
            for address_str in section['global-unicast-addresses'].split(' '):
                if not address_str:
                    continue

                address = IPv6Address(address_str)
                logger.debug("- Creating socket for {} on {}".format(address, interface_name))

                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.bind((str(address), port))
                sockets.append(ListeningSocket(interface_name, sock))

                if not first_global:
                    first_global = address

            if not first_global and (section['link-local-addresses'] or str_to_bool(section.get['multicast'])):
                # Get all global addresses because we would like one for link identification
                available_addresses_info = netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])
                available_address_strings = [address_info['addr'] for address_info in available_addresses_info]
                available_addresses = [IPv6Address(address.split('%')[0]) for address in available_address_strings]
                global_addresses = [address for address in available_addresses if not address.is_link_local]
                global_addresses.sort()

                if global_addresses:
                    first_global = global_addresses[0]
                else:
                    # No address known
                    first_global = IPv6Address('::')

            link_local_sockets = []
            for address_str in section['link-local-addresses'].split(' '):
                if not address_str:
                    continue

                address = IPv6Address(address_str)
                logger.debug("- Creating socket for {} on {}".format(address, interface_name))

                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.bind((str(address), port, 0, interface_index))
                link_local_sockets.append((address, sock))
                sockets.append(ListeningSocket(interface_name, sock, global_address=first_global))

            if str_to_bool(section['multicast']):
                address = mc_address
                reply_from = link_local_sockets[0]

                logger.debug("- Creating socket for {} with {} "
                             "as reply-from address on {} ".format(address, reply_from[0], interface_name))

                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.bind((address, port, 0, interface_index))

                if str_to_bool(section['listen-to-self']):
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)

                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP,
                                pack('16sI', IPv6Address('ff02::1:2').packed, interface_index))

                sockets.append(ListeningSocket(interface_name, sock, reply_from[1], global_address=first_global))

    except OSError as e:
        logger.critical("Cannot create socket for address {} on interface {}: {}".format(address, interface_name,
                                                                                         e.strerror))
        sys.exit(1)
    except ListeningSocketError as e:
        logger.critical(str(e))
        sys.exit(1)

    return sockets


def drop_privileges(uid_name: str or int, gid_name: str or int or None):
    """
    Drop root privileges and change to something more safe.

    :param uid_name: The UID to drop to
    :param gid_name: The GID to drop to
    """
    if os.getuid() != 0:
        logger.warning("Not running as root: cannot change uid/gid to {}/{}".format(uid_name, gid_name))
        return

    # Get the uid/gid from the name
    try:
        try:
            # Try to use it as an integer
            running_uid = int(uid_name)
        except ValueError:
            # Try to use it as a name
            running_uid = pwd.getpwnam(uid_name).pw_uid
    except KeyError:
        logger.critical("User {} does not exist".format(uid_name))
        sys.exit(1)

    if gid_name:
        try:
            try:
                # Try to use it as an integer
                running_gid = int(gid_name)
            except ValueError:
                # Try to use it as a name
                running_gid = grp.getgrnam(gid_name).gr_gid
        except KeyError:
            logger.critical("Group {} does not exist".format(gid_name))
            sys.exit(1)
    else:
        running_gid = pwd.getpwnam(uid_name).pw_gid

    # Remove group privileges
    os.setgroups([])

    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)

    # Ensure a very conservative umask
    os.umask(0o077)

    # Resolve names
    try:
        uid_name = pwd.getpwuid(running_uid).pw_name
    except KeyError:
        uid_name = str(running_uid)

    try:
        gid_name = grp.getgrgid(running_gid).gr_name
    except KeyError:
        gid_name = str(running_gid)

    logger.debug("Dropped privileges to {}/{}".format(uid_name, gid_name))


def create_handler_callback(listening_socket: ListeningSocket) -> types.FunctionType:
    """
    Create a callback for the handler method that still knows the listening socket and the sender

    :param listening_socket: The listening socket to remember
    :return: A callback function with the listening socket and sender enclosed
    :rtype: (concurrent.futures.Future) -> None
    """

    def callback(future: concurrent.futures.Future):
        """
        A callback that handles the result of a handler

        :param future: The future object with the completed result
        """
        try:
            # Get the result
            reply = future.result()

            if reply is None:
                # No reply: we're done with this request
                return

            if not isinstance(reply, RelayReplyMessage):
                logger.error("Handler returned invalid result, not sending a reply")
                return

            try:
                listening_socket.send_reply(reply)
            except ValueError as e:
                logger.error("Handler returned invalid message: {}".format(e))
                return

        except concurrent.futures.CancelledError:
            pass

        except Exception as e:
            # Catch-all exception handler
            logger.exception("Caught unexpected exception {!r}".format(e))

    return callback


def main() -> int:
    """
    The main program loop

    :return: The program exit code
    """
    args = handle_args()
    config = config_parser.load_config(args.config)

    # Go to the working directory
    os.chdir(config['server']['working-directory'])

    set_up_logger(config, args.verbosity)

    logger.info("Starting Python DHCPv6 server v{}".format(dhcpkit.__version__))

    determine_interface_configs(config)
    determine_server_duid(config)

    sockets = get_sockets(config)
    drop_privileges(config['server']['user'], config['server']['group'])

    handler = get_handler(config)

    sel = selectors.DefaultSelector()
    for sock in sockets:
        sel.register(sock, selectors.EVENT_READ)

    # Convert signals to messages on a pipe
    signal_r, signal_w = os.pipe()
    flags = fcntl.fcntl(signal_w, fcntl.F_GETFL, 0)
    flags = flags | os.O_NONBLOCK
    fcntl.fcntl(signal_w, fcntl.F_SETFL, flags)
    signal.set_wakeup_fd(signal_w)
    sel.register(signal_r, selectors.EVENT_READ)

    # Ignore normal signal handling
    signal.signal(signal.SIGINT, lambda signum, frame: None)
    signal.signal(signal.SIGTERM, lambda signum, frame: None)
    signal.signal(signal.SIGHUP, lambda signum, frame: None)

    # Excessive exception catcher
    exception_history = []

    logger.info("Python DHCPv6 server is ready to handle requests")

    exception_window = float(config['server']['exception-window'])
    max_exceptions = int(config['server']['max-exceptions'])
    workers = max(1, int(config['server']['threads']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        stopping = False
        while not stopping:
            # noinspection PyBroadException
            try:
                events = sel.select()
                for key, mask in events:
                    # Handle signal notifications
                    if key.fileobj == signal_r:
                        signal_nr = os.read(signal_r, 1)
                        if signal_nr[0] in (signal.SIGHUP,):
                            # SIGHUP tells the handler to reload
                            # We might even re-parse the config in a later implementation
                            handler.reload(config)
                        elif signal_nr[0] in (signal.SIGINT, signal.SIGTERM):
                            logger.debug("Received termination request")

                            stopping = True
                            break

                        # Unknown signal: ignore
                        continue
                    elif isinstance(key.fileobj, ListeningSocket):
                        try:
                            msg_in = key.fileobj.recv_request()
                        except InvalidPacketError as e:
                            logging.warning("Invalid message from {}: {}".format(e.sender[0], str(e)))
                            continue
                        except ValueError as e:
                            logging.warning("Invalid incoming message: {}".format(str(e)))
                            continue

                        # Submit this request to the worker pool
                        received_over_multicast = key.fileobj.listen_address.is_multicast
                        future = executor.submit(handler.handle, msg_in, received_over_multicast)

                        # Create the callback
                        callback = create_handler_callback(key.fileobj)
                        future.add_done_callback(callback)

            except Exception as e:
                # Catch-all exception handler
                logger.exception("Caught unexpected exception {!r}".format(e))

                now = time.monotonic()

                # Add new exception time to the history
                exception_history.append(now)

                # Remove exceptions outside the window from the history
                cutoff = now - exception_window
                while exception_history and exception_history[0] < cutoff:
                    exception_history.pop(0)

                # Did we receive too many exceptions shortly after each other?
                if len(exception_history) > max_exceptions:
                    logger.critical("Received more than {} exceptions in {} seconds, exiting".format(max_exceptions,
                                                                                                     exception_window))
                    stopping = True

    logger.info("Shutting down Python DHCPv6 server v{}".format(dhcpkit.__version__))

    return 0


def run() -> int:
    """
    Run the main program and handle exceptions

    :return: The program exit code
    """
    try:
        return main()
    except config_parser.ConfigError as e:
        logger.critical("Configuration error: {}".format(e))
        sys.exit(1)


if __name__ == '__main__':
    # Run the server
    sys.exit(run())
