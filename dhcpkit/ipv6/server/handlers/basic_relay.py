"""
Basic handlers for relay options
"""
import logging

import abc

from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class RelayOptionHandler(Handler):
    """
    A base class for handlers that work on option in the relay messages chain.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Handle the data in the bundle by checking the relay chain and calling :meth:`handle_relay` for each relay
        message.

        :param bundle: The transaction bundle
        """
        # We need the outgoing chain to be present
        if bundle.outgoing_relay_messages is None:
            logger.error("Cannot process relay chains: outgoing chain not set")
            return

        # Don't try to match between chains of different size
        if len(bundle.incoming_relay_messages) != len(bundle.outgoing_relay_messages):
            logger.error("Cannot process relay chains: chain have different length")
            return

        # Process the relay messages one by one
        for relay_message_in, relay_message_out in zip(bundle.incoming_relay_messages, bundle.outgoing_relay_messages):
            self.handle_relay(bundle, relay_message_in, relay_message_out)

    @abc.abstractmethod
    def handle_relay(self, bundle: TransactionBundle,
                     relay_message_in: RelayForwardMessage, relay_message_out: RelayReplyMessage):
        """
        Handle the options for each relay message pair.

        :param bundle: The transaction bundle
        :param relay_message_in: The incoming relay message
        :param relay_message_out: Thr outgoing relay message
        """


class CopyRelayOptionHandler(RelayOptionHandler):
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
