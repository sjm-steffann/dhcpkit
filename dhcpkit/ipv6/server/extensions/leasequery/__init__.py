"""
Implementation of the Leasequery and Bulk Leasequery extensions.
"""
import codecs
import logging
from ipaddress import IPv6Address, IPv6Network
from typing import Iterable, Iterator, List, Optional, Tuple, Union

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.extensions.bulk_leasequery import LeasequeryDataMessage, LeasequeryDoneMessage, RelayIdOption, \
    STATUS_QUERY_TERMINATED
from dhcpkit.ipv6.extensions.leasequery import ClientDataOption, LQClientLink, LQQueryOption, LQRelayDataOption, \
    LeasequeryMessage, STATUS_NOT_ALLOWED, STATUS_UNKNOWN_QUERY_TYPE
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, OPTION_IAPREFIX, OPTION_IA_PD
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.messages import Message, RelayForwardMessage, ReplyMessage
from dhcpkit.ipv6.options import IAAddressOption, IANAOption, IATAOption, OPTION_CLIENTID, OPTION_IAADDR, \
    OPTION_IA_NA, OPTION_IA_TA, OPTION_ORO, OPTION_RELAY_MSG, OPTION_SERVERID, OPTION_STATUS_CODE, Option, \
    STATUS_SUCCESS, STATUS_UNSPEC_FAIL, StatusCodeOption
from dhcpkit.ipv6.server.handlers import Handler, ReplyWithLeasequeryError
from dhcpkit.ipv6.server.transaction_bundle import MessagesList, TransactionBundle

logger = logging.getLogger(__name__)


def create_cleanup_handlers() -> List[Handler]:
    """
    Create handlers to handle unhandled queries

    :return: Handlers to add to the handler chain
    """
    return [
        UnansweredLeasequeryHandler(),
    ]


class UnansweredLeasequeryHandler(Handler):
    """
    When there are leasequeries that haven't been handled at the end of the handling phase that means that no handler
    understood the query.
    """

    def post(self, bundle: TransactionBundle):
        """
        Check for unhandled leasequeries.

        :param bundle: The transaction bundle
        """
        if not isinstance(bundle.request, LeasequeryMessage):
            # Only leasequeries are relevant
            return

        unhandled_queries = bundle.get_unhandled_options(LQQueryOption)
        if unhandled_queries:
            query = unhandled_queries[0]
            raise ReplyWithLeasequeryError(STATUS_UNKNOWN_QUERY_TYPE,
                                           "This server can't handle query type {}".format(query.query_type))


