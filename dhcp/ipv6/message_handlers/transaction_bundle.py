"""
An object to hold everything related to a request/response transaction
"""
from ipaddress import IPv6Address
import logging

from dhcp.ipv6.messages import Message, RelayForwardMessage, ClientServerMessage, UnknownMessage

logger = logging.getLogger(__name__)


class TransactionBundle:
    """
    A bundle with all data about a transaction. This makes it much easier to pass around multiple pieces of information.

    :type incoming_message: Message
    :type received_over_multicast: bool
    :type request: ClientServerMessage
    :type relay_messages: list[RelayForwardMessage]
    :type response: ClientServerMessage
    :type handler_state: dict[OptionHandler, object]
    """

    def __init__(self, incoming_message: Message, received_over_multicast: bool):
        self.incoming_message = incoming_message
        self.received_over_multicast = received_over_multicast

        # Convenience properties for easy access to the request and chain without having to walk the chain every time
        self.request, self.relay_messages = self.split_relay_chain(incoming_message)

        # This is where the user puts the response
        # (without reply relay chain, that is added by @property outgoing_message)
        self.response = None

        # State holding space for option handlers, indexed by option handler object
        self.handler_state = {}

    @staticmethod
    def split_relay_chain(message: Message) -> (ClientServerMessage, [RelayForwardMessage]):
        """
        Separate the relay chain from the actual request message.

        :param message: The incoming message
        :returns: The request and the chain of relay messages starting with the one closest to the client
        """
        relay_messages = []
        while isinstance(message, RelayForwardMessage):
            relay_messages.insert(0, message)
            message = message.relayed_message

        # Check if we could actually read the message
        if isinstance(message, UnknownMessage):
            logger.warning("Received an unrecognised message of type {}".format(message.message_type))
            return None, None

        # Check that this message is a client->server message
        if not isinstance(message, ClientServerMessage) or not message.from_client_to_server:
            logger.warning("A server should not receive {} from a client".format(message.__class__.__name__))
            return None, None

        # Save it as the request
        return message, relay_messages

    def get_link_addresses(self) -> [IPv6Address]:
        """
        Find the link address that identifies where this request is coming from
        """
        # Start with the relay closest to the client and keep looking until a useful address is found
        for relay in self.relay_messages:
            # Some relays (i.e. LDRA: https://tools.ietf.org/html/rfc6221) don't have a useful link-address
            if not relay.link_address.is_unspecified and \
                    not relay.link_address.is_loopback and \
                    not relay.link_address.is_link_local:
                # This looks useful
                return [relay.link_address]

        # We shouldn't get to this point
        raise ValueError("Could not determine the link that the request came from")

    @property
    def outgoing_message(self):
        """
        Wrap the response in a relay chain if necessary
        """
        if self.response is None:
            # No response is ok
            return None

        response = self.response
        if response and not response.from_server_to_client:
            logger.error("A server should not send {} to a client".format(response.__class__.__name__))
            return None

        # If it's a plain ClientServerMessage then wrap it in RelayReplyMessage if necessary
        if isinstance(response, ClientServerMessage) and self.relay_messages:
            response = self.relay_messages[-1].wrap_response(response)

        return response
