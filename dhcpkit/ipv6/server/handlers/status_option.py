"""
Some messages need a status code in the response. These handlers insert that status code if no other handler did.
"""
from dhcpkit.ipv6.messages import ConfirmMessage, DeclineMessage, ReleaseMessage
from dhcpkit.ipv6.options import STATUS_SUCCESS, StatusCodeOption
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class AddMissingStatusOptionHandler(Handler):
    """
    The handler that makes sure that replies to confirm messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.ConfirmMessage`, :class:`.ReleaseMessage` and
        :class:`.DeclineMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, ConfirmMessage):
            message = "Assignments confirmed"
        elif isinstance(bundle.request, ReleaseMessage):
            message = "Thank you for releasing your resources"
        elif isinstance(bundle.request, DeclineMessage):
            message = "Our apologies for assigning you unusable addresses"
        else:
            # Not a message type we're interested in
            return

        existing = bundle.response.get_option_of_type(StatusCodeOption)
        if not existing:
            bundle.response.options.append(
                StatusCodeOption(STATUS_SUCCESS, status_message=message)
            )
