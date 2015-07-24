"""
Classes that handle the processing of an option
"""
from dhcp.ipv6.handlers.transaction_bundle import TransactionBundle


class OptionHandler:
    """
    Base class for option handlers
    """
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
        from dhcp.ipv6.options import OptionRequestOption

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
    Overwriting handler for simple static options. Processing is done in the post method so we see everything that
    happened during normal processing.

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
    def post(self, bundle: TransactionBundle):
        from dhcp.ipv6.options import OptionRequestOption

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
    def post(self, bundle: TransactionBundle):
        from dhcp.ipv6.options import OptionRequestOption

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


class UnansweredIANAOptionHandler(OptionHandler):
    """
    A handler that checks that all IANOptions in the request have an answer
    """

    # noinspection PyDocstring
    def post(self, bundle: TransactionBundle):
        from dhcp.ipv6.options import IANAOption, StatusCodeOption, STATUS_NOADDRSAVAIL

        # Make a list of requested IAIDs
        request_iaids = [option.iaid for option in bundle.request.options if isinstance(option, IANAOption)]
        response_iaids = [option.iaid for option in bundle.response.options if isinstance(option, IANAOption)]

        request_iaids.sort()
        response_iaids.sort()

        if request_iaids != response_iaids:
            # Construct the list of missing IAIDs by starting with requested ones and removing ones in response
            missing_iaids = request_iaids[:]
            for iaid in response_iaids:
                if iaid in missing_iaids:
                    missing_iaids.remove(iaid)

            for iaid in missing_iaids:
                # Add what's missing
                bundle.response.options.append(IANAOption(iaid))

        # Now search for IANAOptions that don't have any options and at least give them a status
        for option in bundle.response.options:
            if not isinstance(option, IANAOption):
                continue

            if not option.options:
                option.options.append(StatusCodeOption(STATUS_NOADDRSAVAIL, "No addresses available"))


class UnansweredIATAOptionHandler(OptionHandler):
    """
    A handler that checks that all IATOptions in the request have an answer
    """

    # noinspection PyDocstring
    def post(self, bundle: TransactionBundle):
        from dhcp.ipv6.options import IATAOption, StatusCodeOption, STATUS_NOADDRSAVAIL

        # Make a list of requested IAIDs
        request_iaids = [option.iaid for option in bundle.request.options if isinstance(option, IATAOption)]
        response_iaids = [option.iaid for option in bundle.response.options if isinstance(option, IATAOption)]

        request_iaids.sort()
        response_iaids.sort()

        if request_iaids != response_iaids:
            # Construct the list of missing IAIDs by starting with requested ones and removing ones in response
            missing_iaids = request_iaids[:]
            for iaid in response_iaids:
                if iaid in missing_iaids:
                    missing_iaids.remove(iaid)

            for iaid in missing_iaids:
                # Add what's missing
                bundle.response.options.append(IATAOption(iaid))

        # Now search for IANAOptions that don't have any options and at least give them a status
        for option in bundle.response.options:
            if not isinstance(option, IATAOption):
                continue

            if not option.options:
                option.options.append(StatusCodeOption(STATUS_NOADDRSAVAIL, "No addresses available"))
