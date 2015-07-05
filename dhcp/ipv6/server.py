import argparse
import codecs
import concurrent.futures
import configparser
from configparser import SectionProxy
import importlib
from ipaddress import IPv6Address, AddressValueError
from logging import StreamHandler, Formatter
from logging.handlers import SysLogHandler
import selectors
import socket
from struct import pack
import sys
import os
import re
import signal
import fcntl
import time
import pwd
import grp
import netifaces
import logging
import logging.handlers
import types

import dhcp
from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.listening_socket import ListeningSocket, ListeningSocketError
from dhcp.ipv6.messages import Message

logger = logging.getLogger()


def handle_args():
    parser = argparse.ArgumentParser(
        description="A flexible IPv6 DHCP server written in Python.",
    )

    parser.add_argument("config", help="the configuration file")
    parser.add_argument("-I", "--intf-config", action="store_true", help="Show the active interface configuration")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")

    args = parser.parse_args()

    return args


def load_config(config_file_name) -> configparser.ConfigParser:
    logger.debug("Loading configuration file {}".format(config_file_name))

    config = configparser.ConfigParser()

    # Create mandatory sections
    config.add_section('handler')
    config.add_section('logging')
    config.add_section('process')
    config.add_section('server')

    try:
        config_file_name = os.path.realpath(config_file_name)
        config_file = open(config_file_name, mode='r', encoding='utf-8')
        config.read_file(config_file)
    except FileNotFoundError:
        logger.error("Configuration file {} not found".format(config_file_name))
        sys.exit(1)

    return config


def set_up_logger(logger_config: SectionProxy, verbosity: int=0) -> logging.Logger:
    # Don't filter on level in the root logger
    logger.setLevel(logging.NOTSET)

    # Determine syslog facility
    facility_name = str(logger_config.get('facility', 'daemon')).lower()
    facility = logging.handlers.SysLogHandler.facility_names.get(facility_name)
    if not facility:
        logger.critical("Invalid logging facility: {}".format(facility_name))
        sys.exit(1)

    # Create the syslog handler
    syslog_handler = SysLogHandler(facility=facility)
    logger.addHandler(syslog_handler)

    if verbosity > 0:
        # Also output to sys.stdout
        stdout_handler = StreamHandler(stream=sys.stdout)

        # Set level according to verbosity
        if verbosity >= 2:
            stdout_handler.setLevel(logging.DEBUG)
        else:
            stdout_handler.setLevel(logging.INFO)

        # Set output style according to verbosity
        if verbosity >= 3:
            stdout_handler.setFormatter(Formatter('{asctime} [{threadName}] {name}#{lineno} [{levelname}] {message}',
                                                  style='{'))
        elif verbosity == 2:
            stdout_handler.setFormatter(Formatter('{asctime} [{levelname}] {message}',
                                                  datefmt=Formatter.default_time_format, style='{'))

        logger.addHandler(stdout_handler)


def get_handler(config: configparser.ConfigParser) -> Handler:
    handler_module_name = config['handler'].get('module')
    if not handler_module_name:
        logger.critical("No handler module configured")
        sys.exit(1)

    logger.info("Importing request handler from {}".format(handler_module_name))

    try:
        handler_module = importlib.import_module(handler_module_name)
    except ImportError as e:
        logger.critical(str(e))
        sys.exit(1)

    # The handler module must have a function called 'get_handler' which returns a subclass of Handler
    try:
        handler = handler_module.get_handler(config)

        if not isinstance(handler, Handler):
            logger.critical("{}.get_handler() did not return a subclass of "
                            "dhcp.ipv6.handlers.Handler".format(handler_module_name))
            sys.exit(1)
    except (AttributeError, TypeError):
        logger.critical("Module {} does not contain a 'get_handler()' function".format(handler_module_name))
        sys.exit(1)

    return handler


