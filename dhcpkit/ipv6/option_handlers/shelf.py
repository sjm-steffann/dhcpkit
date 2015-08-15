"""
An option handler that assigns addresses based on DUID from a shelf file
"""
import codecs
import configparser
from ipaddress import IPv6Network
import logging
import shelve

from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.option_handlers import OptionHandler, register_option_handler
from dhcpkit.ipv6.option_handlers.fixed_assignment import FixedAssignmentOptionHandler
from dhcpkit.ipv6.option_handlers.utils import Assignment
from dhcpkit.ipv6.options import ClientIdOption, InterfaceIdOption

logger = logging.getLogger(__name__)


def create_shelf_from_csv():
    """
    Function to be called from the command line to convert a CSV based assignments file to a shelf.

    :return: exit code
    """
    import argparse
    import sys
    from dhcpkit.ipv6.option_handlers.csv import CSVBasedFixedAssignmentOptionHandler

    # Handle command line arguments
    parser = argparse.ArgumentParser(
        description="Assignments CSV to Shelf converter",
    )

    parser.add_argument("source", help="the source CSV file")
    parser.add_argument("destination", help="the destination shelf file")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")

    args = parser.parse_args()

    # Our logger is the root logger now
    global logger
    logger = logging.getLogger()

    # Don't filter on level in the root logger
    logger.setLevel(logging.NOTSET)

    # Output to sys.stdout
    stdout_handler = logging.StreamHandler(stream=sys.stdout)

    # Set level according to verbosity
    if args.verbosity >= 3:
        stdout_handler.setLevel(logging.DEBUG)
    elif args.verbosity == 2:
        stdout_handler.setLevel(logging.INFO)
    elif args.verbosity >= 1:
        stdout_handler.setLevel(logging.WARNING)
    else:
        stdout_handler.setLevel(logging.CRITICAL)

    logger.addHandler(stdout_handler)

    logger.info("Reading assignments from CSV file {}".format(args.source))
    assignments = CSVBasedFixedAssignmentOptionHandler.parse_csv_file(args.source)

    logger.info("Writing assignments to shelf file {}".format(args.destination))
    with shelve.open(args.destination, 'n') as shelf:
        for key, value in assignments:
            shelf[key] = value
            logger.debug("Stored assignment for {} in shelf".format(key))

        logger.info("Wrote {} assignments".format(len(shelf)))


class ShelfBasedFixedAssignmentOptionHandler(FixedAssignmentOptionHandler):
    """
    Assign addresses and/or prefixes based on the contents of a Shelf file
    """

    def __init__(self, filename: str, responsible_for_links: [IPv6Network],
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param filename: The filename containing the shelf data
        :param responsible_for_links: The IPv6 links that this handler is responsible for
        """
        super().__init__(responsible_for_links,
                         address_preferred_lifetime, address_valid_lifetime,
                         prefix_preferred_lifetime, prefix_valid_lifetime)

        self.mapping = shelve.open(filename, 'r')

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
        interface_id_option = bundle.incoming_relay_messages[0].get_option_of_type(InterfaceIdOption)
        interface_id = None
        if interface_id_option:
            interface_id = 'interface-id:' + codecs.encode(interface_id_option.interface_id, 'hex').decode('ascii')
            if interface_id in self.mapping:
                return self.mapping[interface_id]

        # Look up based on Remote-ID
        remote_id_option = bundle.incoming_relay_messages[0].get_option_of_type(RemoteIdOption)
        remote_id = None
        if remote_id_option:
            remote_id = 'remote-id:{}:{}'.format(remote_id_option.enterprise_number,
                                                 codecs.encode(remote_id_option.remote_id, 'hex').decode('ascii'))
            if remote_id in self.mapping:
                return self.mapping[remote_id]

        # Nothing found
        identifiers = filter(bool, [duid, remote_id, interface_id])
        logger.info("No assignment found for {}".format(', '.join(identifiers)))

        return Assignment(address=None, prefix=None)

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
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
        address_preferred_lifetime = section.getint('address-preferred-lifetime', 3600)
        address_valid_lifetime = section.getint('address-valid-lifetime', 7200)
        prefix_preferred_lifetime = section.getint('prefix-preferred-lifetime', 43200)
        prefix_valid_lifetime = section.getint('prefix-valid-lifetime', 86400)

        shelf_filename = section.get('assignments-file')

        return cls(shelf_filename, responsible_for_links,
                   address_preferred_lifetime, address_valid_lifetime,
                   prefix_preferred_lifetime, prefix_valid_lifetime)


register_option_handler(ShelfBasedFixedAssignmentOptionHandler)
