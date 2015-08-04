"""
An option handler that assigns addresses based on DUID from a CSV file
"""
import codecs
import configparser
import csv
from ipaddress import IPv6Address, IPv6Network
import logging

from dhcpkit.ipv6 import option_handler_registry
from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.message_handlers.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.option_handlers.fixed_assignment import FixedAssignmentOptionHandler
from dhcpkit.ipv6.option_handlers.utils import Assignment
from dhcpkit.ipv6.options import ClientIdOption, InterfaceIdOption

logger = logging.getLogger(__name__)


class CSVBasedFixedAssignmentOptionHandler(FixedAssignmentOptionHandler):
    """
    Assign addresses and/or prefixes based on the contents of a CSV file
    """

    def __init__(self, filename: str, responsible_for_links: [IPv6Network],
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param filename: The filename containing the CSV data
        :param responsible_for_links: The IPv6 links that this handler is responsible for
        """
        super().__init__(responsible_for_links,
                         address_preferred_lifetime, address_valid_lifetime,
                         prefix_preferred_lifetime, prefix_valid_lifetime)

        self.mapping = self.parse_csv_file(filename)

    def get_assignment(self, bundle: TransactionBundle) -> Assignment:
        """
        Look up the assignment based on DUID, Interface-ID of the relay closest to the client and Remote-ID of the
        relay closest to the client, in that order.

        :param bundle: The transaction bundle
        :return: The assignment, if any
        """
        # Look up based on DUID
        duid_option = bundle.request.get_option_of_type(ClientIdOption)
        duid = 'duid:' + codecs.encode(duid_option.duid.save(), 'hex').decode('ascii')
        if duid in self.mapping:
            return self.mapping[duid]

        # Look up based on Interface-ID
        interface_id_option = bundle.relay_messages[0].get_option_of_type(InterfaceIdOption)
        interface_id = None
        if interface_id_option:
            interface_id = 'interface-id:' + codecs.encode(interface_id_option.interface_id, 'hex').decode('ascii')
            if interface_id in self.mapping:
                return self.mapping[interface_id]

        # Look up based on Remote-ID
        remote_id_option = bundle.relay_messages[0].get_option_of_type(RemoteIdOption)
        remote_id = None
        if remote_id_option:
            remote_id = 'remote-id:' + codecs.encode(remote_id_option.remote_id, 'hex').decode('ascii')
            if remote_id in self.mapping:
                return self.mapping[remote_id]

        # Nothing found
        identifiers = filter(bool, [duid, remote_id, interface_id])
        logger.info("No assignment found for {}".format(', '.join(identifiers)))

        return Assignment(address=None, prefix=None)

    @staticmethod
    def parse_csv_file(csv_filename: str):
        """
        Read the assignments from the file specified in the configuration

        :param csv_filename: The filename of the CSV file
        """

        logger.debug("Loading assignments from {}".format(csv_filename))

        assignments = {}
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

                    # Validate id input
                    if row['id'].startswith('duid:'):
                        duid_hex = row['id'][5:]
                        duid_bytes = codecs.decode(duid_hex, 'hex')
                        length, duid = DUID.parse(duid_bytes, length=len(duid_bytes))

                    elif row['id'].startswith('interface-id:'):
                        interface_id_hex = row['id'][13:]
                        interface_id_bytes = codecs.decode(interface_id_hex, 'hex')

                    elif row['id'].startswith('remote-id:'):
                        remote_id_hex = row['id'][10:]
                        remote_id_bytes = codecs.decode(remote_id_hex, 'hex')

                    else:
                        raise ValueError("The id must start with duid:, interface-id: or remote-id: followed by a "
                                         "hex-encoded value")

                    # Store the original id
                    logger.debug("Loaded assignment for {}".format(row['id']))
                    assignments[row['id']] = Assignment(address=address, prefix=prefix)

                except KeyError:
                    raise configparser.Error("Assignment CSV must have columns 'id', 'address' and 'prefix'")
                except ValueError as e:
                    logger.error("Ignoring line {} with invalid value: {}".format(line, e))

        logger.info("Loaded {} assignments from CSV".format(len(assignments)))

        return assignments

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        # The option handler ID is our primary link prefix
        responsible_for_links = []
        try:
            prefix = IPv6Network(option_handler_id)
            responsible_for_links.append(prefix)
        except ValueError:
            raise configparser.ParsingError("The ID of [{}] must be the primary link prefix".format(section.name))

        # Add any extra prefixes
        additional_prefixes = section.get('additional-prefixes', '').split(' ')
        for additional_prefix in additional_prefixes:
            if not additional_prefix:
                continue

            try:
                prefix = IPv6Network(additional_prefix)
                responsible_for_links.append(prefix)
            except ValueError:
                raise configparser.ParsingError("'{}' is not a valid IPv6 prefix".format(additional_prefix))

        # Get the lifetimes
        address_preferred_lifetime = section.get('address-preferred-lifetime', 3600)
        address_valid_lifetime = section.get('address-valid-lifetime', 7200)
        prefix_preferred_lifetime = section.get('prefix-preferred-lifetime', 43200)
        prefix_valid_lifetime = section.get('prefix-valid-lifetime', 86400)

        csv_filename = section.get('assignments-file')

        return cls(csv_filename, responsible_for_links,
                   address_preferred_lifetime, address_valid_lifetime,
                   prefix_preferred_lifetime, prefix_valid_lifetime)


option_handler_registry.register(CSVBasedFixedAssignmentOptionHandler)