def get_interface_configs(config: configparser.ConfigParser) -> {str: {str: str}}:
    interface_names = netifaces.interfaces()

    # Gather the interface sections
    interface_configs = {}
    for section_name in config.sections():
        parts = section_name.split(' ')

        # Skip non-interface sections
        if parts[0] != 'interface':
            continue

        # Check name structure
        if len(parts) != 2:
            logger.critical("Interface sections must be named [interface xyz] where 'xyz' is an interface name")
            sys.exit(1)

        # Check interface existence
        interface_name = parts[1]
        if interface_name != '*' and interface_name not in interface_names:
            logger.critical("Interface '{}' not found".format(interface_name))
            sys.exit(1)

        # Copy the settings into a normal dictionary
        interface_configs[interface_name] = dict(config[section_name])

        # Add some defaults if necessary
        interface_configs[interface_name].setdefault('multicast', 'no')
        interface_configs[interface_name].setdefault('listen-to-self', 'no')
        if interface_configs[interface_name]['multicast'].lower() == 'yes':
            # Multicast interfaces need a link-local address
            interface_configs[interface_name].setdefault('link-local-addresses', 'auto')
        else:
            interface_configs[interface_name].setdefault('link-local-addresses', '')
        interface_configs[interface_name].setdefault('global-addresses', '')

    # Apply default to unconfigured interfaces
    if '*' in interface_configs:
        # Extract the default
        default_config = interface_configs['*']
        del interface_configs['*']

        for interface_name in interface_names:
            if interface_name not in interface_configs:
                interface_configs[interface_name] = dict(default_config)

    # Check options and values
    for interface_name, interface_config in interface_configs.items():
        for option_name, option_value in interface_config.items():
            if option_name in ('multicast', 'listen-to-self'):
                option_value = option_value.lower()
                if option_value not in ('yes', 'no'):
                    logger.critical(
                        "Interface {} option {} must be either 'yes' or 'no'".format(interface_name, option_name))
                    sys.exit(1)

                # Convert to boolean
                interface_configs[interface_name][option_name] = (option_value == 'yes')

            elif option_name in ('link-local-addresses', 'global-addresses'):
                option_value = option_value.lower()
                if option_value in ('auto', 'all'):
                    logger.info("Discovering {} on interface {}".format(option_name, interface_name))

                    # Get all addresses
                    available_addresses = netifaces.ifaddresses(interface_name).get(netifaces.AF_INET6, [])
                    available_addresses = [address_info['addr'] for address_info in available_addresses]
                    available_addresses = [IPv6Address(address.split('%')[0]) for address in available_addresses]

                    # Filter on type
                    if option_name == 'link-local-addresses':
                        available_addresses = [address for address in available_addresses if address.is_link_local]
                    elif option_name == 'global-addresses':
                        available_addresses = [address for address in available_addresses
                                               if not address.is_link_local and (address.is_global
                                                                                 or address.is_private)]

                    for address in available_addresses:
                        logger.debug("- Found {}".format(address))

                    if option_value == 'all':
                        logger.debug("= Using all of them")

                    # Pick the 'best' one if the config says 'auto'
                    if option_value == 'auto':
                        # TODO: need to take autoconf/temporary/etc into account once netifaces implements those

                        # First try to find an address with the universal bit set
                        universal_addresses = [address for address in available_addresses if address.packed[8] & 2]
                        if universal_addresses:
                            # Take the lowest universal address
                            available_addresses = [min(universal_addresses)]

                        elif available_addresses:
                            # Take the lowest available address
                            available_addresses = [min(available_addresses)]

                        logger.debug("= Chose {} as 'best' address".format(available_addresses[0]))

                    # Store list of IPv6Addresses
                    interface_configs[interface_name][option_name] = available_addresses

                else:
                    # This should be a list of addresses
                    option_values = []
                    for addr_str in re.split('[^0-9a-f:]+', option_value):
                        if not addr_str:
                            continue

                        try:
                            addr = IPv6Address(addr_str)

                            if option_name == 'link-local-addresses' and not addr.is_link_local:
                                logger.critical("Interface {} option {} must contain "
                                                "link-local addresses".format(interface_name, option_name))
                                sys.exit(1)

                            if option_name == 'global-addresses' and not (addr.is_global or addr.is_private) \
                                    or addr.is_multicast:
                                logger.critical("Interface {} option {} must contain "
                                                "global unicast addresses".format(interface_name, option_name))
                                sys.exit(1)

                            option_values.append(addr)

                        except AddressValueError:
                            logger.critical("Interface {} option {} must contain "
                                            "valid IPv6 addresses".format(interface_name, option_name))
                            sys.exit(1)

                    # Store list of IPv6Addresses
                    interface_configs[interface_name][option_name] = option_values

            else:
                logger.critical("Interface {} has unknown option {}".format(interface_name, option_name))
                sys.exit(1)

    # And clean up
    for interface_name in list(interface_configs.keys()):
        # Remove loopback
        if IPv6Address('::1') in interface_configs[interface_name]['global-addresses']:
            del interface_configs[interface_name]
            continue

        # Remove interfaces without addresses
        if not interface_configs[interface_name]['link-local-addresses'] \
                and not interface_configs[interface_name]['global-addresses']:
            del interface_configs[interface_name]
            continue

        # Check that multicast interfaces have a link-local address
        if interface_configs[interface_name]['multicast'] \
                and not interface_configs[interface_name]['link-local-addresses']:
            logger.critical("Interface {} listens for multicast requests "
                            "but has no link-local address to reply from".format(interface_name))
            sys.exit(1)

        # Remove duplicates
        interface_configs[interface_name]['link-local-addresses'] = list(
            set(interface_configs[interface_name]['link-local-addresses']))
        interface_configs[interface_name]['global-addresses'] = list(
            set(interface_configs[interface_name]['global-addresses']))

    return interface_configs


