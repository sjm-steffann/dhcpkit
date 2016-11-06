"""
Server extension to handle bulk leasequery properly
"""
import logging

from dhcpkit.ipv6.extensions.bulk_leasequery import QUERY_BY_LINK_ADDRESS, QUERY_BY_RELAY_ID, QUERY_BY_REMOTE_ID
from dhcpkit.ipv6.extensions.leasequery import LQQueryOption, LeasequeryMessage, STATUS_NOT_ALLOWED
from dhcpkit.ipv6.server.handlers import CannotRespondError, Handler, ReplyWithLeasequeryError
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from typing import List

logger = logging.getLogger(__name__)


def create_setup_handlers() -> List[Handler]:
    """
    Create handlers to clean up stuff in the transaction bundle

    :return: Handlers to add to the handler chain
    """
    return [
        RequireBulkLeasequeryOverTCPHandler(),
        RefuseBulkLeasequeryOverUDPHandler(),
    ]


class RequireBulkLeasequeryOverTCPHandler(Handler):
    """
    A handler that makes sure only bulk leasequery is accepted over TCP.

    Only LEASEQUERY, LEASEQUERY-REPLY, LEASEQUERY-DATA, and LEASEQUERY-DONE messages are allowed over the Bulk
    Leasequery connection.  No other DHCPv6 messages are supported.  The Bulk Leasequery connection is not an
    alternative DHCPv6 communication option for clients seeking DHCPv6 service.
    """

    def pre(self, bundle: TransactionBundle):
        """
        Make sure that bulk leasequery options are not coming in over UDP.

        :param bundle: The transaction bundle
        """
        if not bundle.received_over_tcp:
            # Not a bulk leasequery TCP connection, we don't care
            return

        # The incoming message must be a LeasequeryMessage
        if not isinstance(bundle.request, LeasequeryMessage):
            logger.warning("Client sent non-Leasequery message over a Bulk Leasequery socket")
            raise CannotRespondError


class RefuseBulkLeasequeryOverUDPHandler(Handler):
    """
    A handler that refuses bulk leasequery over UDP.

    The new queries introduced in this specification cannot be used with the UDP Leasequery protocol.  Servers that
    implement this specification and also permit UDP queries MUST NOT accept Bulk Leasequery query-types in UDP
    Leasequery messages.  Such servers MUST respond with an error status code of
    :data:`~dhcpkit.ipv6.extensions.leasequery.STATUS_NOT_ALLOWED`.
    """

    def pre(self, bundle: TransactionBundle):
        """
        Make sure that bulk leasequery options are not coming in over UDP.

        :param bundle: The transaction bundle
        """
        if bundle.received_over_tcp:
            # This is over TCP, so we allow all query types
            return

        if not isinstance(bundle.request, LeasequeryMessage):
            # Not a leasequery question, we don't care
            return

        query = bundle.request.get_option_of_type(LQQueryOption)
        if query.query_type in (QUERY_BY_RELAY_ID, QUERY_BY_LINK_ADDRESS, QUERY_BY_REMOTE_ID):
            raise ReplyWithLeasequeryError(STATUS_NOT_ALLOWED,
                                           "Query type {} is only allowed over bulk leasequery".format(
                                               query.query_type))
