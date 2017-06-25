"""
Testing of the SQLite LeaseQuery store
"""
import os
import sqlite3
import time
import unittest
from ipaddress import IPv6Address
from tempfile import TemporaryDirectory

from typing import Iterable, Type

from dhcpkit.ipv6.duids import LinkLayerDUID
from dhcpkit.ipv6.extensions.bulk_leasequery import QUERY_BY_LINK_ADDRESS, QUERY_BY_RELAY_ID, QUERY_BY_REMOTE_ID, \
    RelayIdOption
from dhcpkit.ipv6.extensions.dns import OPTION_DNS_SERVERS, RecursiveNameServersOption
from dhcpkit.ipv6.extensions.leasequery import CLTTimeOption, ClientDataOption, LQQueryOption, LQRelayDataOption, \
    OPTION_LQ_RELAY_DATA, QUERY_BY_ADDRESS, QUERY_BY_CLIENT_ID
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.messages import RelayForwardMessage, SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, ElapsedTimeOption, IAAddressOption, IANAOption, InterfaceIdOption, \
    Option, OptionRequestOption, RelayMessageOption
from dhcpkit.ipv6.server.extensions.leasequery.sqlite import LeasequerySqliteStore
from dhcpkit.ipv6.server.handlers import ReplyWithLeasequeryError
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.tests.ipv6.messages.test_confirm_message import confirm_message
from dhcpkit.tests.ipv6.messages.test_reply_message import reply_message
from dhcpkit.utils import normalise_hex


class LeasequerySqliteStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.relayed_solicit_message = RelayForwardMessage(
            hop_count=1,
            link_address=IPv6Address('2001:db8:ffff:1::1'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=RelayForwardMessage(
                    hop_count=0,
                    link_address=IPv6Address('::'),
                    peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
                    options=[
                        RelayMessageOption(relayed_message=SolicitMessage(
                            transaction_id=bytes.fromhex('f350d6'),
                            options=[
                                ElapsedTimeOption(elapsed_time=0),
                                ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                                  link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                                IANAOption(iaid=bytes.fromhex('c43cb2f1')),
                                IAPDOption(iaid=bytes.fromhex('c43cb2f1')),
                                OptionRequestOption(requested_options=[
                                    OPTION_DNS_SERVERS,
                                ]),
                            ],
                        )),
                        InterfaceIdOption(interface_id=b'Fa2/3'),
                        RemoteIdOption(enterprise_number=9,
                                       remote_id=bytes.fromhex('020023000001000a0003000100211c7d486e')),
                    ])
                ),
                InterfaceIdOption(interface_id=b'Gi0/0/0'),
                RemoteIdOption(enterprise_number=9, remote_id=bytes.fromhex('020000000000000a0003000124e9b36e8100')),
                RelayIdOption(duid=LinkLayerDUID(hardware_type=1, link_layer_address=bytes.fromhex('121212121212'))),
            ],
        )

    def test_database_creation(self):
        with TemporaryDirectory() as tmp_dir_name:
            with self.assertLogs('', level='NOTSET') as cm:
                LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))

            self.assertEqual(len(cm.output), 4)
            self.assertRegex(cm.output[0], 'Opening Leasequery SQLite database')
            self.assertRegex(cm.output[1], 'Upgrading or removing')
            self.assertRegex(cm.output[2], 'Creating leasequery database tables')
            self.assertRegex(cm.output[3], 'Cleaning up old records')

    def test_bad_database_creation(self):
        with TemporaryDirectory() as tmp_dir_name:
            with self.assertRaisesRegex(ValueError, 'unable to open database'):
                LeasequerySqliteStore(os.path.join(tmp_dir_name, 'BAD/DIR/NAME/lq.sqlite'))

    def test_filename(self):
        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))

            self.assertRegex(store.sqlite_filename, '/lq.sqlite$')

    def test_database_tables(self):
        expected_elements = [
            {'type': "table", 'name': "clients",
             'seen': False,
             'sql': "CREATE TABLE clients ("
                    "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                    "client_id TEXT NOT NULL, "
                    "link_address TEXT NOT NULL, "
                    "options BLOB NOT NULL DEFAULT '', "
                    "last_interaction INTEGER NOT NULL DEFAULT -1, "
                    "relay_data BLOB NOT NULL DEFAULT '', "
                    "UNIQUE (client_id, link_address))"},
            {'type': "table", 'name': "addresses",
             'seen': False,
             'sql': "CREATE TABLE addresses ("
                    "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                    "address TEXT NOT NULL, "
                    "preferred_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                    "valid_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                    "options BLOB NOT NULL DEFAULT '', "
                    "UNIQUE (client_fk, address))"},
            {'type': "table", 'name': "prefixes",
             'seen': False,
             'sql': "CREATE TABLE prefixes ("
                    "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                    "first_address TEXT NOT NULL, "
                    "last_address TEXT NOT NULL, "
                    "preferred_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                    "valid_lifetime_end INTEGER NOT NULL DEFAULT -1, "
                    "options BLOB NOT NULL DEFAULT '', "
                    "UNIQUE (client_fk, first_address, last_address))"},
            {'type': "table", 'name': "remote_ids",
             'seen': False,
             'sql': "CREATE TABLE remote_ids ("
                    "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                    "remote_id TEXT NOT NULL, "
                    "UNIQUE (client_fk, remote_id))"},
            {'type': "table", 'name': "relay_ids",
             'seen': False,
             'sql': "CREATE TABLE relay_ids ("
                    "client_fk INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
                    "relay_id TEXT NOT NULL, "
                    "UNIQUE (client_fk, relay_id))"},
            {'type': "index", 'name': "clients_client_id",
             'seen': False,
             'sql': "CREATE INDEX clients_client_id ON clients(client_id, link_address)"},
            {'type': "index", 'name': "clients_link_address",
             'seen': False,
             'sql': "CREATE INDEX clients_link_address ON clients(link_address)"},
            {'type': "index", 'name': "addresses_address",
             'seen': False,
             'sql': "CREATE INDEX addresses_address ON addresses(address)"},
            {'type': "index", 'name': "prefixes_range",
             'seen': False,
             'sql': "CREATE INDEX prefixes_range ON prefixes(first_address, last_address)"},
            {'type': "index", 'name': "remote_ids_remote_id",
             'seen': False,
             'sql': "CREATE INDEX remote_ids_remote_id ON remote_ids(remote_id)"},
            {'type': "index",
             'name': "relay_ids_relay_id",
             'seen': False,
             'sql': "CREATE INDEX relay_ids_relay_id ON relay_ids(relay_id)"},
        ]

        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))

            db = sqlite3.connect(store.sqlite_filename)
            rows = db.execute("SELECT type, name, sql FROM sqlite_master "
                              "WHERE name NOT LIKE '%_autoindex_%' "
                              "AND name NOT LIKE '%_fk' "
                              "AND name NOT LIKE 'sqlite_%'")

            for row in rows:
                with self.subTest(msg="{type}: {name}".format(type=row[0], name=row[1])):
                    for element in expected_elements:
                        if row[0] == element['type'] and row[1] == element['name']:
                            self.assertEqual(row[2], element['sql'])
                            element['seen'] = True
                            break
                    else:  # pragma: no cover
                        raise self.failureException("Unexpected {type} '{name}'".format(type=row[0], name=row[1]))

            for element in expected_elements:
                with self.subTest(msg="{type}: {name}".format(type=element['type'], name=element['name'])):
                    if not element['seen']:  # pragma: no cover
                        raise self.failureException("Expected {type} '{name}' does not exist".format(**element))

    def test_sqlite_present(self):
        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))

            store.worker_init([])
            self.assertIsInstance(store.db, sqlite3.Connection)

    def test_sensitive_options_empty(self):
        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))

            store.worker_init([])
            self.assertEqual(len(store.sensitive_options), 0)

    def test_sensitive_options_not_empty(self):
        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))

            store.worker_init([1, 2, 3])
            self.assertEqual(len(store.sensitive_options), 3)
            self.assertIn(1, store.sensitive_options)
            self.assertIn(2, store.sensitive_options)
            self.assertIn(3, store.sensitive_options)

    def test_remember_lease_non_interesting(self):
        bundle = TransactionBundle(confirm_message, received_over_multicast=False)
        bundle.response = reply_message

        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            # Check that nothing ended up in the database
            db = sqlite3.connect(store.sqlite_filename)
            rows = list(db.execute("SELECT 1 FROM clients"))
            self.assertEqual(len(rows), 0)

    def test_remember_lease_interesting(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.request.get_option_of_type(ClientIdOption)
        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)
        ia_pd_option = bundle.response.get_option_of_type(IAPDOption)
        ia_prefix = ia_pd_option.get_option_of_type(IAPrefixOption)

        remote_ids = set()
        for relay_message in bundle.incoming_relay_messages:
            for option in relay_message.get_options_of_type(RemoteIdOption):
                remote_ids.add("{}:{}".format(option.enterprise_number, normalise_hex(option.remote_id)))

        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            # Check that the data ended up in the database
            db = sqlite3.connect(store.sqlite_filename)
            db.row_factory = sqlite3.Row

            rows = list(db.execute("SELECT * FROM clients"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            client_row = row['id']
            self.assertEqual(row['client_id'], normalise_hex(client_id_option.duid.save()))
            self.assertEqual(row['link_address'], bundle.link_address.exploded)
            self.assertAlmostEqual(row['last_interaction'], time.time(), delta=5)
            # print({key: row[key] for key in rows[0].keys()})

            rows = list(db.execute("SELECT * FROM addresses"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['client_fk'], client_row)
            self.assertEqual(row['address'], ia_address.address.exploded)
            self.assertAlmostEqual(row['preferred_lifetime_end'], time.time() + ia_address.preferred_lifetime, delta=5)
            self.assertAlmostEqual(row['valid_lifetime_end'], time.time() + ia_address.valid_lifetime, delta=5)
            self.assertEqual(row['options'], b'')

            rows = list(db.execute("SELECT * FROM prefixes"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['client_fk'], client_row)
            self.assertEqual(row['first_address'], ia_prefix.prefix[0].exploded)
            self.assertEqual(row['last_address'], ia_prefix.prefix[-1].exploded)
            self.assertAlmostEqual(row['preferred_lifetime_end'], time.time() + ia_address.preferred_lifetime, delta=5)
            self.assertAlmostEqual(row['valid_lifetime_end'], time.time() + ia_address.valid_lifetime, delta=5)
            self.assertEqual(row['options'], b'')

            rows = list(db.execute("SELECT * FROM remote_ids"))
            self.assertEqual(len(rows), len(remote_ids))
            self.assertSetEqual({row['remote_id'] for row in rows}, remote_ids)

            rows = list(db.execute("SELECT * FROM relay_ids"))
            self.assertEqual(len(rows), 1)

    def test_remember_lease_again(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.request.get_option_of_type(ClientIdOption)
        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)
        ia_pd_option = bundle.response.get_option_of_type(IAPDOption)
        ia_prefix = ia_pd_option.get_option_of_type(IAPrefixOption)

        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            # Change some of the relay information and remember again
            bundle.incoming_relay_messages[-1].get_option_of_type(RelayIdOption).duid=LinkLayerDUID(
                hardware_type=1, link_layer_address=bytes.fromhex('343434343434'))
            bundle.incoming_relay_messages[0].get_option_of_type(RemoteIdOption).enterprise_number = 10
            store.remember_lease(bundle)

            remote_ids = set()
            for relay_message in bundle.incoming_relay_messages:
                for option in relay_message.get_options_of_type(RemoteIdOption):
                    remote_ids.add("{}:{}".format(option.enterprise_number, normalise_hex(option.remote_id)))

            # Check that the data ended up in the database
            db = sqlite3.connect(store.sqlite_filename)
            db.row_factory = sqlite3.Row

            rows = list(db.execute("SELECT * FROM clients"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            client_row = row['id']
            self.assertEqual(row['client_id'], normalise_hex(client_id_option.duid.save()))
            self.assertEqual(row['link_address'], bundle.link_address.exploded)
            self.assertAlmostEqual(row['last_interaction'], time.time(), delta=5)
            # print({key: row[key] for key in rows[0].keys()})

            rows = list(db.execute("SELECT * FROM addresses"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['client_fk'], client_row)
            self.assertEqual(row['address'], ia_address.address.exploded)
            self.assertAlmostEqual(row['preferred_lifetime_end'], time.time() + ia_address.preferred_lifetime, delta=5)
            self.assertAlmostEqual(row['valid_lifetime_end'], time.time() + ia_address.valid_lifetime, delta=5)
            self.assertEqual(row['options'], b'')

            rows = list(db.execute("SELECT * FROM prefixes"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['client_fk'], client_row)
            self.assertEqual(row['first_address'], ia_prefix.prefix[0].exploded)
            self.assertEqual(row['last_address'], ia_prefix.prefix[-1].exploded)
            self.assertAlmostEqual(row['preferred_lifetime_end'], time.time() + ia_address.preferred_lifetime, delta=5)
            self.assertAlmostEqual(row['valid_lifetime_end'], time.time() + ia_address.valid_lifetime, delta=5)
            self.assertEqual(row['options'], b'')

            rows = list(db.execute("SELECT * FROM remote_ids"))
            self.assertEqual(len(rows), len(remote_ids))
            self.assertSetEqual({row['remote_id'] for row in rows}, remote_ids)

            rows = list(db.execute("SELECT * FROM relay_ids"))
            self.assertEqual(len(rows), 1)

    def test_remember_lease_differently(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.request.get_option_of_type(ClientIdOption)
        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)
        ia_pd_option = bundle.response.get_option_of_type(IAPDOption)
        ia_prefix = ia_pd_option.get_option_of_type(IAPrefixOption)

        remote_ids = set()
        for relay_message in bundle.incoming_relay_messages:
            for option in relay_message.get_options_of_type(RemoteIdOption):
                remote_ids.add("{}:{}".format(option.enterprise_number, normalise_hex(option.remote_id)))

        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            store.remember_lease(bundle)

            # Check that the data ended up in the database
            db = sqlite3.connect(store.sqlite_filename)
            db.row_factory = sqlite3.Row

            rows = list(db.execute("SELECT * FROM clients"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            client_row = row['id']
            self.assertEqual(row['client_id'], normalise_hex(client_id_option.duid.save()))
            self.assertEqual(row['link_address'], bundle.link_address.exploded)
            self.assertAlmostEqual(row['last_interaction'], time.time(), delta=5)
            # print({key: row[key] for key in rows[0].keys()})

            rows = list(db.execute("SELECT * FROM addresses"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['client_fk'], client_row)
            self.assertEqual(row['address'], ia_address.address.exploded)
            self.assertAlmostEqual(row['preferred_lifetime_end'], time.time() + ia_address.preferred_lifetime, delta=5)
            self.assertAlmostEqual(row['valid_lifetime_end'], time.time() + ia_address.valid_lifetime, delta=5)
            self.assertEqual(row['options'], b'')

            rows = list(db.execute("SELECT * FROM prefixes"))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row['client_fk'], client_row)
            self.assertEqual(row['first_address'], ia_prefix.prefix[0].exploded)
            self.assertEqual(row['last_address'], ia_prefix.prefix[-1].exploded)
            self.assertAlmostEqual(row['preferred_lifetime_end'], time.time() + ia_address.preferred_lifetime, delta=5)
            self.assertAlmostEqual(row['valid_lifetime_end'], time.time() + ia_address.valid_lifetime, delta=5)
            self.assertEqual(row['options'], b'')

            rows = list(db.execute("SELECT * FROM remote_ids"))
            self.assertEqual(len(rows), len(remote_ids))
            self.assertSetEqual({row['remote_id'] for row in rows}, remote_ids)

            rows = list(db.execute("SELECT * FROM relay_ids"))
            self.assertEqual(len(rows), 1)

    def query(self, bundle: TransactionBundle, query: LQQueryOption, extra_options: Iterable[Type[Option]] = None):
        extra_options = list(extra_options or [])

        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            nr_found, results = store.find_leases(query)
            results = list(results)

            self.assertEqual(nr_found, 1)
            self.assertEqual(len(results), 1)

            link_address, client_data = results[0]
            self.assertEqual(link_address, bundle.link_address)
            self.assertIsInstance(client_data, ClientDataOption)
            self.assertEqual(len(client_data.options), 4 + len(extra_options))

            option_classes = {option.__class__ for option in client_data.options}
            self.assertIn(CLTTimeOption, option_classes)
            self.assertIn(ClientIdOption, option_classes)
            self.assertIn(IAAddressOption, option_classes)
            self.assertIn(IAPrefixOption, option_classes)
            for option_class in extra_options:
                self.assertIn(option_class, option_classes)

    def query_empty(self, bundle: TransactionBundle, query: LQQueryOption, invalid=False):
        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            nr_found, results = store.find_leases(query)
            results = list(results)

            self.assertEqual(nr_found, -1 if invalid else 0)
            self.assertEqual(len(results), 0)

    def test_query_by_address(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, options=[ia_address])

        self.query(bundle, query)

    def test_query_by_address_malformed(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(QUERY_BY_ADDRESS)

        with self.assertRaisesRegex(ReplyWithLeasequeryError, 'Address queries must contain an address'):
            self.query(bundle, query)

    def test_query_by_address_on_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, link_address=bundle.link_address, options=[ia_address])

        self.query(bundle, query)

    def test_query_by_address_on_wrong_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, link_address=IPv6Address('3ffe::'), options=[ia_address])

        self.query_empty(bundle, query)

    def test_query_by_address_with_extra_data(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, options=[ia_address, OptionRequestOption([OPTION_DNS_SERVERS])])

        self.query(bundle, query, [RecursiveNameServersOption])

    def test_query_by_address_with_relay_data(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, options=[ia_address, OptionRequestOption([OPTION_LQ_RELAY_DATA])])

        self.query(bundle, query, [LQRelayDataOption])

    def test_query_by_address_with_extra_and_relay_data(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, options=[ia_address, OptionRequestOption([OPTION_DNS_SERVERS,
                                                                                          OPTION_LQ_RELAY_DATA])])

        self.query(bundle, query, [RecursiveNameServersOption, LQRelayDataOption])

    def test_query_by_client_id(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.response.get_option_of_type(ClientIdOption)

        query = LQQueryOption(QUERY_BY_CLIENT_ID, options=[client_id_option])

        self.query(bundle, query)

    def test_query_by_client_id_malformed(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(QUERY_BY_CLIENT_ID)

        with self.assertRaisesRegex(ReplyWithLeasequeryError, 'Client-ID queries must contain a client ID'):
            self.query(bundle, query)

    def test_query_by_client_id_on_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.response.get_option_of_type(ClientIdOption)

        query = LQQueryOption(QUERY_BY_CLIENT_ID, link_address=bundle.link_address, options=[client_id_option])

        self.query(bundle, query)

    def test_query_by_client_id_on_wrong_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.response.get_option_of_type(ClientIdOption)

        query = LQQueryOption(QUERY_BY_CLIENT_ID, link_address=IPv6Address('3ffe::'), options=[client_id_option])

        self.query_empty(bundle, query)

    def test_query_by_relay_id(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        relay_id_option = bundle.incoming_relay_messages[-1].get_option_of_type(RelayIdOption)

        query = LQQueryOption(QUERY_BY_RELAY_ID, options=[relay_id_option])

        self.query(bundle, query)

    def test_query_by_relay_id_malformed(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(QUERY_BY_RELAY_ID)

        with self.assertRaisesRegex(ReplyWithLeasequeryError, 'Relay-ID queries must contain a relay ID'):
            self.query(bundle, query)

    def test_query_by_relay_id_on_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        relay_id_option = bundle.incoming_relay_messages[-1].get_option_of_type(RelayIdOption)

        query = LQQueryOption(QUERY_BY_RELAY_ID, link_address=bundle.link_address, options=[relay_id_option])

        self.query(bundle, query)

    def test_query_by_relay_id_on_wrong_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        client_id_option = bundle.response.get_option_of_type(ClientIdOption)

        query = LQQueryOption(QUERY_BY_RELAY_ID, link_address=IPv6Address('3ffe::'),
                              options=[RelayIdOption(duid=client_id_option.duid)])

        # Our test data doesn't have a relay-id, so no results expected
        self.query_empty(bundle, query)

    def test_query_by_link_address(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(QUERY_BY_LINK_ADDRESS, link_address=bundle.link_address)

        self.query(bundle, query)

    def test_query_by_unspecified_link_address(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(QUERY_BY_LINK_ADDRESS, link_address=IPv6Address('::'))

        self.query(bundle, query)

    def test_query_by_remote_id(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        # Test every remote-id
        for relay_message in bundle.incoming_relay_messages:
            for option in relay_message.get_options_of_type(RemoteIdOption):
                with self.subTest(msg="{}:{}".format(option.enterprise_number, normalise_hex(option.remote_id))):
                    query = LQQueryOption(QUERY_BY_REMOTE_ID, options=[option])
                    self.query(bundle, query)

    def test_query_by_remote_id_malformed(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(QUERY_BY_REMOTE_ID)

        with self.assertRaisesRegex(ReplyWithLeasequeryError, 'Remote-ID queries must contain a remote ID'):
            self.query(bundle, query)

    def test_query_by_remote_id_on_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        # Test every remote-id
        for relay_message in bundle.incoming_relay_messages:
            for option in relay_message.get_options_of_type(RemoteIdOption):
                with self.subTest(msg="{}:{}".format(option.enterprise_number, normalise_hex(option.remote_id))):
                    query = LQQueryOption(QUERY_BY_REMOTE_ID, link_address=bundle.link_address, options=[option])
                    self.query(bundle, query)

    def test_query_by_remote_id_on_wrong_link(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        # Test every remote-id
        for relay_message in bundle.incoming_relay_messages:
            for option in relay_message.get_options_of_type(RemoteIdOption):
                with self.subTest(msg="{}:{}".format(option.enterprise_number, normalise_hex(option.remote_id))):
                    query = LQQueryOption(QUERY_BY_REMOTE_ID, link_address=IPv6Address('3ffe::'), options=[option])
                    self.query_empty(bundle, query)

    def test_query_by_unknown(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        query = LQQueryOption(-1)

        # No valid query provided, no data
        self.query_empty(bundle, query, invalid=True)

    def test_query_messed_up_prefix(self):
        bundle = TransactionBundle(self.relayed_solicit_message, received_over_multicast=False)
        bundle.response = reply_message

        ia_na_option = bundle.response.get_option_of_type(IANAOption)
        ia_address = ia_na_option.get_option_of_type(IAAddressOption)

        query = LQQueryOption(QUERY_BY_ADDRESS, options=[ia_address])

        # Messed-up data, a log message should appear
        with TemporaryDirectory() as tmp_dir_name:
            store = LeasequerySqliteStore(os.path.join(tmp_dir_name, 'lq.sqlite'))
            store.worker_init([])
            store.remember_lease(bundle)

            # Mess up the data in our poor database
            db = sqlite3.connect(store.sqlite_filename)
            db.row_factory = sqlite3.Row
            db.execute("UPDATE prefixes SET first_address='2001:0db8:0000:0000:0000:0000:0000:0000'")
            db.commit()

            with self.assertLogs('', 'NOTSET')as cm:
                nr_found, results = store.find_leases(query)
                results = list(results)

            self.assertEqual(nr_found, 1)
            self.assertEqual(len(results), 1)
            self.assertEqual(len(cm.output), 1)
            self.assertRegex(cm.output[0], 'Ignoring invalid prefix range')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
