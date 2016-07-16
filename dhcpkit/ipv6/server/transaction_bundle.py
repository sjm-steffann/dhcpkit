"""
An object to hold everything related to a request/response transaction
"""
import codecs
import logging
from ipaddress import IPv6Address

from typing import Tuple, List, TypeVar, Type, Iterable

from dhcpkit.ipv6.messages import Message, RelayForwardMessage, ClientServerMessage, RelayReplyMessage
from dhcpkit.ipv6.options import Option, ClientIdOption
from dhcpkit.ipv6.utils import split_relay_chain

logger = logging.getLogger(__name__)

# Typing helpers
SomeOption = TypeVar('SomeOption', bound='Option')


class TransactionBundle:
    """
    A bundle with all data about a transaction. This makes it much easier to pass around multiple pieces of information.

    :type incoming_message: Message
    :type received_over_multicast: bool
    :type request: ClientServerMessage
    :type incoming_relay_messages: List[RelayForwardMessage]
    :type response: Optional[ClientServerMessage]
    :type outgoing_relay_messages: Optional[List[RelayReplyMessage]]
    :type handled_options: List[Option]
    :type marks: Set[str]
    :type handler_data: Dict[Handler, object]
    """

    def __init__(self, incoming_message: Message, received_over_multicast: bool, allow_rapid_commit: bool = False,
                 marks: Iterable[str] = None):

        self.incoming_message = incoming_message
        """The incoming message including the relay chain"""

        self.received_over_multicast = received_over_multicast
        """A flag indicating whether the client used multicast to contact the server"""

        self.allow_unicast = False
        """Allow the client use unicast to contact the server. Set to True by handlers"""

        self.allow_rapid_commit = allow_rapid_commit
        """Allow rapid commit? May be set to True on creation, may be set to False by handlers, not vice versa"""

        # Convenience properties for easy access to the request and chain without having to walk the chain every time
        self.request = None
        """The incoming request without the relay messages"""

        self.incoming_relay_messages = []
        """The chain of relay messages starting with the one closest to the client"""

        self.request, self.incoming_relay_messages = split_relay_chain(incoming_message)

        self.response = None
        """This is where the user puts the response :class:`.ClientServerMessage`"""

        self.outgoing_relay_messages = None
        """This is where the user puts the reply relay chain by calling :meth:`create_outgoing_relay_messages`"""

        # Extra state to track handling of the message
        self.handled_options = []
        """A list of options from the request that have been handled, only applies to IA type options"""

        self.marks = set(marks or [])
        """A set of marks that have been applied to this message"""

        self.handler_data = {}
        """A place for handlers to store data related to this transaction"""

    def __str__(self) -> str:
        client_id = self.request.get_option_of_type(ClientIdOption)
        if client_id:
            duid = codecs.encode(client_id.save(), 'hex').decode('ascii')
        else:
            duid = 'unknown'

        output = "{} from {}".format(type(self.request).__name__, duid)

        interesting_relay_messages = [message for message in self.incoming_relay_messages
                                      if not message.link_address.is_unspecified]
        if interesting_relay_messages:
            output += ' at {} via {}'.format(interesting_relay_messages[0].peer_address,
                                             interesting_relay_messages[0].link_address)
            for relay in interesting_relay_messages[1:]:
                output += ' -> {}'.format(relay.link_address)

        if self.marks:
            output += " with marks '{}'".format("', '".join(self.marks))

        return output

    def mark_handled(self, option: Option):
        """
        Mark the given option as handled. Not all options are specifically handled. This is mostly useful for
        options like IANAOption, IATAOption and IAPDOption.

        :param option: The option to mark as handled
        """
        if option not in self.handled_options:
            self.handled_options.append(option)

    def get_unhandled_options(self, option_types: Type[SomeOption] or Tuple[Type[SomeOption]]) -> List[SomeOption]:
        """
        Get a list of all Options in the request that haven't been marked as handled

        :return: The list of unanswered Options
        """
        # Make a list of requested IANAOptions
        return [option for option in self.request.options
                if isinstance(option, option_types) and option not in self.handled_options]

    def add_mark(self, mark: str):
        """
        Add this mark to the set.

        :param mark: The mark to add
        """
        self.marks.add(mark.strip())

    @property
    def link_address(self) -> IPv6Address:
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

        self.outgoing_relay_messages = []
        if not self.incoming_relay_messages:
            return

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
