"""
Classes that handle the processing of an option
"""
import abc
import configparser
import importlib
import logging
import pkgutil

from dhcpkit.ipv6.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.messages import RelayReplyMessage, RelayForwardMessage
from dhcpkit.ipv6.options import OptionRequestOption, Option

logger = logging.getLogger(__name__)


# The registry that keeps track of which class implements which option handler name
# type: {str: OptionHandler}
option_handler_name_registry = {}


def register_option_handler(subclass: type):
    """
    Register a new option handler in the option handler registry.

    :param subclass: A subclass of OptionHandler that implements the handler
    """
    from dhcpkit.ipv6.option_handlers import OptionHandler
    from dhcpkit.utils import camelcase_to_dash

    if not issubclass(subclass, OptionHandler):
        raise TypeError('Only OptionHandlers can be registered')

    # Store based on name
    name = subclass.__name__
    if name.endswith('Handler'):
        name = name[:-7]
    if name.endswith('Option'):
        name = name[:-6]
    name = camelcase_to_dash(name)
    option_handler_name_registry[name] = subclass


def load_all():
    """
    Load all option handlers
    """
    for module_finder, name, is_pkg in pkgutil.iter_modules(__path__):
        # Make sure we import all extensions we know about
        importlib.import_module('{}.{}'.format(__name__, name))


class OptionHandler(metaclass=abc.ABCMeta):
    """
    Base class for option handlers
    """

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> object:
        """
        Create a handler of this class based on the configuration in the config section. No default implementation
        is provided. Subclasses should implement their own if they want to be loaded from a configuration file.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier for an option handler
        :return: A handler object
        :rtype: OptionHandler
        """
        raise configparser.Error("{} does not support loading from configuration".format(cls.__name__))

    # noinspection PyMethodMayBeStatic
    def pre(self, bundle: TransactionBundle):
        """
        Pre-process the data in the bundle. Subclasses can update bundle state here or abort processing of the request
        by raising a CannotRespondError.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    @abc.abstractmethod
    def handle(self, bundle: TransactionBundle):
        """
        Handle the data in the bundle. Should do their main work here.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def post(self, bundle: TransactionBundle):
        """
        Post-process the data in the bundle. Subclasses can e.g. clean up state.

        :param bundle: The transaction bundle
        """


class RelayOptionHandler(OptionHandler):
    """
    A base class for option handlers that work on option in the relay messages chain.
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


class SimpleOptionHandler(OptionHandler):
    """
    Standard handler for simple static options

    :param option: The option instance to add to the response
    :param append: Always add, even if an option of this class already exists
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option: Option, *, append: bool=False, always_send: bool=False):
        self.option = option
        """The option instance to add to the response"""

        self.option_class = type(option)
        """The class of the option"""

        self.append = append
        """Always add, even if an option of this class already exists"""

        self.always_send = always_send
        """Always send this option, even if the :class:`.OptionRequestOption` doesn't ask for it"""

    def handle(self, bundle: TransactionBundle):
        """
        Add the option to the response in the bundle.

        :param bundle: The transaction bundle
        """
        # Make sure this option can go into this type of response
        if not bundle.response.may_contain(self.option):
            return

        # Check what the client requested
        if not self.always_send:
            # Don't add if the client doesn't request it
            oro = bundle.request.get_option_of_type(OptionRequestOption)
            if oro and self.option.option_type not in oro.requested_options:
                # Client doesn't want this
                return

        if self.append:
            # Just add
            add = True
        else:
            # See if this option was already present
            found = bundle.response.get_option_of_type(self.option_class)
            add = not found

        if add:
            # We always want to add it, or it didn't exist yet
            bundle.response.options.append(self.option)


class OverwritingOptionHandler(OptionHandler):
    """
    Overwriting handler for simple static options.

    :param option: The option instance to use
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option: object, *, always_send: bool=False):
        """
        :type option: Option
        """
        self.option = option
        """The option to add to the response"""

        self.option_class = type(option)
        """The class of the option"""

        self.always_send = always_send
        """Whether an :class:`.OptionRequestOption` in the request should be ignored"""

    def handle(self, bundle: TransactionBundle):
        """
        Overwrite the option in the response in the bundle.

        :param bundle: The transaction bundle
        """
        # Make sure this option can go into this type of response
        if not bundle.response.may_contain(self.option):
            return

        # Check what the client requested
        if not self.always_send:
            # Don't add if the client doesn't request it
            oro = bundle.request.get_option_of_type(OptionRequestOption)
            if oro and self.option.option_type not in oro.requested_options:
                # Client doesn't want this
                return

        # Make sure this option isn't present and then add our own
        bundle.response.options = [existing_option for existing_option in bundle.response.options
                                   if not isinstance(existing_option, self.option_class)]
        bundle.response.options.insert(0, self.option)


class CopyOptionHandler(OptionHandler):
    """
    This handler just copies a type of option from the request to the response

    :param option_class: The option class to copy
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option_class: object, *, always_send: bool=False):
        """
        :type option_class: Option
        """
        self.option_class = option_class
        """The class of the option from the request to the response"""

        self.always_send = always_send
        """Whether an :class:`.OptionRequestOption` in the request should be ignored"""

    def handle(self, bundle: TransactionBundle):
        """
        Copy the option from the request to the response.

        :param bundle: The transaction bundle
        """
        # Make sure this option can go into this type of response
        if not bundle.response.may_contain(self.option_class):
            return

        # Check what the client requested
        if not self.always_send:
            # Don't add if the client doesn't request it
            oro = bundle.request.get_option_of_type(OptionRequestOption)
            if oro and self.option_class.option_type not in oro.requested_options:
                # Client doesn't want this
                return

        # Make sure this option isn't present and then copy those from the request
        bundle.response.options = [existing_option for existing_option in bundle.response.options
                                   if not isinstance(existing_option, self.option_class)]
        bundle.response.options[:0] = bundle.request.get_options_of_type(self.option_class)


class CopyRelayOptionHandler(RelayOptionHandler):
    """
    This handler just copies a type of option from the incoming relay messages to the outgoing relay messages

    :param option_class: The option class to copy
    """

    def __init__(self, option_class: object):
        """
        :type option_class: Option
        """
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
