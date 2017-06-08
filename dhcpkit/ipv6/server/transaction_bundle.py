"""
An object to hold everything related to a request/response transaction
"""
import codecs
import logging
from ipaddress import IPv6Address
from typing import Iterable, Iterator, List, Optional, Tuple, Type, TypeVar

from dhcpkit.ipv6.messages import ClientServerMessage, Message, RelayReplyMessage
from dhcpkit.ipv6.options import ClientIdOption, Option
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
    :type responses: MessagesList
    :type outgoing_relay_messages: Optional[List[RelayReplyMessage]]
    :type handled_options: List[Option]
    :type marks: Set[str]
    :type handler_data: Dict[Handler, object]
    """

    def __init__(self, incoming_message: Message, received_over_multicast: bool, received_over_tcp: bool = False,
                 allow_rapid_commit: bool = False, marks: Iterable[str] = None):

        self.incoming_message = incoming_message
        """The incoming message including the relay chain"""

        self.received_over_multicast = received_over_multicast
        """A flag indicating whether the client used multicast to contact the server"""

        self.received_over_tcp = received_over_tcp
        """A flag indicating whether the client used TCP to contact the server"""

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

        # Check that TCP connections don't include any further relay messages
        if self.received_over_tcp and len(self.incoming_relay_messages) > 1:
            raise ValueError("Relayed message on TCP connection, ignoring")

        self.responses = MessagesList()
        """This is where we keep our responses, potentially more than one"""

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
            duid = codecs.encode(client_id.duid.save(), 'hex').decode('ascii')
        else:
            duid = 'unknown'

        output = "{} from {}".format(type(self.request).__name__, duid)

        if self.received_over_tcp:
            output += ' over TCP'

        if self.incoming_relay_messages:
            link_address = self.incoming_relay_messages[0].link_address
            link_name = str(link_address) if not link_address.is_unspecified else 'LDRA'

            output += ' at {} via {}'.format(self.incoming_relay_messages[0].peer_address, link_name)
            for relay in self.incoming_relay_messages[1:]:
                link_name = str(relay.link_address) if not relay.link_address.is_unspecified else 'LDRA'
                output += ' -> {}'.format(link_name)

        if self.marks:
            output += " with marks '{}'".format("', '".join(self.marks))

        return output

    @property
    def response(self):
        """
        Backwards-compatibility handling for when we only supported one response. TCP connections can support more than
        one response, but for normal DHCPv6 a single response is all we need is a single one, so make this use-case
        easy and backwards-compatible.

        :return: The first response
        """
        if not self.responses:
            return None

        return self.responses[0]

    @response.setter
    def response(self, new_response: ClientServerMessage):
        """
        Backwards-compatibility handling for when we only supported one response. TCP connections can support more than
        one response, but for normal DHCPv6 a single response is all we need is a single one, so make this use-case
        easy and backwards-compatible.

        :param new_response: The new response
        """
        if new_response is None:
            # No response: remove all of them
            self.responses = MessagesList()
        elif self.responses:
            # We already have a response, overwrite first
            self.responses[0] = new_response
        else:
            # No responses yet, this is the first one
            self.responses = MessagesList(new_response)

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
        Find the link address that identifies where this request is coming from. For TCP connections we use the remote
        endpoint of the connection instead.
        """
        # Use remote TCP endpoint
        if self.received_over_tcp:
            return self.incoming_relay_messages[-1].peer_address

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

    @property
    def relays(self) -> List[IPv6Address]:
        """
        Get a list of all the relays that this message went through
        """
        return [relay.link_address for relay in self.incoming_relay_messages
                if not relay.link_address.is_unspecified]

    def create_outgoing_relay_messages(self):
        """
        Create a plain chain of RelayReplyMessages for the current response
        """
        self.outgoing_relay_messages = []
        if not self.incoming_relay_messages:
            return

        outgoing_message = self.incoming_relay_messages[-1].wrap_response(self.response)
        self.outgoing_relay_messages = []
        while isinstance(outgoing_message, RelayReplyMessage):
            self.outgoing_relay_messages.insert(0, outgoing_message)
            outgoing_message = outgoing_message.relayed_message

    @property
    def outgoing_message(self) -> Optional[RelayReplyMessage]:
        """
        Wrap the response in a relay chain if necessary. Only works when there is a single response.
        """
        if self.response is None:
            # No response is ok
            return None

        messages = list(self.outgoing_messages)
        if not messages:
            return None
        else:
            return messages[0]

    @property
    def outgoing_messages(self) -> Iterable[RelayReplyMessage]:
        """
        Wrap the responses in a relay chain if necessary and iterate over them.

        .. warning::
            Be careful when iterating over outgoing messages. When iterating over multiple responses the original relay
            messages will be updated to contain the next response when proceeding the the next one!
        """
        if self.incoming_relay_messages and not self.outgoing_relay_messages:
            # No outgoing relay messages, but we had incoming relay messages: auto-create a plain relay chain
            self.create_outgoing_relay_messages()

        for response in self.responses:
            if not response.from_server_to_client:
                logger.error("A server should not send {} to a client".format(response.__class__.__name__))
                continue

            if self.outgoing_relay_messages:
                # Make sure the right response is in the relay messages (in case someone overwrites :attr:`response`
                # without updating the contents of the relay messages as well. If there are multiple responses we
                # reuse the existing relay messages.
                self.outgoing_relay_messages[0].relayed_message = response

                # Send the relay messages
                yield self.outgoing_relay_messages[-1]
            else:
                # Send the plain response
                yield response


class MessagesList:
    """
    A weird iterator wrapper. This allows handlers to manipulate the first message while not needing to load all of the
    subsequent messages in memory.
    """

    def __init__(self, first_message: ClientServerMessage = None,
                 subsequent_messages: Iterator[ClientServerMessage] = None):
        self.first_message = first_message
        self.subsequent_messages = subsequent_messages or iter([])
        self.has_been_iterated_over = False

    def __iter__(self) -> Iterator[ClientServerMessage]:
        """
        An iterator for our messages.

        :return: The messages
        """
        if not self.first_message:
            return

        yield self.first_message
        yield from self.subsequent_messages

    def __getitem__(self, index: int) -> ClientServerMessage:
        """
        We are asked for a specific index, we only support 0.

        :param index: Index of the requested message
        :return: The requested message
        """
        if index != 0:
            raise IndexError("MessagesList only supports directly accessing the first message directly")

        if self.first_message:
            return self.first_message
        else:
            raise IndexError

    def __setitem__(self, index: int, new_message: ClientServerMessage):
        """
        Overwrite the first message (we only support index 0).

        :param index: The index of the message to be overwritten
        :param new_message: The new message
        """
        if index != 0:
            raise IndexError("MessagesList only supports directly accessing the first message directly")

        self.first_message = new_message

    def __bool__(self):
        """
        Return whether there are messages, i.e. there is at least a first message.

        :return: Whether we have messages
        """
        return bool(self.first_message)
