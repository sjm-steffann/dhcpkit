"""
DHCP handler that reads IA-NA and IA-PD assignments per relay interface ID from a CSV file
"""

from collections import namedtuple
import configparser
import csv
from ipaddress import IPv6Network, IPv6Address
import logging
import os

from dhcp.ipv6 import extensions
from dhcp.ipv6.extensions.prefix_delegation import IAPrefixOption
from dhcp.ipv6.handlers.base import UseMulticastError, CannotReplyError
from dhcp.ipv6.handlers.standard import StandardHandler
from dhcp.ipv6.options import InterfaceIdOption, IAAddressOption
from ipv6.handlers.base import TransactionBundle

logger = logging.getLogger(__name__)

# Load all extensions so we can handle them
extensions.load_all()

# A named tuple to store assignments in
Assignment = namedtuple('Assignment', ['address', 'prefix'])


class CSVHandler(StandardHandler):
    """
    DHCP handler that reads IA-NA and IA-PD assignments per relay interface ID from a CSV file

    :type options: list[Option]
    :type address_preferred_lifetime: int
    :type address_valid_lifetime: int
    :type prefix_preferred_lifetime: int
    :type prefix_valid_lifetime: int
    :type assignments: dict[bytes, Assignment]
    """

    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)

        # The options we're going to use for every request
        self.options = self.get_options_from_config()

        # Standard lifetimes
        self.address_preferred_lifetime = self.config.get('handler', 'address-preferred-lifetime', fallback=600)
        self.address_valid_lifetime = self.config.get('handler', 'address-valid-lifetime', fallback=900)
        self.prefix_preferred_lifetime = self.config.get('handler', 'prefix-preferred-lifetime', fallback=600)
        self.prefix_valid_lifetime = self.config.get('handler', 'prefix-valid-lifetime', fallback=900)

        # Fill assignments
        self.assignments = {}
        self.read_csv()

    # noinspection PyDocstring
    def handle_reload(self):
        # Update the assignments from the CSV
        self.read_csv()

    def read_csv(self):
        """
        Read the assignments from the file specified in the configuration
        """
        csv_rel_filename = self.config.get('handler', 'assignments-file')

        # Find the CSV file
        if os.path.isabs(csv_rel_filename):
            csv_filename = csv_rel_filename
        else:
            config_filename = self.config['config']['filename']
            config_dir = os.path.dirname(config_filename)
            csv_filename = os.path.realpath(os.path.join(config_dir, csv_rel_filename))

        if self.assignments:
            logger.debug("Reloading assignments from {}".format(csv_filename))
        else:
            logger.debug("Loading assignments from {}".format(csv_filename))

        self.assignments = {}
        with open(csv_filename) as csv_file:
            reader = csv.DictReader(csv_file)

            # First line is column headings
            line = 1
            for row in reader:
                line += 1
                try:
                    address_str = row['address'].strip()
                    address = address_str and IPv6Address(address_str) or None

                    prefix_str = row['prefix'].strip()
                    prefix = prefix_str and IPv6Network(prefix_str) or None

                    self.assignments[row['interface-id'].encode('utf8')] = Assignment(address=address, prefix=prefix)
                except KeyError:
                    raise configparser.Error("Assignment CSV must have columns "
                                             "'interface-id', 'address' and 'prefix'")
                except ValueError as e:
                    logger.error("Ignoring line {} with invalid value: {}".format(line, e))

        logger.info("Loaded {} assignments from CSV".format(len(self.assignments)))

    @staticmethod
    def get_interface_id(relay_messages: list) -> bytes:
        """
        Extract the interface-ID of the relay closest to the client

        :param relay_messages: The chain of relay messages
        :return: The interface-id bytes
        """
        try:
            interface_id_option = relay_messages[0].get_option_of_type(InterfaceIdOption)
            if interface_id_option is None:
                raise CannotReplyError
        except IndexError:
            # Assume that missing relay options mean that the client used unicast
            raise UseMulticastError

        return interface_id_option.interface_id

    # noinspection PyDocstring
    def get_non_temporary_addresses(self, bundle: TransactionBundle) -> list:
        interface_id = self.get_interface_id(bundle.relay_messages)
        assignment = self.assignments.get(interface_id)

        # There might not be an address for this client
        if not assignment or assignment.address is None:
            return []

        # Insert the address in an IAAddressOption
        return [
            IAAddressOption(address=assignment.address,
                            preferred_lifetime=self.address_preferred_lifetime,
                            valid_lifetime=self.address_valid_lifetime)
        ]

    # noinspection PyDocstring
    def get_temporary_addresses(self, bundle: TransactionBundle) -> list:
        # We don't provide any
        return []

    # noinspection PyDocstring
    def get_delegated_prefixes(self, bundle: TransactionBundle) -> list:
        interface_id = self.get_interface_id(bundle.relay_messages)
        assignment = self.assignments.get(interface_id)

        # There might not be a prefix for this client
        if not assignment or assignment.prefix is None:
            return []

        # Insert the address in an IAAddressOption
        return [
            IAPrefixOption(prefix=assignment.prefix,
                           preferred_lifetime=self.address_preferred_lifetime,
                           valid_lifetime=self.address_valid_lifetime)
        ]

    # noinspection PyDocstring
    def get_options(self, bundle: TransactionBundle) -> list:
        # We have a fixed list of options
        return self.options


handler = CSVHandler
