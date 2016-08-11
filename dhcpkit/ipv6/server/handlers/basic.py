"""
Basic handlers for options
"""

import logging

from dhcpkit.ipv6.options import Option, OptionRequestOption
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from typing import Iterable, Optional, Type

logger = logging.getLogger(__name__)


class CopyOptionHandler(Handler):
    """
    This handler just copies a type of option from the request to the response

    :param option_class: The option class to copy
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option_class: Type[Option], *, always_send: bool = False):
        super().__init__()

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
            # noinspection PyUnresolvedReferences
            if oro and self.option_class.option_type not in oro.requested_options:
                # Client doesn't want this
                return

        # Make sure this option isn't present and then copy those from the request
        bundle.response.options = [existing_option for existing_option in bundle.response.options
                                   if not isinstance(existing_option, self.option_class)]
        bundle.response.options[:0] = bundle.request.get_options_of_type(self.option_class)


class SimpleOptionHandler(Handler):
    """
    Standard handler for simple static options

    :param option: The option instance to add to the response
    :param append: Always add, even if an option of this class already exists
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option: Option, *, append: bool = False, always_send: bool = False):
        super().__init__()

        self.option = option
        """The option instance to add to the response"""

        self.option_class = type(option)
        """The class of the option"""

        self.append = append
        """Always add, even if an option of this class already exists"""

        self.always_send = always_send
        """Always send this option, even if the :class:`.OptionRequestOption` doesn't ask for it"""

    def combine(self, existing_options: Iterable[Option]) -> Optional[Option]:
        """
        If an option of this type already exists this method can combine the existing option with our own option to
        create a combined option.

        :param existing_options: The existing options
        :return: The combined option which will replace all existing options, or None to leave the existing options
        """
        # By default we just leave the existing options alone
        return None

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
            found = bundle.response.get_options_of_type(self.option_class)
            if found:
                result = self.combine(existing_options=found)
                if isinstance(result, Option):
                    # A new option, remove the old ones
                    for option in found:
                        bundle.response.options.remove(option)

                    # And add the combined one
                    bundle.response.options.append(result)

                # Don't add the standard version
                add = False
            else:
                # The option didn't exist yet, just add it
                add = True

        if add:
            # We always want to add it, or it didn't exist yet
            bundle.response.options.append(self.option)


class OverwriteOptionHandler(Handler):
    """
    Overwriting handler for simple static options.

    :param option: The option instance to use
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option: Option, *, always_send: bool = False):
        super().__init__()

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
