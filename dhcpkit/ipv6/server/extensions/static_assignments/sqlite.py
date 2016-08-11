"""
An option handler that assigns addresses based on DUID from a SQLite database
"""
import codecs
import logging
import os
import sqlite3
import time
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.extensions.linklayer_id import LinkLayerIdOption
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.extensions.subscriber_id import SubscriberIdOption
from dhcpkit.ipv6.options import ClientIdOption, InterfaceIdOption
from dhcpkit.ipv6.server.extensions.static_assignments import Assignment, StaticAssignmentHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


def build_sqlite() -> int:
    """
    Function to be called from the command line to convert a CSV based assignments file to a sqlite database.
    :return: exit code
    """
    import argparse
    import sys
    from dhcpkit.ipv6.server.extensions.static_assignments.csv import CSVStaticAssignmentHandler

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
    assignments = CSVStaticAssignmentHandler.parse_csv_file(args.source)

    logger.info("Writing assignments to SQLite file {}".format(args.destination))
    db = sqlite3.connect(args.destination, isolation_level='IMMEDIATE')
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS assignments ("
                "id TEXT NOT NULL PRIMARY KEY, "
                "address TEXT, "
                "prefix TEXT, "
                "csv_mtime INT NOT NULL"
                ") WITHOUT ROWID")

    try:
        executed_in_transaction = 0
        for key, value in assignments:
            if executed_in_transaction == 0:
                # New transaction, check if we have a newer competing update process
                cur.execute("BEGIN IMMEDIATE")
                row = cur.execute("SELECT MAX(csv_mtime) FROM assignments").fetchone()
                if row[0] and row[0] > csv_mtime:
                    logger.critical("Update with newer CSV file detected, aborting")
                    return 1

            address = value.address and str(value.address) or None
            prefix = value.prefix and str(value.prefix) or None

            cur.execute("INSERT OR REPLACE INTO assignments (id, address, prefix, csv_mtime) VALUES (?, ?, ?, ?)",
                        (key, address, prefix, csv_mtime))

            executed_in_transaction += 1
            if executed_in_transaction >= 50:
                logger.debug("Interim commit to allow readers to access data")
                db.commit()
                time.sleep(0.05)
                executed_in_transaction = 0

        db.commit()

    except ValueError as e:
        logger.critical(e)
        return 1

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


class SqliteStaticAssignmentHandler(StaticAssignmentHandler):
    """
    Assign addresses and/or prefixes based on the contents of a Shelf file
    """

    def __init__(self, filename: str,
                 address_preferred_lifetime: int, address_valid_lifetime: int,
                 prefix_preferred_lifetime: int, prefix_valid_lifetime: int):
        """
        Initialise the mapping. This handler will respond to clients on responsible_for_links and assume that all
        addresses in the mapping are appropriate for on those links.

        :param filename: The filename containing the SQLite database
        """
        super().__init__(address_preferred_lifetime, address_valid_lifetime,
                         prefix_preferred_lifetime, prefix_valid_lifetime)

        self.sqlite_filename = filename
        self.db = None

    def __str__(self):
        return "{} from {}".format(self.__class__.__name__, self.sqlite_filename)

    def worker_init(self):
        """
        Open the SQLite database in each worker
        """
        logger.info("Opening SQLite database {}".format(self.sqlite_filename))
        self.db = sqlite3.connect(self.sqlite_filename, check_same_thread=False)

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
        if interface_id_option:
            interface_id = 'interface-id:' + codecs.encode(interface_id_option.interface_id, 'hex').decode('ascii')
            possible_ids.append(interface_id)

        # Look up based on Remote-ID
        remote_id_option = bundle.incoming_relay_messages[0].get_option_of_type(RemoteIdOption)
        if remote_id_option:
            remote_id = 'remote-id:{}:{}'.format(remote_id_option.enterprise_number,
                                                 codecs.encode(remote_id_option.remote_id, 'hex').decode('ascii'))
            possible_ids.append(remote_id)

        # Look up based on Subscriber-ID
        subscriber_id_option = bundle.incoming_relay_messages[0].get_option_of_type(SubscriberIdOption)
        if subscriber_id_option:
            subscriber_id = 'subscriber-id:{}'.format(
                codecs.encode(subscriber_id_option.subscriber_id, 'hex').decode('ascii')
            )
            possible_ids.append(subscriber_id)

        # Look up based on LinkLayer-ID
        linklayer_id_option = bundle.incoming_relay_messages[0].get_option_of_type(LinkLayerIdOption)
        if linklayer_id_option:
            linklayer_id = 'linklayer-id:{}:{}'.format(
                linklayer_id_option.link_layer_type,
                codecs.encode(linklayer_id_option.link_layer_address, 'hex').decode('ascii')
            )
            possible_ids.append(linklayer_id)

        # Search
        placeholders = ', '.join(['?'] * len(possible_ids))
        query = "SELECT address, prefix FROM assignments WHERE id IN (" + placeholders + ") ORDER BY id LIMIT 1"
        results = self.db.execute(query, possible_ids).fetchone()
        if results:
            address = results[0] and IPv6Address(results[0]) or None
            prefix = results[1] and IPv6Network(results[1]) or None

            return Assignment(address=address, prefix=prefix)

        # Nothing found
        return Assignment(address=None, prefix=None)