class LeasequeryStore:
    """
    Base class for leasequery stores
    """

    def __init__(self):
        """
        The main initialisation will be done in the master process. After initialisation the master process will create
        worker processes using the multiprocessing module. Things that can't be pickled and transmitted to the worker
        processes (think database connections etc) have to be initialised separately. Each worker process will call
        worker_init() to do so. Filters that don't need per-worker initialisation can do everything here in __init__().
        """
        self.sensitive_options = []

    def worker_init(self, sensitive_options: Iterable[int]):
        """
        Separate initialisation that will be called in each worker process that is created. Things that can't be forked
        (think database connections etc) have to be initialised here.

        :param sensitive_options: The options that are not allowed to be stored
        """
        self.sensitive_options = list(sensitive_options or [])

    def __str__(self):
        """
        Return a representation of this store for logging purposes

        :return: A descriptive string
        """
        # Use the class name as default, let subclasses overrule this where it makes sense
        return self.__class__.__name__

    def remember_lease(self, bundle: TransactionBundle):
        """
        Remember the leases in the given transaction bundle so they can be queried later.

        :param bundle: The transaction to remember
        """
        raise NotImplementedError

    def find_leases(self, query: LQQueryOption) -> Tuple[int, Iterable[Tuple[IPv6Address, ClientDataOption]]]:
        """
        Find all leases that match the given query.

        :param query: The query
        :return: The number of leases and an iterator over tuples of link-address and corresponding client data
        """
        raise NotImplementedError

    @staticmethod
    def filter_options(options: Iterable[Option], unwanted_option_types: Iterable[int]) -> Iterable[Option]:
        """
        Remove unwanted data from the options.

        :param options: The options to filter
        :param unwanted_option_types: List of option types to filter out
        :return: The filtered options
        """
        # Scrub the output so that we don't return options that are marked as sensitive or otherwise unwanted
        return [option for option in options if option.option_type not in unwanted_option_types]

    def filter_sensitive_options(self, options: Iterable[Option]) -> Iterable[Option]:
        """
        Remove sensitive data from the options.

        :param options: The options to filter
        :return: The filtered options
        """
        return self.filter_options(options, self.sensitive_options)

    def filter_storable_options(self, options: Iterable[Option]) -> Iterable[Option]:
        """
        Only include storable data from the options.

        :param options: The options to filter
        :return: The filtered options
        """
        return self.filter_options(
            options,
            self.sensitive_options + [
                OPTION_CLIENTID, OPTION_SERVERID, OPTION_RELAY_MSG, OPTION_ORO, OPTION_IA_NA,
                OPTION_IA_TA, OPTION_IA_PD, OPTION_IAADDR, OPTION_IAPREFIX, OPTION_STATUS_CODE
            ]
        )

    def filter_requested_options(self, options: Iterable[Option], requested_options: Iterable[int]):
        """
        Only return options that are requested by the leasequery client.

        :param options: The original list of options
        :param requested_options: The list of requested options
        :return: The filtered list
        """
        if not requested_options:
            # No options requested, no options returned
            return []

        return [option for option in options
                if option.option_type in requested_options and option.option_type not in self.sensitive_options]

    @staticmethod
    def is_accepted(element: Union[ReplyMessage, IANAOption, IATAOption, IAPDOption]) -> bool:
        """
        Check if there is no status code that signals rejection.

        :param element: The element to look in
        :return: Whether the status is ok
        """
        status = element.get_option_of_type(StatusCodeOption)
        if not status:
            return True

        return status.status_code == STATUS_SUCCESS

    @staticmethod
    def encode_duid(duid: DUID) -> str:
        """
        Encode DUID as a string.

        :param duid: The DUID object
        :return: The string representing the DUID
        """
        return codecs.encode(duid.save(), 'hex').decode('ascii')

    @staticmethod
    def decode_duid(duid_str: str) -> DUID:
        """
        Decode DUID from a string.

        :param duid_str: The DUID string
        :return: The DUID object
        """
        duid_bytes = bytes.fromhex(duid_str)
        duid_len, duid = DUID.parse(duid_bytes, length=len(duid_bytes))
        return duid

    @staticmethod
    def encode_remote_id(remote_id_option: RemoteIdOption) -> str:
        """
        Encode remote id as a string.

        :param remote_id_option: The remote-id option
        :return: The string representing the remote-id
        """
        return "{}:{}".format(remote_id_option.enterprise_number,
                              codecs.encode(remote_id_option.remote_id, 'hex').decode('ascii'))

    @staticmethod
    def decode_remote_id(remote_id_str: str) -> RemoteIdOption:
        """
        Decode remote id from a string.

        :param remote_id_str: The remote-id string
        :return: The remote-id option
        """
        parts = remote_id_str.split(':', maxsplit=1)
        enterprise_number = int(parts[0])
        remote_id = bytes.fromhex(parts[1])
        return RemoteIdOption(enterprise_number, remote_id)

    def get_remote_ids(self, bundle: TransactionBundle) -> Iterator[str]:
        """
        Go through all the relay messages and return all remote-ids found as lowercase hex strings

        :param bundle: The transaction bundle
        :return: The remote-ids as hex strings
        """
        for relay_message in bundle.incoming_relay_messages:
            for remote_id_option in relay_message.get_options_of_type(RemoteIdOption):
                yield self.encode_remote_id(remote_id_option)

    @staticmethod
    def get_relay_ids(bundle: TransactionBundle) -> Iterator[str]:
        """
        Go through all the relay messages and return all relay-ids found as lowercase hex strings

        :param bundle: The transaction bundle
        :return: The relay-ids as hex strings
        """
        for relay_message in bundle.incoming_relay_messages:
            for relay_id_option in relay_message.get_options_of_type(RelayIdOption):
                yield codecs.encode(relay_id_option.duid, 'hex').decode('ascii')

    def get_address_leases(self, bundle: TransactionBundle) -> Iterator[IAAddressOption]:
        """
        Search through the reply and return all addresses given to the client.

        :param bundle: The transaction bundle
        :return: The address options
        """
        for option in bundle.response.get_options_of_type(IANAOption, IATAOption):
            if not self.is_accepted(option):
                continue

            yield from option.get_options_of_type(IAAddressOption)

    def get_prefix_leases(self, bundle: TransactionBundle) -> Iterator[IAPrefixOption]:
        """
        Search through the reply and return all prefixes given to the client.

        :param bundle: The transaction bundle
        :return: The prefix options
        """
        for option in bundle.response.get_options_of_type(IAPDOption):
            if not self.is_accepted(option):
                continue

            yield from option.get_options_of_type(IAPrefixOption)

    def encode_options(self, options: Iterable[Option]) -> bytes:
        """
        Encode a list of options as bytes.

        :param options: The list of options
        :return: The bytes
        """
        out = b''
        for option in self.filter_storable_options(options):
            out += option.save()
        return out

    @staticmethod
    def decode_options(data: bytes) -> Iterable[Option]:
        """
        Decode a list of options from bytes.

        :param data: The bytes
        :return: The list of options
        """
        options = []
        max_length = len(data)
        offset = 0
        while max_length > offset:
            used_buffer, option = Option.parse(data, offset=offset, length=max_length - offset)
            options.append(option)
            offset += used_buffer

        return options

    def encode_relay_messages(self, relay_chain: Optional[RelayForwardMessage]) -> bytes:
        """
        Encode a chain of relay messages as bytes.

        :param relay_chain: The incoming relay messages
        :return: The bytes
        """
        if not relay_chain:
            return b''

        current_in = relay_chain
        current_out = None
        out = None
        while isinstance(current_in, RelayForwardMessage):
            new_relay_message = RelayForwardMessage(hop_count=current_in.hop_count,
                                                    link_address=current_in.link_address,
                                                    peer_address=current_in.peer_address,
                                                    options=self.filter_storable_options(current_in.options))
            if not current_out:
                out = new_relay_message
            else:
                current_out.relayed_message = new_relay_message

            current_in = current_in.relayed_message
            current_out = new_relay_message

        # Save the resulting chain
        if not out:
            return b''

        return out.save()

    @staticmethod
    def decode_relay_messages(data: bytes) -> Optional[RelayForwardMessage]:
        """
        Decode a chain of relay messages from bytes.

        :param data: The bytes
        :return: The relay message
        """
        if not data:
            return None

        return Message.parse(data)[1]

    def build_relay_data_option_from_relay_data(self, relay_data: bytes) -> Optional[LQRelayDataOption]:
        """
        The relay data includes the outer relay message, which is generated inside the server to keep track of where
        we got the request from. When returning relay data to the leasequery client we build the LQRelayDataOption
        using this internal relay message only including the real relay messages we received.

        :param relay_data: The raw relay data
        :return: The LQRelayDataOption if applicable
        """
        if not relay_data:
            return None

        relay_chain = self.decode_relay_messages(relay_data)

        # The outer relay message contains the peer address we need
        peer_address = relay_chain.peer_address

        # Go up one position in the relay chain
        relay_chain = relay_chain.relayed_message

        if not isinstance(relay_chain, RelayForwardMessage):
            # We only had the internal relay message, so we didn't receive this client's request through a relay
            return None

        return LQRelayDataOption(peer_address, relay_chain)


