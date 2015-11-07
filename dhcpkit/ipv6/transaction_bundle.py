"""
An object to hold everything related to a request/response transaction
"""
import logging
from ipaddress import IPv6Address

from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption
from dhcpkit.ipv6.messages import Message, RelayForwardMessage, ClientServerMessage, UnknownMessage, RelayReplyMessage
from dhcpkit.ipv6.options import Option, IANAOption, IATAOption

logger = logging.getLogger(__name__)


class TransactionBundle:
    """
    A bundle with all data about a transaction. This makes it much easier to pass around multiple pieces of information.

    :type incoming_message: Message
    :type received_over_multicast: bool
    :type request: ClientServerMessage
    :type incoming_relay_messages: list[RelayForwardMessage]
    :type response: ClientServerMessage
    :type outgoing_relay_messages: list[RelayReplyMessage]
    :type handled_options: list[Option]
    """

    def __init__(self, incoming_message: Message, received_over_multicast: bool, allow_rapid_commit: bool = False):
        self.allow_rapid_commit = allow_rapid_commit
        """Allow rapid commit? May be set to True on creation, may be set to False by option handlers, not vice versa"""

        self.incoming_message = incoming_message
        """The incoming message including the relay chain"""

        self.received_over_multicast = received_over_multicast
        """A flag indicating whether the client used multicast to contact the server"""

        # Convenience properties for easy access to the request and chain without having to walk the chain every time
        self.request = None
        """The incoming request without the relay messages"""

        self.incoming_relay_messages = []
        """The chain of relay messages starting with the one closest to the client"""

        self.request, self.incoming_relay_messages = self.split_relay_chain(incoming_message)

        self.response = None
        """This is where the user puts the response :class:`.ClientServerMessage`"""

        self.outgoing_relay_messages = None
        """This is where the user puts the reply relay chain by calling :meth:`create_outgoing_relay_messages`"""

        self.handled_options = []
        """A list of options from the request that have been handled, only applies to IA type options"""

    def mark_handled(self, option: Option):
        """
        Mark the given option as handled
        :param option:
        :return:
        """
        if option not in self.handled_options:
            self.handled_options.append(option)

    def get_unanswered_ia_options(self) -> [IANAOption or IATAOption]:
        """
        Get a list of all IANAOptions and IATAOptions in the request that have no counterpart in the response

        :return: The list of unanswered IANAOptions and IATAOptions
        :rtype: list[IANAOption or IATAOption]
        """
        # Make a list of requested IANAOptions
        return [option for option in self.request.options
                if isinstance(option, (IANAOption, IATAOption)) and option not in self.handled_options]

    def get_unanswered_iana_options(self) -> [IANAOption]:
        """
        Get a list of all IANAOptions in the request that have no counterpart in the response

        :return: The list of unanswered IANAOptions
        :rtype: list[IANAOption]
        """
        # Make a list of requested IANAOptions
        return [option for option in self.request.options
                if isinstance(option, IANAOption) and option not in self.handled_options]

    def get_unanswered_iata_options(self) -> [IATAOption]:
        """
        Get a list of all IATAOptions in the request that have no counterpart in the response

        :return: The list of unanswered IATAOptions
        :rtype: list[IATAOption]
        """
        # Make a list of requested IANAOptions
        return [option for option in self.request.options
                if isinstance(option, IATAOption) and option not in self.handled_options]

    def get_unanswered_iapd_options(self) -> [IAPDOption]:
        """
        Get a list of all IANAOptions in the request that have no counterpart in the response

        :return: The list of unanswered IAPDOptions
        :rtype: list[IAPDOption]
        """
        # Make a list of requested IANAOptions
        return [option for option in self.request.options
                if isinstance(option, IAPDOption) and option not in self.handled_options]

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

    def get_link_address(self) -> IPv6Address:
        """
        Find the link address that identifies where this request is coming from
        """
        # Start with the relay closest to the client and keep looking until a useful address is found
        for relay in self.incoming_relay_messages:
            # Some relays (i.e. LDRA: :rfc:`6221`) don't have a useful link-address
            if not relay.link_address.is_unspecified and \
                    not relay.link_address.is_loopback and \
                    not relay.link_address.is_link_local:
                # This looks useful
                return relay.link_address

        # Nothing useful...
        return IPv6Address('::')

    def create_outgoing_relay_messages(self):
        """
        Create a plain chain of RelayReplyMessages for the current response
        """
        if not self.response:
            raise ValueError("Cannot create outgoing relay messages without a response")

        outgoing_message = self.incoming_relay_messages[-1].wrap_response(self.response)
        self.outgoing_relay_messages = []
        while isinstance(outgoing_message, RelayReplyMessage):
            self.outgoing_relay_messages.insert(0, outgoing_message)
            outgoing_message = outgoing_message.relayed_message

    @property
    def outgoing_message(self):
        """
        Wrap the response in a relay chain if necessary
        """
        if self.response is None:
            # No response is ok
            return None

        if not self.response.from_server_to_client:
            logger.error("A server should not send {} to a client".format(self.response.__class__.__name__))
            return None

        if self.incoming_relay_messages and not self.outgoing_relay_messages:
            # No outgoing relay messages, but we had incoming relay messages: auto-create a plain relay chain
            self.create_outgoing_relay_messages()

        if self.outgoing_relay_messages:
            # Make sure the right response is in the relay messages (in case someone overwrites :attr:`response` without
            # updating the contents of the relay messages as well
            self.outgoing_relay_messages[0].relayed_message = self.response

            # Send the relay messages
            return self.outgoing_relay_messages[-1]
        else:
            # Send the plain response
            return self.response