def determine_server_duid(options: SectionProxy, interface_configs: dict=None) -> bytes:
    # Try to get the server DUID from the configuration
    config_duid = options.get('duid')
    if config_duid:
        config_duid = config_duid.strip()
        try:
            duid = bytes.fromhex(config_duid.strip())
        except ValueError:
            logger.critical("Configured hex DUID contains invalid characters")
            sys.exit(1)

        if not duid:
            logger.critical("Configured DUID can not be empty")
            sys.exit(1)

        logger.info("Using server DUID from configuration: {}", config_duid)

        options['duid'] = codecs.encode(duid, 'hex').decode('ascii')
        return

    # Use the first interface's MAC address as default
    if interface_configs:
        interface_names = list(interface_configs.keys())
        interface_names.sort()

        for interface_name in interface_names:
            link_addresses = netifaces.ifaddresses(interface_name).get(netifaces.AF_LINK, [])
            link_addresses = [link_address['addr'] for link_address in link_addresses if link_address.get('addr')]
            link_addresses.sort()

            for link_address in link_addresses:
                # Try to decode
                try:
                    duid = bytes.fromhex(link_address.replace(':', ''))

                    # Prepend a special code to make sure it's unique
                    duid = b'\x53\x4a\x4d\x53' + duid

                    logger.info("Using server DUID based on {} link address: "
                                "{}".format(interface_name, codecs.encode(duid, 'hex').decode('ascii')))

                    options['duid'] = codecs.encode(duid, 'hex').decode('ascii')
                    return
                except ValueError:
                    # Try the next one
                    pass

    # We didn't find a useful server DUID
    logger.critical("Cannot find a usable DUID")
    sys.exit(1)


def get_sockets(interface_configs: dict) -> [ListeningSocket]:
    logger.debug("Creating sockets")

    mc_address = dhcp.ipv6.All_DHCP_Relay_Agents_and_Servers
    port = dhcp.ipv6.SERVER_PORT

    # Placeholders for exception message
    interface_name = 'unknown'
    address = 'unknown'

    try:
        sockets = []
        for interface_name, interface_config in interface_configs.items():
            interface_index = socket.if_nametoindex(interface_name)

            for address in interface_config['global-addresses']:
                logger.debug("- Creating socket for {} on {}".format(address, interface_name))

                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.bind((str(address), port))
                sockets.append(ListeningSocket(sock))

            link_local_sockets = []
            for address in interface_config['link-local-addresses']:
                logger.debug("- Creating socket for {} on {}".format(address, interface_name))

                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.bind((str(address), port, 0, interface_index))
                link_local_sockets.append((address, sock))
                sockets.append(ListeningSocket(sock))

            if interface_config['multicast']:
                address = mc_address
                reply_from = link_local_sockets[0]

                logger.debug(
                    "- Creating socket for {} with {} as reply-from address on {} ".format(address, reply_from[0],
                                                                                           interface_name))

                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.bind((address, port, 0, interface_index))

                if interface_config['listen-to-self']:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP,
                                pack('16sI', IPv6Address('ff02::1:2').packed, interface_index))

                sockets.append(ListeningSocket(sock, reply_from[1]))

    except OSError as e:
        logger.critical(
            "Cannot create socket for address {} on interface {}: {}".format(address, interface_name, e.strerror))
        sys.exit(1)
    except ListeningSocketError as e:
        logger.critical(str(e))
        sys.exit(1)

    return sockets


