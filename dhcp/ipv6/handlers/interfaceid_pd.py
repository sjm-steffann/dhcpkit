import configparser
from configparser import NoOptionError, ParsingError
import csv
from ipaddress import IPv6Network, IPv6Address
import logging
import os

from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import Message
from dhcp.ipv6.options import InterfaceIdOption
from dhcp.rwlock import RWLock

logger = logging.getLogger(__name__)


class InterfaceIdPrefixDelegationHandler(Handler):
    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)
        self.assignments = {}  # type: {bytes: (IPv6Address, IPv6Network)}
        self._lock = RWLock()
        self.read_csv()

    def read_csv(self):
        csv_rel_filename = self.config['handler']['assignments-file']
        if not csv_rel_filename:
            raise NoOptionError('assignments-file', 'handler')

        # Find the CSV file
        config_filename = self.config['config']['filename']
        config_dir = os.path.dirname(config_filename)
        csv_filename = os.path.realpath(os.path.join(config_dir, csv_rel_filename))

        # Get the write lock before we update the assignments
        with self._lock.write_lock():
            self.assignments = {}
            with open(csv_filename) as csv_file:
                reader = csv.DictReader(csv_file)

                # First line is column headings
                line = 1
                for row in reader:
                    line += 1
                    try:
                        self.assignments[row['interface-id'].encode('utf8')] = (IPv6Address(row['address']),
                                                                                IPv6Network(row['prefix']))
                    except KeyError:
                        raise ParsingError("Assignment CSV must have columns 'interface-id', 'address' and 'prefix'")
                    except ValueError as e:
                        logger.error("Ignoring line {} with invalid value: {}".format(line, e))

    def find_clostest_interface_id(self, relay_messages: list) -> bytes or None:
        if not relay_messages:
            # No relay message -> no interface
            return None

        # Return the interface is from the first relay, which is the one closest to the client
        for option in relay_messages[-1].options:
            if isinstance(option, InterfaceIdOption):
                return option.interface_id

        # Nothing found
        return None

    def get_addresses_for_interface_id(self, relay_messages: list) -> (IPv6Address or None, IPv6Network or None):
        interface_id = self.find_clostest_interface_id(relay_messages)
        if not interface_id:
            logger.warning("Received a request without a relay interface id: cannot assign addresses")
            return None, None

        # Get the read lock
        with self._lock.read_lock():
            result = self.assignments.get(interface_id)
            if result:
                return result
            else:
                logger.warning("Received a request with unknown relay interface id {}: "
                               "cannot assign addresses".format(interface_id))
                return (None, None)

    # noinspection PyUnusedLocal
    def handle_solicit_message(self, request: Message, relay_messages: list,
                               sender: tuple, receiver: tuple) -> None or Message or (Message, tuple):

        address, prefix = self.get_addresses_for_interface_id(relay_messages)
        logger.debug("Decided on {} and {}".format(address, prefix))


def get_handler(config: configparser.ConfigParser) -> type:
    return InterfaceIdPrefixDelegationHandler(config)
