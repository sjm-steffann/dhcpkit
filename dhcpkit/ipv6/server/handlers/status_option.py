"""
Some messages need a status code in the response. These handlers insert that status code if no other handler did.
"""
from dhcpkit.ipv6.messages import ConfirmMessage, ReleaseMessage, DeclineMessage
from dhcpkit.ipv6.options import StatusCodeOption, STATUS_SUCCESS, STATUS_NOBINDING
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class ConfirmStatusOptionHandler(Handler):
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
                    StatusCodeOption(STATUS_NOBINDING, "Assignments confirmed")
                )


class ReleaseStatusOptionHandler(Handler):
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


class DeclineStatusOptionHandler(Handler):
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
