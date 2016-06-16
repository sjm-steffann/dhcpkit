"""
Basic handlers for options
"""

import logging

from dhcpkit.ipv6.options import OptionRequestOption, Option
from dhcpkit.ipv6.server.handlers import Handler, CannotRespondError
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class IgnoreRequestHandler(Handler):
    """
    A simple handler that tells the server to stop processing the request and ignore it
    """

    def pre(self, bundle: TransactionBundle):
        """
        Stop processing

        :param bundle: The transaction bundle
        """
        logging.info("Configured to ignore {}".format(bundle))
        raise CannotRespondError("Ignoring request")


class CopyOptionHandler(Handler):
    """
    This handler just copies a type of option from the request to the response

    :param option_class: The option class to copy
    :param always_send: Always send this option, even if the OptionRequestOption doesn't ask for it
    """

    def __init__(self, option_class: type(Option), *, always_send: bool = False):
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
            if oro and self.option_class.option_type not in oro.requested_options:
                # Client doesn't want this
                return

        # Make sure this option isn't present and then copy those from the request
        bundle.response.options = [existing_option for existing_option in bundle.response.options
                                   if not isinstance(existing_option, self.option_class)]
        bundle.response.options[:0] = bundle.request.get_options_of_type(self.option_class)


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
