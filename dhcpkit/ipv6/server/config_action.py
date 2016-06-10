"""
Actions: the things that take action on an incoming message and possibly update the response
"""
import logging

import abc

from dhcpkit.common.server.config_elements import ConfigSection
from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class ActionException(Exception):
    """
    Base class for action exceptions
    """


class CannotRespondError(ActionException):
    """
    This exception signals that we cannot reply to this client.
    """


class UseMulticastError(ActionException):
    """
    This exception signals that a STATUS_USEMULTICAST should be returned to the client.
    """


class Action(ConfigSection, metaclass=abc.ABCMeta):
    """
    Base class for actions
    """

    # noinspection PyMethodMayBeStatic
    def pre(self, bundle: TransactionBundle):
        """
        Pre-process the data in the bundle. Subclasses can update bundle state here or abort processing of the request
        by raising a CannotRespondError.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def handle(self, bundle: TransactionBundle):
        """
        Handle the data in the bundle. Subclasses should do their main work here.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def post(self, bundle: TransactionBundle):
        """
        Post-process the data in the bundle. Subclasses can e.g. clean up state. Subclasses assigning addresses should
        check whether the bundle.response is an AdvertiseMessage or a ReplyMessage. The class can change between
        handle() and post() when the server is using rapid-commit.

        :param bundle: The transaction bundle
        """


class RelayOptionHandler(Action):
    """
    A base class for actions that work on option in the relay messages chain.
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


class IgnoreRequestAction(Action):
    """
    A simple action that tells the server to stop processing the request and ignore it
    """

    def pre(self, bundle: TransactionBundle):
        """
        Stop processing

        :param bundle: The transaction bundle
        """
        logging.info("Configured to ignore {}".format(bundle))
        raise CannotRespondError("Ignoring request")