def show_interface_configs(interface_configs: dict):
    config = configparser.ConfigParser()

    interface_names = list(interface_configs.keys())
    interface_names.sort()
    for interface_name in interface_names:
        interface_config = interface_configs[interface_name]
        section_name = 'interface {}'.format(interface_name)
        config.add_section(section_name)

        option_names = list(interface_config.keys())
        option_names.sort()
        for option_name in option_names:
            value = interface_config[option_name]
            if isinstance(value, bool):
                config[section_name][option_name] = value and 'yes' or 'no'
            elif isinstance(value, list):
                config[section_name][option_name] = ' '.join([str(v) for v in value])
            else:
                config[section_name][option_name] = value

    config.write(sys.stdout)
    sys.exit(0)


def drop_privileges(uid_name: str, gid_name: str):
    if os.getuid() != 0:
        logger.info("Not running as root: cannot change uid/gid to {}/{}".format(uid_name, gid_name))
        return

    # Get the uid/gid from the name
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid

    # Remove group privileges
    os.setgroups([])

    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)

    # Ensure a very conservative umask
    os.umask(0o077)

    logger.info("Dropped privileges to {}/{}".format(uid_name, gid_name))


def create_handler_callback(listening_socket: ListeningSocket, sender: tuple) -> types.FunctionType:
    def callback(future: concurrent.futures.Future):
        try:
            # Get the result
            result = future.result()

            # Allow either None, a Message or a (Message, destination) tuple from the handler
            if result is None:
                # No response: we're done with this request
                return
            elif isinstance(result, Message):
                # Just a message returned, send reply to the sender
                msg_out, destination = result, sender
            elif isinstance(result, tuple):
                # Explicit destination specified, use that
                msg_out, destination = result
            else:
                msg_out = None
                destination = None

            if not isinstance(msg_out, Message) or not isinstance(destination, tuple) or len(destination) != 4:
                logger.error("Handler returned invalid result, not sending a reply to {}".format(destination[0]))
                return

            try:
                pkt_out = msg_out.save()
            except ValueError as e:
                logger.error("Handler returned invalid message: {}".format(e))
                return

            success = listening_socket.send_reply(pkt_out, destination)
            if success:
                logger.debug("Sent {} to {}".format(msg_out.__class__.__name__, destination[0]))
            else:
                logger.error("{} to {} could not be sent".format(msg_out.__class__.__name__, destination[0]))

        except concurrent.futures.CancelledError:
            pass

        except Exception as e:
            # Catch-all exception handler
            logger.exception("Cought unexpected exception {!r}".format(e))

    return callback


def run() -> int:
    args = handle_args()
    config = load_config(args.config)
    set_up_logger(config['logging'], args.verbosity)

    logger.info("Starting Python DHCPv6 server v{}".format(dhcp.__version__))

    interface_configs = get_interface_configs(config)

    if args.intf_config:
        show_interface_configs(interface_configs)

    sockets = get_sockets(interface_configs)
    drop_privileges(config['server'].get('user', 'nobody'),
                    config['server'].get('group', 'nobody'))

    determine_server_duid(config['server'], interface_configs)
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

    # Excessive exception catcher
    exception_history = []

    logger.info("Python DHCPv6 server is ready to handle requests")

    exception_window = config['server'].getfloat('exception-window', 1.0)
    max_exceptions = config['server'].getint('max-exceptions', 10)
    workers = max(1, config['server'].getint('threads', 10))
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
                        if signal_nr[0] in (signal.SIGINT, signal.SIGTERM):
                            logger.info("Received termination request")

                            stopping = True
                            break

                        # Unknown signal: ignore
                        continue

                    pkt, sender = key.fileobj.recv_request()
                    try:
                        length, msg_in = Message.parse(pkt)
                    except ValueError as e:
                        logging.info("Invalid message from {}: {}".format(sender[0], str(e)))
                        continue

                    # Submit this request to the worker pool
                    receiver = key.fileobj.listen_socket.getsockname()
                    future = executor.submit(handler.handle, msg_in, sender, receiver)

                    # Create the callback
                    callback = create_handler_callback(key.fileobj, sender)
                    future.add_done_callback(callback)

            except Exception as e:
                # Catch-all exception handler
                logger.exception("Cought unexpected exception {!r}".format(e))

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

    logger.info("Shutting down Python DHCPv6 server v{}".format(dhcp.__version__))

    return 0
