"""
An option handler that assigns addresses based on DUID from a SQLite database
"""
import codecs
import logging
import os
import sqlite3
import time
from ipaddress import IPv6Network, IPv6Address

from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.option_handlers import OptionHandler
from dhcpkit.ipv6.option_handlers.fixed_assignment import FixedAssignmentOptionHandler
from dhcpkit.ipv6.option_handlers.utils import Assignment
from dhcpkit.ipv6.options import ClientIdOption, InterfaceIdOption
from dhcpkit.ipv6.server.config_parser import ConfigError
from dhcpkit.ipv6.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


def create_sqlite_from_csv():
    """
    Function to be called from the command line to convert a CSV based assignments file to a sqlite database.

    :return: exit code
    """
    import argparse
    import sys
    from dhcpkit.ipv6.option_handlers.csv import CSVBasedFixedAssignmentOptionHandler

    # Handle command line arguments
    parser = argparse.ArgumentParser(
        description="Assignments CSV to SQLite converter",
    )

    parser.add_argument("source", help="the source CSV file")
    parser.add_argument("destination", help="the destination SQLite file")
    parser.add_argument("-f", "--force", action="store_true", default=False, help="force removing old entries, even if "
                                                                                  "that means deleting more than 30%% "
                                                                                  "of the contents of the database")
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
    csv_mtime = os.stat(args.source).st_mtime_ns
    logger.debug("CSV file modification time: {} ns".format(csv_mtime))
    assignments = CSVBasedFixedAssignmentOptionHandler.parse_csv_file(args.source)

    logger.info("Writing assignments to SQLite file {}".format(args.destination))
    db = sqlite3.connect(args.destination, isolation_level='IMMEDIATE')
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS assignments ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "address TEXT, "
                "prefix TEXT, "
                "csv_mtime INT NOT NULL"
                ") WITHOUT ROWID")

    executed_in_transaction = 0
    for key, value in assignments:
        if executed_in_transaction == 0:
            # New transaction, check if we have a newer competing update process
            cur.execute("BEGIN IMMEDIATE")
            row = cur.execute("SELECT MAX(csv_mtime) FROM assignments").fetchone()
            if row[0] and row[0] > csv_mtime:
                logger.critical("Update with newer CSV file detected, aborting")
                return 1

        cur.execute("INSERT OR REPLACE INTO assignments (id, address, prefix, csv_mtime) VALUES (?, ?, ?, ?)",
                    (key, str(value.address), str(value.prefix), csv_mtime))

        executed_in_transaction += 1
        if executed_in_transaction >= 50:
            logger.debug("Interim commit to allow readers to access data")
            db.commit()
            time.sleep(0.05)
            executed_in_transaction = 0

    db.commit()

    cur.execute("SELECT COUNT(1) FROM assignments")
    total_count = cur.fetchone()[0]
    logger.info("Database contains {} assignments".format(total_count))

    cur.execute("SELECT COUNT(1) FROM assignments WHERE csv_mtime=?", [csv_mtime])
    updated_count = cur.fetchone()[0]
    logger.info("Added/updated {} assignments".format(updated_count))

    safety_limit = total_count * 0.7
    do_delete = True
    if updated_count < safety_limit:
        if args.force:
            logger.warning("Removing old entries, despite that being >30% of total")
        else:
            logger.warning("Not removing old entries, would delete >30% of total")
            do_delete = False

    if do_delete:
        cur.execute("DELETE FROM assignments WHERE csv_mtime<?", [csv_mtime])
        logger.info("Deleted {} old assignments".format(cur.rowcount))

    db.commit()

    if not do_delete:
        # Signal that we didn't delete
        return 2
    else:
        # Normal exit
        return 0


class SqliteBasedFixedAssignmentOptionHandler(FixedAssignmentOptionHandler):
    """
    Assign addresses and/or prefixes based on the contents of a Shelf file
    """

    def __init__(self, filename: str, responsible_for_links: [IPv6Network],
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param filename: The filename containing the SQLite database
        :param responsible_for_links: The IPv6 links that this handler is responsible for
        """
        super().__init__(responsible_for_links,
                         address_preferred_lifetime, address_valid_lifetime,
                         prefix_preferred_lifetime, prefix_valid_lifetime)

        self.db = sqlite3.connect(filename, check_same_thread=False)

    def get_assignment(self, bundle: TransactionBundle) -> Assignment:
        """
        Look up the assignment based on DUID, Interface-ID of the relay closest to the client and Remote-ID of the
        relay closest to the client, in that order.

        :param bundle: The transaction bundle
        :return: The assignment, if any
        """
        # Gather all possible IDs
        possible_ids = []

        # Look up based on DUID
        duid_option = bundle.request.get_option_of_type(ClientIdOption)
        duid = 'duid:' + codecs.encode(duid_option.duid.save(), 'hex').decode('ascii')
        possible_ids.append(duid)

        # Look up based on Interface-ID
        interface_id_option = bundle.incoming_relay_messages[0].get_option_of_type(InterfaceIdOption)
        interface_id = None
        if interface_id_option:
            interface_id = 'interface-id:' + codecs.encode(interface_id_option.interface_id, 'hex').decode('ascii')
            possible_ids.append(interface_id)

        # Look up based on Remote-ID
        remote_id_option = bundle.incoming_relay_messages[0].get_option_of_type(RemoteIdOption)
        remote_id = None
        if remote_id_option:
            remote_id = 'remote-id:{}:{}'.format(remote_id_option.enterprise_number,
                                                 codecs.encode(remote_id_option.remote_id, 'hex').decode('ascii'))
            possible_ids.append(remote_id)

        # Search
        placeholders = ', '.join(['?'] * len(possible_ids))
        query = "SELECT address, prefix FROM assignments WHERE id IN (" + placeholders + ") ORDER BY id LIMIT 1"
        results = self.db.execute(query, possible_ids).fetchone()
        if results:
            return Assignment(address=IPv6Address(results[0]), prefix=IPv6Network(results[1]))

        # Nothing found
        identifiers = filter(bool, [duid, remote_id, interface_id])
        logger.info("No assignment found for {}".format(', '.join(identifiers)))

        return Assignment(address=None, prefix=None)

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
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
            raise ConfigError("The ID of section must be the primary link prefix")

        # Add any extra prefixes
        additional_prefixes = section.get('additional-prefixes', '').split(' ')
        for additional_prefix in additional_prefixes:
            if not additional_prefix:
                continue

            try:
                prefix = IPv6Network(additional_prefix)
                responsible_for_links.append(prefix)
            except ValueError:
                raise ConfigError("'{}' is not a valid IPv6 prefix".format(additional_prefix))

        # Get the lifetimes
        address_preferred_lifetime = section.get('address-preferred-lifetime', 3600)
        address_valid_lifetime = section.get('address-valid-lifetime', 7200)
        prefix_preferred_lifetime = section.get('prefix-preferred-lifetime', 43200)
        prefix_valid_lifetime = section.get('prefix-valid-lifetime', 86400)

        sqlite_filename = section.get('assignments-file')

        return cls(sqlite_filename, responsible_for_links,
                   int(address_preferred_lifetime), int(address_valid_lifetime),
                   int(prefix_preferred_lifetime), int(prefix_valid_lifetime))
