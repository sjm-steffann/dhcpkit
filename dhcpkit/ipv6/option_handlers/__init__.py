"""
Classes that handle the processing of an option
"""
import configparser
import importlib
import logging
import pkgutil

from dhcpkit.ipv6.message_handlers.transaction_bundle import TransactionBundle
from dhcpkit.ipv6.options import OptionRequestOption

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


class OptionHandler:
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
        by raising a CannotReplyError.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def handle(self, bundle: TransactionBundle):
        """
        handle the data in the bundle. Should do their main work here.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def post(self, bundle: TransactionBundle):
        """
        Post-process the data in the bundle. Subclasses can e.g. clean up state.

        :param bundle: The transaction bundle
        """


class SimpleOptionHandler(OptionHandler):
    """
    Standard handler for simple static options

    :param option: The option instance to use
    :param append: Always add, even if an option of this type already exists
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option: object, *, append: bool=False, always_send: bool=False):
        """
        :type option: Option
        """
        self.option = option
        self.option_class = type(option)
        self.append = append
        self.always_send = always_send

    # noinspection PyDocstring
    def handle(self, bundle: TransactionBundle):
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
        self.option_class = type(option)
        self.always_send = always_send

    # noinspection PyDocstring
    def handle(self, bundle: TransactionBundle):
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
        self.always_send = always_send

    # noinspection PyDocstring
    def handle(self, bundle: TransactionBundle):
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
        bundle.response.options[:0] = [existing_option for existing_option in bundle.request.options
                                       if isinstance(existing_option, self.option_class)]
