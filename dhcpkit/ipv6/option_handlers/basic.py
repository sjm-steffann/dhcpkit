"""
Option handlers for the basic :rfc:`3315` options
"""

import logging

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.exceptions import CannotRespondError
from dhcpkit.ipv6.messages import ConfirmMessage, ReleaseMessage, DeclineMessage
from dhcpkit.ipv6.option_handlers import CopyOptionHandler, OverwritingOptionHandler, OptionHandler
from dhcpkit.ipv6.options import ClientIdOption, ServerIdOption, StatusCodeOption, STATUS_SUCCESS
from dhcpkit.ipv6.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class ClientIdOptionHandler(CopyOptionHandler):
    """
    The handler for ClientIdOptions
    """

    def __init__(self):
        super().__init__(ClientIdOption, always_send=True)


class ServerIdOptionHandler(OverwritingOptionHandler):
    """
    The handler for ServerIdOption. Checks whether any server-id in the request matches our own and puts our server-id
    in the response message to let the client know who is answering.

    :type option: ServerIdOption
    """

    option = None

    def __init__(self, duid: DUID):
        """
        Create a handler function based on the provided DUID

        :param duid: The DUID of this server
        """
        option = ServerIdOption(duid)
        option.validate()

        super().__init__(option, always_send=True)

    def pre(self, bundle: TransactionBundle):
        """
        Check if there is a ServerId in the request

        :param bundle: The transaction bundle
        """
        server_id = bundle.request.get_option_of_type(ServerIdOption)
        if server_id and server_id.duid != self.option.duid:
            # This message is not for this server
            raise CannotRespondError


class ConfirmStatusOptionHandler(OptionHandler):
    """
    The handler that makes sure that replies to confirm messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.ConfirmMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, ConfirmMessage):
            existing = bundle.response.get_option_of_type(StatusCodeOption)
            if not existing:
                bundle.response.options.append(
                    StatusCodeOption(STATUS_SUCCESS, "Assignments confirmed")
                )


class ReleaseStatusOptionHandler(OptionHandler):
    """
    The handler that makes sure that replies to release messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.ReleaseMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, ReleaseMessage):
            existing = bundle.response.get_option_of_type(StatusCodeOption)
            if not existing:
                bundle.response.options.append(
                    StatusCodeOption(STATUS_SUCCESS,
                                     "Thank you for releasing your resources")
                )


class DeclineStatusOptionHandler(OptionHandler):
    """
    The handler that makes sure that replies to decline messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.DeclineMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, DeclineMessage):
            existing = bundle.response.get_option_of_type(StatusCodeOption)
            if not existing:
                bundle.response.options.append(
                    StatusCodeOption(STATUS_SUCCESS,
                                     "Our apologies for assigning you unusable addresses")
                )
