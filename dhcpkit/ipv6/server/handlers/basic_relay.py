"""
Basic handlers for relay options
"""
import logging

from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.server.handlers import Handler, RelayHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class CopyRelayOptionHandler(RelayHandler):
    """
    This handler just copies a type of option from the incoming relay messages to the outgoing relay messages

    :param option_class: The option class to copy
    """

    def __init__(self, option_class: type(Handler)):
        super().__init__()
        self.option_class = option_class
        """The class of the option from the :class:`.RelayForwardMessage` to the :class:`.RelayReplyMessage`"""

    def handle_relay(self, bundle: TransactionBundle,
                     relay_message_in: RelayForwardMessage, relay_message_out: RelayReplyMessage):
        """
        Copy the options for each relay message pair.

        :param bundle: The transaction bundle
        :param relay_message_in: The incoming relay message
        :param relay_message_out: Thr outgoing relay message
        """
        # Make sure this option can go into this type of response
        if not relay_message_out.may_contain(self.option_class):
            return

        # Make sure this option isn't present and then copy those from the request
        relay_message_out.options = [existing_option for existing_option in relay_message_out.options
                                     if not isinstance(existing_option, self.option_class)]
        relay_message_out.options[:0] = relay_message_in.get_options_of_type(self.option_class)