class LeasequeryHandler(Handler):
    """
    Handle leasequery requests and analyse replies that we send out to store any observed leases.
    """

    def __init__(self, store: LeasequeryStore, allow_from: Iterable[IPv6Network] = None,
                 sensitive_options: Iterable[int] = None):
        super().__init__()

        self.store = store
        self.allow_from = list(allow_from or [])
        self.sensitive_options = list(sensitive_options or [])

    def worker_init(self):
        """
        Make sure the store gets a chance to initialise itself.
        """
        self.store.worker_init(self.sensitive_options)

    def pre(self, bundle: TransactionBundle):
        """
        Make sure we allow this client to make leasequery requests.

        :param bundle: The transaction bundle
        """
        if not isinstance(bundle.request, LeasequeryMessage):
            # Not a leasequery, not our business
            return

        # Check access based on relay closest to the client
        if not any([bundle.incoming_relay_messages[0].peer_address in allow_from for allow_from in self.allow_from]):
            raise ReplyWithLeasequeryError(STATUS_NOT_ALLOWED, "Leasequery not allowed from your address")

    @staticmethod
    def generate_data_messages(transaction_id: bytes, leases: Iterator[Tuple[IPv6Address, ClientDataOption]]) \
            -> Iterator[Union[LeasequeryDataMessage, LeasequeryDoneMessage]]:
        """
        Generate a leasequery data message for each of the leases, followed by a leasequery done message.

        :param transaction_id: The transaction ID to use in the messages
        :param leases: An open iterator for the data we still need to return
        :return: Leasequery messages to send to the client
        """
        for link_address, data_option in leases:
            yield LeasequeryDataMessage(transaction_id, options=[data_option])

        yield LeasequeryDoneMessage(transaction_id, options=[
            StatusCodeOption(STATUS_SUCCESS, "That's all folks")
        ])

    def handle(self, bundle: TransactionBundle):
        """
        Perform leasequery if requested.

        :param bundle: The transaction bundle
        """
        if not isinstance(bundle.request, LeasequeryMessage):
            # Not a leasequery, not our business
            return

        # Extract the query
        queries = bundle.get_unhandled_options(LQQueryOption)
        if not queries:
            # No unhandled queries
            return

        query = queries[0]

        # Get the leases from the store
        lease_count, leases = self.store.find_leases(query)

        # A count of -1 means unsupported query, so we stop handling
        if lease_count < 0:
            return

        # Otherwise mark this query as handled
        bundle.mark_handled(query)

        # What we do now depends on the protocol
        if bundle.received_over_tcp:
            try:
                if lease_count > 0:
                    # We're doing bulk leasequery, return all the records in separate messages
                    leases_iterator = iter(leases)
                    first_link_address, first_data_option = next(leases_iterator)
                    first_message = bundle.response
                    first_message.options.append(first_data_option)

                    bundle.responses = MessagesList(first_message,
                                                    self.generate_data_messages(first_message.transaction_id,
                                                                                leases_iterator))
                else:
                    # If the server does not find any bindings satisfying a query, it
                    # SHOULD send a LEASEQUERY-REPLY without an OPTION_STATUS_CODE option
                    # and without any OPTION_CLIENT_DATA option.
                    pass
            except:
                # Something went wrong (database changes while reading?), abort
                logger.exception("Error while building bulk leasequery response")
                raise ReplyWithLeasequeryError(STATUS_QUERY_TERMINATED,
                                               "Error constructing your reply, please try again")
        else:
            try:
                if lease_count == 1:
                    # One entry found, return it
                    leases_iterator = iter(leases)
                    first_link_address, first_data_option = next(leases_iterator)
                    bundle.response.options.append(first_data_option)
                elif lease_count > 1:
                    # The Client Link option is used only in a LEASEQUERY-REPLY message and
                    # identifies the links on which the client has one or more bindings.
                    # It is used in reply to a query when no link-address was specified and
                    # the client is found to be on more than one link.
                    link_addresses = set([link_address for link_address, data_option in leases])
                    bundle.response.options.append(LQClientLink(link_addresses))
            except:
                # Something went wrong (database changes while reading?), abort
                logger.exception("Error while building leasequery response")
                raise ReplyWithLeasequeryError(STATUS_UNSPEC_FAIL,
                                               "Error constructing your reply, please try again")

    def analyse_post(self, bundle: TransactionBundle):
        """
        Watch outgoing replies and store observed leases in the store.

        :param bundle: The transaction bundle containing the outgoing reply
        """
        if isinstance(bundle.response, ReplyMessage):
            # We're only interested in replies, advertise messages don't give a lease. Rapid commit will have turned
            # this into a reply when used, so checking for replies is enough.
            self.store.remember_lease(bundle)
