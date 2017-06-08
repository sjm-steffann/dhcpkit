"""
SQLIte based implementation of a leasequery store
"""
import logging
import sqlite3
import time
from ipaddress import IPv6Address, summarize_address_range
from typing import Iterable, Iterator, List, Optional, Tuple

from dhcpkit.common.server.logging import DEBUG_HANDLING
from dhcpkit.ipv6.extensions.bulk_leasequery import QUERY_BY_LINK_ADDRESS, QUERY_BY_RELAY_ID, QUERY_BY_REMOTE_ID, \
    RelayIdOption
from dhcpkit.ipv6.extensions.leasequery import CLTTimeOption, ClientDataOption, LQQueryOption, OPTION_LQ_RELAY_DATA, \
    QUERY_BY_ADDRESS, QUERY_BY_CLIENT_ID, STATUS_MALFORMED_QUERY
from dhcpkit.ipv6.extensions.prefix_delegation import IAPrefixOption
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.messages import RebindMessage, RelayForwardMessage, RenewMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, IAAddressOption, Option, OptionRequestOption
from dhcpkit.ipv6.server.extensions.leasequery import LeasequeryStore
from dhcpkit.ipv6.server.handlers import ReplyWithLeasequeryError
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class LeasequerySqliteStore(LeasequeryStore):
    """
    A leasequery store using a SQLite database.
    """

    def __init__(self, filename: str):
        super().__init__()

        self.sqlite_filename = filename
        """Name of the database file"""

        self.db = None
        """Workers store the database connection here"""

        # Prepare the database in the main process, not separately in every worker
        self.create_tables()

        # These options are not allowed to be stored
        self.sensitive_options = []

    def worker_init(self, sensitive_options: Iterable[int]):
        """
        Worker initialisation: open database connection

        :param sensitive_options: The type-numbers of options that are not allowed to be stored
        """
        super().worker_init(sensitive_options)
        self.db = self.open_database()

    def open_database(self) -> sqlite3.Connection:
        """
        Open the database with the right settings.

        :return: The database connection
        """
        try:
            logger.info("Opening Leasequery SQLite database {}".format(self.sqlite_filename))
            db = sqlite3.connect(self.sqlite_filename, isolation_level="IMMEDIATE")
            db.execute("PRAGMA journal_mode = WAL")
            db.execute("PRAGMA foreign_keys = ON")

            db.row_factory = sqlite3.Row

            return db
        except sqlite3.Error as e:
            raise ValueError("Cannot open leasequery db: {}".format(e))

    def remember_lease(self, bundle: TransactionBundle):
        """
        Remember the leases in the given transaction bundle so they can be queried later.

        :param bundle: The transaction to remember
        """
        """
        Remember the leases in the given transaction bundle so they can be queried later.

        :param bundle: The transaction to remember
        """
        # Client identification fields
        client_id_option = bundle.request.get_option_of_type(ClientIdOption)
        client_id_str = self.encode_duid(client_id_option.duid)
        link_address_long = bundle.link_address.exploded

        # Gather addresses and prefixes
        address_leases = []
        prefix_leases = []
        if isinstance(bundle.request, (SolicitMessage, RequestMessage, RenewMessage, RebindMessage)):
            if self.is_accepted(bundle.response):
                # These messages update leases, so we need to process the result
                address_leases = list(self.get_address_leases(bundle))
                prefix_leases = list(self.get_prefix_leases(bundle))

        # Is this client interesting enough to create a record for if it doesn't exist?
        interesting_client = bool(address_leases or prefix_leases)

        # Get the row id for this client, creating it if necessary
        client_row_id = self.get_client_row_id(client_id_str, link_address_long, create=interesting_client)
        if client_row_id is None:
            # No client row, nothing else to do
            return

        # Keep track of when we last communicated with this client
        self.update_last_interaction(client_row_id, bundle.response.options, bundle.incoming_relay_messages[-1])

        # Keep track of where the last request came from
        self.replace_remote_ids(client_row_id, self.get_remote_ids(bundle))
        self.replace_relay_ids(client_row_id, self.get_relay_ids(bundle))

        # These messages update leases, so we need to process the result
        self.update_address_leases(client_row_id, address_leases)
        self.update_prefix_leases(client_row_id, prefix_leases)

    def find_leases(self, query: LQQueryOption) -> Tuple[int, Iterable[Tuple[IPv6Address, ClientDataOption]]]:
        """
        Find all leases that match the given query.

        :param query: The query
        :return: The number of leases and an iterator over tuples of link-address and corresponding client data
        """
        # Run everything in one transaction
        with self.db:
            if query.query_type == QUERY_BY_ADDRESS:
                client_row_ids = self.find_client_by_address(query)
            elif query.query_type == QUERY_BY_CLIENT_ID:
                client_row_ids = self.find_client_by_client_id(query)
            elif query.query_type == QUERY_BY_RELAY_ID:
                client_row_ids = self.find_client_by_relay_id(query)
            elif query.query_type == QUERY_BY_LINK_ADDRESS:
                client_row_ids = self.find_client_by_link_address(query)
            elif query.query_type == QUERY_BY_REMOTE_ID:
                client_row_ids = self.find_client_by_remote_id(query)
            else:
                # We can't handle this query
                return -1, []

            if not client_row_ids:
                # None found
                return 0, []

            # Generate records for these client IDs
            oro = query.get_option_of_type(OptionRequestOption)
            requested_options = oro.requested_options if oro else []
            return len(client_row_ids), self.generate_client_data_options(client_row_ids, requested_options)

    def generate_client_data_options(self, client_row_ids: Iterable[int], requested_options: Iterable[int]) \
            -> Iterable[Tuple[IPv6Address, ClientDataOption]]:
        """
        Create a generator for the data of the specified client rows/

        :param client_row_ids: The list of client rows what we are interested in
        :param requested_options: Option types explicitly requested by the leasequery client
        :return: The client data options for those rows
        """
        # Some helper variables
        relay_data_requested = OPTION_LQ_RELAY_DATA in requested_options
        extra_data_requested = any([requested_option for requested_option in requested_options
                                    if requested_option != OPTION_LQ_RELAY_DATA])

        # Determine which columns we are interested in, no point in dragging in large chunks of data for nothing
        selected_columns = ["id", "client_id", "link_address", "last_interaction"]
        if extra_data_requested:
            selected_columns.append("options")
        if relay_data_requested:
            selected_columns.append("relay_data")

        now = int(time.time())
        client_cur = self.db.execute("SELECT {} FROM clients WHERE id IN ({})".format(
            ', '.join(selected_columns),
            ', '.join(map(str, client_row_ids))))
        for client_row in client_cur:
            # This is the first part of the tuple we yield
            link_address = IPv6Address(client_row['link_address'])

            # Reconstruct the DUID of the client
            duid = self.decode_duid(client_row['client_id'])
            client_id_option = ClientIdOption(duid)

            # How long ago did we speak to this client?
            clt_option = CLTTimeOption(now - client_row['last_interaction'])

            # Get the requested options
            if extra_data_requested:
                stored_options = self.decode_options(client_row['options'])
                stored_options = self.filter_requested_options(stored_options, requested_options)
            else:
                stored_options = []

            # Get the relay data
            if relay_data_requested:
                relay_data_option = self.build_relay_data_option_from_relay_data(client_row['relay_data'])
            else:
                relay_data_option = None

            # Build all the options for this client
            options = [client_id_option, clt_option] + stored_options  # type: List[Option]
            if relay_data_option:
                options.append(relay_data_option)

            # Add all addresses
            address_cur = self.db.execute("SELECT address, preferred_lifetime_end, valid_lifetime_end, options "
                                          "FROM addresses WHERE client_fk=? AND valid_lifetime_end>?",
                                          (client_row['id'], now))
            for address_row in address_cur:
                options.append(IAAddressOption(address=IPv6Address(address_row['address']),
                                               preferred_lifetime=max(0, address_row['preferred_lifetime_end'] - now),
                                               valid_lifetime=max(0, address_row['valid_lifetime_end'] - now),
                                               options=self.decode_options(address_row['options'])))

            # Add all prefixes
            prefix_cur = self.db.execute("SELECT first_address, last_address, "
                                         "preferred_lifetime_end, valid_lifetime_end, options "
                                         "FROM prefixes WHERE client_fk=? AND valid_lifetime_end>?",
                                         (client_row['id'], now))
            for prefix_row in prefix_cur:
                prefixes = list(summarize_address_range(
                    IPv6Address(prefix_row['first_address']),
                    IPv6Address(prefix_row['last_address'])
                ))
                if len(prefixes) != 1:
                    logger.error("Ignoring invalid prefix range in leasequery db: {} - {}".format(
                        prefix_row['first_address'], prefix_row['last_address']))
                    continue

                options.append(IAPrefixOption(prefix=prefixes[0],
                                              preferred_lifetime=max(0, prefix_row['preferred_lifetime_end'] - now),
                                              valid_lifetime=max(0, prefix_row['valid_lifetime_end'] - now),
                                              options=self.decode_options(prefix_row['options'])))

            # We got everything, yield it
            yield link_address, ClientDataOption(options)

    def find_client_by_address(self, query: LQQueryOption) -> List[int]:
        """
        Get the row ids of the clients we want to return.

        :param query: The query
        :return: A list of row ids
        """
        # Get the requested address from the query
        address_option = query.get_option_of_type(IAAddressOption)
        if not address_option:
            raise ReplyWithLeasequeryError(STATUS_MALFORMED_QUERY, "Address queries must contain an address")

        address = address_option.address.exploded

        if query.link_address.is_unspecified:
            cur = self.db.execute("SELECT client_fk FROM addresses WHERE address=?"
                                  " UNION "
                                  "SELECT client_fk FROM prefixes WHERE ? BETWEEN first_address AND last_address",
                                  (address, address))
            return [row['client_fk'] for row in cur]
        else:
            cur = self.db.execute(
                "SELECT id FROM clients WHERE link_address=? AND ("
                "id IN (SELECT client_fk FROM addresses WHERE address=?)"
                " OR "
                "id IN (SELECT client_fk FROM prefixes WHERE ? BETWEEN first_address AND last_address)"
                ")",
                (query.link_address.exploded, address, address)
            )
            return [row['id'] for row in cur]

    def find_client_by_client_id(self, query: LQQueryOption) -> List[int]:
        """
        Get the row ids of the clients we want to return.

        :param query: The query
        :return: A list of row ids
        """
        # Get the requested client ID from the query
        client_id_option = query.get_option_of_type(ClientIdOption)
        if not client_id_option:
            raise ReplyWithLeasequeryError(STATUS_MALFORMED_QUERY, "Client-ID queries must contain a client ID")

        client_id_str = self.encode_duid(client_id_option.duid)

        if query.link_address.is_unspecified:
            cur = self.db.execute("SELECT id FROM clients WHERE client_id=?",
                                  (client_id_str,))
        else:
            cur = self.db.execute("SELECT id FROM clients WHERE client_id=? AND link_address=?",
                                  (client_id_str, query.link_address.exploded))

        return [row['id'] for row in cur]

    def find_client_by_relay_id(self, query: LQQueryOption) -> List[int]:
        """
        Get the row ids of the clients we want to return.

        :param query: The query
        :return: A list of row ids
        """
        # Get the requested relay ID from the query
        relay_id_option = query.get_option_of_type(RelayIdOption)
        if not relay_id_option:
            raise ReplyWithLeasequeryError(STATUS_MALFORMED_QUERY, "Relay-ID queries must contain a relay ID")

        relay_id_str = self.encode_duid(relay_id_option.duid)

        if query.link_address.is_unspecified:
            cur = self.db.execute("SELECT client_fk FROM relay_ids WHERE relay_id=?",
                                  (relay_id_str,))

            return [row['client_fk'] for row in cur]
        else:
            cur = self.db.execute("SELECT id FROM clients "
                                  "WHERE link_address=? AND id IN (SELECT client_fk FROM relay_ids WHERE relay_id=?)",
                                  (query.link_address.exploded, relay_id_str))

            return [row['id'] for row in cur]

    def find_client_by_link_address(self, query: LQQueryOption) -> List[int]:
        """
        Get the row ids of the clients we want to return.

        :param query: The query
        :return: A list of row ids
        """
        if query.link_address.is_unspecified:
            # Query by link-address with an unspecified address, I guess that means all leases
            cur = self.db.execute("SELECT id FROM clients")
        else:
            cur = self.db.execute("SELECT id FROM clients WHERE link_address=?",
                                  (query.link_address.exploded,))

        return [row['id'] for row in cur]

    def find_client_by_remote_id(self, query: LQQueryOption) -> List[int]:
        """
        Get the row ids of the clients we want to return.

        :param query: The query
        :return: A list of row ids
        """
        # Get the requested remote ID from the query
        remote_id_option = query.get_option_of_type(RemoteIdOption)
        if not remote_id_option:
            raise ReplyWithLeasequeryError(STATUS_MALFORMED_QUERY, "Remote-ID queries must contain a remote ID")

        remote_id_str = self.encode_remote_id(remote_id_option)

        if query.link_address.is_unspecified:
            cur = self.db.execute("SELECT client_fk FROM relay_ids WHERE relay_id=?",
                                  (remote_id_str,))

            return [row['client_fk'] for row in cur]
        else:
            cur = self.db.execute("SELECT id FROM clients "
                                  "WHERE link_address=? AND id IN (SELECT client_fk FROM relay_ids WHERE relay_id=?)",
                                  (query.link_address.exploded, remote_id_str))

            return [row['id'] for row in cur]

    def get_client_row_id(self, client_id_str: str, link_address_long: str, create: bool = True) -> Optional[int]:
        """
        Get the client's row id, creating the client row if necessary.

        :param client_id_str: The DUID of the client as a string
        :param link_address_long: The fully expanded link address
        :param create: Should we create this record if it doesn't exist?
        :return: The row id
        """
        with self.db:
            if create:
                # First make sure we have the client in our database
                cur = self.db.execute("INSERT OR IGNORE INTO clients(client_id, link_address) "
                                      "VALUES (?, ?)", (client_id_str, link_address_long))
                if cur.rowcount == 1 and cur.lastrowid > 0:
                    # We already know the new id
                    return cur.lastrowid

            # We don't know the id yet, go get it
            cur = self.db.execute("SELECT id FROM clients WHERE client_id=? AND link_address=?",
                                  (client_id_str, link_address_long))
            row = cur.fetchone()
            return row['id'] if row else None

    def update_last_interaction(self, client_row_id: int, options: Iterable[Option],
                                relay_chain: Optional[RelayForwardMessage]):
        """
        Keep track of when we last communicated with this client.

        :param client_row_id: The row id of the client
        :param options: Options of the last response
        :param relay_chain: The incoming relay messages
        """
        self.db.execute("UPDATE clients SET last_interaction=?, options=?, relay_data=? WHERE id=?",
                        (int(time.time()), self.encode_options(options), self.encode_relay_messages(relay_chain),
                         client_row_id,))

    def replace_remote_ids(self, client_row_id: int, remote_ids: Iterable[str]):
        """
        Replace the existing remote-id records with the remote-ids provided.

        :param client_row_id: The id of the client record
        :param remote_ids: The new remote-ids
        """
        remote_ids = list(remote_ids)
        with self.db:
            # First see what we already have
            rows = self.db.execute("SELECT remote_id FROM remote_ids WHERE client_fk=?", (client_row_id,))
            for row in rows:
                if row['remote_id'] in remote_ids:
                    # New remote-id is already in the database, no need to do anything
                    logger.log(DEBUG_HANDLING, "Keeping existing row in remote_ids "
                                               "for client {} remote-id {}".format(client_row_id, row['remote_id']))
                    remote_ids.remove(row['remote_id'])
                else:
                    # Record in the database is not what we want, delete it
                    logger.log(DEBUG_HANDLING, "Deleting row from remote_ids "
                                               "for client {} remote-id {}".format(client_row_id, row['remote_id']))
                    self.db.execute("DELETE FROM remote_ids "
                                    "WHERE client_fk=? AND remote_id=?", (client_row_id, row['remote_id']))

            # Now create the ones we don't already have
            for remote_id in remote_ids:
                # Ignore if it already exists. Shouldn't happen, but better safe than sorry
                logger.log(DEBUG_HANDLING, "Insert row into remote_ids "
                                           "for client {} remote-id {}".format(client_row_id, remote_id))
                self.db.execute("INSERT OR IGNORE INTO remote_ids (client_fk, remote_id) "
                                "VALUES (?, ?)", (client_row_id, remote_id))

    def replace_relay_ids(self, client_row_id: int, relay_ids: Iterable[str]):
        """
        Replace the existing relay-id records with the relay-ids provided.

        :param client_row_id: The id of the client record
        :param relay_ids: The new relay-ids
        """
        relay_ids = list(relay_ids)
        with self.db:
            # First see what we already have
            rows = self.db.execute("SELECT relay_id FROM relay_ids WHERE client_fk=?", (client_row_id,))
            for row in rows:
                if row['relay_id'] in relay_ids:
                    # New relay-id is already in the database, no need to do anything
                    logger.log(DEBUG_HANDLING, "Keeping existing row in relay_ids "
                                               "for client {} relay-id {}".format(client_row_id, row['relay_id']))
                    relay_ids.remove(row['relay_id'])
                else:
                    # Record in the database is not what we want, delete it
                    logger.log(DEBUG_HANDLING, "Deleting row from relay_ids "
                                               "for client {} relay-id {}".format(client_row_id, row['relay_id']))
                    self.db.execute("DELETE FROM relay_ids "
                                    "WHERE client_fk=? AND relay_id=?", (client_row_id, row['relay_id']))

            # Now create the ones we don't already have
            for relay_id in relay_ids:
                # Ignore if it already exists. Shouldn't happen, but better safe than sorry
                logger.log(DEBUG_HANDLING, "Insert row into relay_ids "
                                           "for client {} relay-id {}".format(client_row_id, relay_id))
                self.db.execute("INSERT OR IGNORE INTO relay_ids (client_fk, relay_id) "
                                "VALUES (?, ?)", (client_row_id, relay_id))

    def update_address_leases(self, client_row_id: int, address_leases: Iterator[IAAddressOption]):
        """
        Update address leases in the database and remove expired ones.

        :param client_row_id: The id of the client record
        :param address_leases: The updated leases to record
        """

        # Build a mapping from the input for easier checking
        new_leases = {}
        for address_lease in address_leases:
            new_leases[address_lease.address.exploded] = address_lease

        now = int(time.time())

        with self.db:
            # Remove all rows that contain the same address for another client, this newer one overrides it
            for address, new_lease in new_leases.items():
                self.db.execute("DELETE FROM addresses WHERE address=? AND client_fk<>?", (address, client_row_id))

            # First see what we already have
            rows = self.db.execute("SELECT address FROM addresses WHERE client_fk=?", (client_row_id,))
            for row in rows:
                if row['address'] in new_leases:
                    # New relay-id is already in the database, update the lifetimes and options
                    new_lease = new_leases[row['address']]

                    logger.log(DEBUG_HANDLING, "Updating existing row in addresses "
                                               "for client {} address {}".format(client_row_id, new_lease.address))
                    self.db.execute("UPDATE addresses SET preferred_lifetime_end=?, valid_lifetime_end=?, options=? "
                                    "WHERE client_fk=? AND address=?",
                                    (now + new_lease.preferred_lifetime,
                                     now + new_lease.valid_lifetime,
                                     self.encode_options(new_lease.options),
                                     client_row_id, row['address']))

                    del new_leases[row['address']]

            # Now create the ones we don't already have
            for address, new_lease in new_leases.items():
                # Ignore if it already exists. Shouldn't happen, but better safe than sorry
                logger.log(DEBUG_HANDLING, "Insert row into addresses "
                                           "for client {} address {}".format(client_row_id, new_lease.address))
                self.db.execute("INSERT OR IGNORE INTO addresses (client_fk, address, preferred_lifetime_end, "
                                "valid_lifetime_end, options) VALUES (?, ?, ?, ?, ?)",
                                (client_row_id, address,
                                 now + new_lease.preferred_lifetime,
                                 now + new_lease.valid_lifetime,
                                 self.encode_options(new_lease.options)))

            # Remove all expired rows from the database
            logger.log(DEBUG_HANDLING, "Deleting expired rows from addresses for {}".format(client_row_id, ))
            self.db.execute("DELETE FROM addresses "
                            "WHERE client_fk=? AND valid_lifetime_end<?", (client_row_id, now))

    def update_prefix_leases(self, client_row_id: int, prefix_leases: Iterator[IAPrefixOption]):
        """
        Update prefix leases in the database and remove expired ones.

        :param client_row_id: The id of the client record
        :param prefix_leases: The updated leases to record
        """

        # Build a mapping from the input for easier checking
        new_leases = {}
        for prefix_lease in prefix_leases:
            new_leases[(prefix_lease.prefix[0].exploded, prefix_lease.prefix[-1].exploded)] = prefix_lease

        now = int(time.time())

        with self.db:
            # Remove all rows that contain overlapping prefixes for another client, this newer one overrides it
            for prefix_idx, new_lease in new_leases.items():
                first_address, last_address = prefix_idx
                self.db.execute("DELETE FROM prefixes WHERE first_address<=? AND last_address>=? AND client_fk<>?",
                                (last_address, first_address, client_row_id))

            # First see what we already have
            rows = self.db.execute("SELECT first_address, last_address FROM prefixes "
                                   "WHERE client_fk=?", (client_row_id,))
            for row in rows:
                prefix_idx = (row['first_address'], row['last_address'])
                if prefix_idx in new_leases:
                    # New relay-id is already in the database, update the lifetimes and options
                    new_lease = new_leases[prefix_idx]

                    logger.log(DEBUG_HANDLING, "Updating existing row in prefixes "
                                               "for client {} prefix {}".format(client_row_id, new_lease.prefix))
                    self.db.execute("UPDATE prefixes SET preferred_lifetime_end=?, valid_lifetime_end=?, options=? "
                                    "WHERE client_fk=? AND first_address=? AND last_address=?",
                                    (now + new_lease.preferred_lifetime,
                                     now + new_lease.valid_lifetime,
                                     self.encode_options(new_lease.options),
                                     client_row_id, prefix_idx[0], prefix_idx[1]))
                    del new_leases[prefix_idx]

            # Now create the ones we don't already have
            for prefix_idx, new_lease in new_leases.items():
                # Ignore if it already exists. Shouldn't happen, but better safe than sorry
                logger.log(DEBUG_HANDLING, "Insert row into prefixes "
                                           "for client {} prefix {}".format(client_row_id, new_lease.prefix))
                self.db.execute("INSERT OR IGNORE INTO prefixes (client_fk, first_address, last_address, "
                                "preferred_lifetime_end, valid_lifetime_end, options) VALUES (?, ?, ?, ?, ?, ?)",
                                (client_row_id, prefix_idx[0], prefix_idx[1],
                                 now + new_lease.preferred_lifetime,
                                 now + new_lease.valid_lifetime,
                                 self.encode_options(new_lease.options)))

            # Remove all expired rows from the database
            logger.log(DEBUG_HANDLING, "Deleting expired rows from prefixes for {}".format(client_row_id, ))
            self.db.execute("DELETE FROM prefixes "
                            "WHERE client_fk=? AND valid_lifetime_end<?", (client_row_id, now))

    def create_tables(self):
        """
        Create the tables required for this leasequery implementation
        """
        db = self.open_database()
        user_version = 1

        with db:
            # Check if the user version is recent enough
            cur = db.execute("PRAGMA user_version")
            current_version = cur.fetchone()[0]

            if current_version < user_version:
                logger.debug("Upgrading or removing old versions of the leasequery database tables")

                if current_version < 1:
                    # 0 is an empty database, nothing to remove
                    pass

            logger.debug("Creating leasequery database tables where necessary")

            # Generic rules (because SQLite doesn't support INET/CIDR data types):
            # - All IPv6 addresses are written without any compression in lower case
            #   2001:db8 would be stored as 2001:0db8:0000:0000:0000:0000:0000:0001
            #   This makes string searching on IP ranges easier, i.e.
            #   WHERE '2001:0db8:0000:0000:0000:0000:0000:0001' BETWEEN first_address AND last_address

            # Rules for this table:
            # - client_id is the hex representation of the client's DUID in lower case
            # - the options are stored in binary on-the-wire representation and concatenated
            # - last_interaction is the UNIX timestamp in UTC
            # - relay_data is the binary on-the-wire representation of a RelayForwardMessage, if any
            #   The outer relay message (the one added internally by the server) is included for the peer-address
            db.execute("CREATE TABLE IF NOT EXISTS clients ("
                       "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                       "client_id TEXT NOT NULL, "
                       "link_address TEXT NOT NULL, "
                       "options BLOB NOT NULL DEFAULT '', "
                       "last_interaction INTEGER NOT NULL DEFAULT -1, "
                       "relay_data BLOB NOT NULL DEFAULT '', "
                       "UNIQUE (client_id, link_address)"
                       ")")

            db.execute("CREATE INDEX IF NOT EXISTS clients_client_id ON clients(client_id, link_address)")
            db.execute("CREATE INDEX IF NOT EXISTS clients_link_address ON clients(link_address)")

            # Rules for this table:
            # - the options are stored in binary on-the-wire representation and concatenated
            # - lifetimes are stored as deadlines in UNIX timestamps in UTC
            db.execute("CREATE TABLE IF NOT EXISTS addresses ("
                       "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                       "address TEXT NOT NULL, "
                       "preferred_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                       "valid_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                       "options BLOB NOT NULL DEFAULT '', "
                       "UNIQUE (client_fk, address)"
                       ")")

            db.execute("CREATE INDEX IF NOT EXISTS addresses_address ON addresses(address)")
            db.execute("CREATE INDEX IF NOT EXISTS addresses_client_fk ON addresses(client_fk)")

            # Rules for this table:
            # - Prefixes are stored by first and last address so we can search the range:
            #   WHERE '2001:0db8:0000:0000:0000:0000:0000:0001' BETWEEN first_address AND last_address
            # - the options are stored in binary on-the-wire representation and concatenated
            # - lifetimes are stored as deadlines in UNIX timestamps in UTC
            db.execute("CREATE TABLE IF NOT EXISTS prefixes ("
                       "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                       "first_address TEXT NOT NULL, "
                       "last_address TEXT NOT NULL, "
                       "preferred_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                       "valid_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                       "options BLOB NOT NULL DEFAULT '', "
                       "UNIQUE (client_fk, first_address, last_address)"
                       ")")

            db.execute("CREATE INDEX IF NOT EXISTS prefixes_range ON prefixes(first_address, last_address)")
            db.execute("CREATE INDEX IF NOT EXISTS prefixes_client_fk ON prefixes(client_fk)")

            # Rules for this table:
            # - remote_id is the hex representation of the remote-id in lower case
            db.execute("CREATE TABLE IF NOT EXISTS remote_ids ("
                       "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                       "remote_id TEXT NOT NULL, "
                       "UNIQUE (client_fk, remote_id)"
                       ")")

            db.execute("CREATE INDEX IF NOT EXISTS remote_ids_remote_id ON remote_ids(remote_id)")
            db.execute("CREATE INDEX IF NOT EXISTS remote_ids_client_fk ON remote_ids(client_fk)")

            # Rules for this table:
            # - relay_id is the hex representation of the relay's DUID in lower case
            db.execute("CREATE TABLE IF NOT EXISTS relay_ids ("
                       "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                       "relay_id TEXT NOT NULL, "
                       "UNIQUE (client_fk, relay_id)"
                       ")")

            db.execute("CREATE INDEX IF NOT EXISTS relay_ids_relay_id ON relay_ids(relay_id)")
            db.execute("CREATE INDEX IF NOT EXISTS relay_ids_client_fk ON relay_ids(client_fk)")

            db.execute("PRAGMA user_version={}".format(user_version))

        with db:
            # Cleaning up
            logger.debug("Cleaning up old records from the database and vacuuming")

            now = int(time.time())

            db.execute("DELETE FROM addresses WHERE preferred_lifetime_end<? AND valid_lifetime_end<?", (now, now))
            db.execute("DELETE FROM prefixes WHERE preferred_lifetime_end<? AND valid_lifetime_end<?", (now, now))
            db.execute("DELETE FROM clients WHERE NOT EXISTS(SELECT 1 FROM addresses WHERE client_fk=clients.id) "
                       "AND NOT EXISTS(SELECT 1 FROM prefixes WHERE client_fk=clients.id);")

            db.execute("VACUUM")

        db.close()
