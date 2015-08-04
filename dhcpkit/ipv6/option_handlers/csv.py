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
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.option_handlers.fixed_duid import FixedDUIDOptionHandler
from dhcpkit.ipv6.option_handlers.utils import Assignment

logger = logging.getLogger(__name__)


class CSVBasedDUIDOptionHandler(FixedDUIDOptionHandler):
    """
    Assign addresses and/or prefixes based on the contents of a CSV file
    """

    def __init__(self, filename: str, responsible_for_links: [IPv6Network],
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):

        mapping = self.parse_csv_file(filename)
        super().__init__(mapping, responsible_for_links,
                         address_preferred_lifetime, address_valid_lifetime,
                         prefix_preferred_lifetime, prefix_valid_lifetime)

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

                    duid_hex = row['duid']
                    duid_bytes = codecs.decode(duid_hex, 'hex')
                    length, duid = DUID.parse(duid_bytes, length=len(duid_bytes))

                    logger.debug("Loaded assignment for {!r}".format(duid))
                    assignments[duid] = Assignment(address=address, prefix=prefix)
                except KeyError:
                    raise configparser.Error("Assignment CSV must have columns 'duid', 'address' and 'prefix'")
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


option_handler_registry.register(CSVBasedDUIDOptionHandler)
