"""
Classes that handle the processing of an option
"""
import configparser
from ipaddress import IPv6Address

from dhcp.ipv6 import option_handler_registry
from dhcp.ipv6.duids import DUID
from dhcp.ipv6.exceptions import CannotReplyError
from dhcp.ipv6.message_handlers.transaction_bundle import TransactionBundle
from dhcp.ipv6.options import ClientIdOption, ServerIdOption, PreferenceOption, ServerUnicastOption


class OptionHandler:
    """
    Base class for option handlers
    """

    @classmethod
    def from_config(cls, section: configparser.SectionProxy) -> object:
        """
        Create a handler of this class based on the configuration in the config section. No default implementation
        is provided. Subclasses should implement their own if they want to be loaded from a configuration file.

        :param section: The configuration section
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
        # Make sure this option can go into this type of response
        if not bundle.response.may_contain(self.option):
            return

        # Check what the client requested
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
        # Make sure this option can go into this type of response
        if not bundle.response.may_contain(self.option_class):
            return

        # Check what the client requested
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


class ClientIdOptionHandler(CopyOptionHandler):
    """
    The handler for ClientIdOptions
    """

    def __init__(self):
        super().__init__(ClientIdOption, always_send=True)


class ServerIdOptionHandler(OverwritingOptionHandler):
    """
    The handler for ServerIdOption. Checks whether any server-id in the request matches our own and puts our server-id
    in the response message to let the client know who is answering.
    """

    def __init__(self, duid: DUID):
        """
        Create a handler function based on the provided DUID

        :param duid: The DUID of this server
        :returns: A handler that verifies this DUID in the request and inserts it in the reply
        """
        option = ServerIdOption(duid)
        option.validate()

        super().__init__(option, always_send=True)

    # noinspection PyDocstring
    def pre(self, bundle: TransactionBundle):
        # Check if there is a ServerId in the request
        server_id = bundle.request.get_option_of_type(ServerIdOption)
        if server_id and server_id.duid != self.option.duid:
            # This message is not for this server
            raise CannotReplyError


class PreferenceOptionHandler(SimpleOptionHandler):
    """
    The handler for PreferenceOption which adds a preference option to appropriate responses
    """

    def __init__(self, preference: int):
        # This option remains constant, so create a singleton that can be re-used
        option = PreferenceOption(preference=preference)
        option.validate()

        super().__init__(option, always_send=True)

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy) -> OptionHandler:
        preference = section.getint('preference')
        if preference is None:
            raise configparser.NoOptionError('preference', section.name)

        return cls(preference)


class ServerUnicastOptionHandler(SimpleOptionHandler):
    """
    The handler for inserting ServerUniCastOptions into responses
    """

    def __init__(self, address: IPv6Address):
        # This option remains constant, so create a singleton that can be re-used
        option = ServerUnicastOption(server_address=address)
        option.validate()

        super().__init__(option, always_send=True)

    # noinspection PyDocstring
    @classmethod
    def from_config(cls, section: configparser.SectionProxy) -> OptionHandler:
        address = section.get('server-address')
        if address is None:
            raise configparser.NoOptionError('server-address', section.name)

        address = IPv6Address(address)

        return cls(address)


option_handler_registry.register(UnansweredIANAOptionHandler)
option_handler_registry.register(UnansweredIATAOptionHandler)
option_handler_registry.register(ClientIdOptionHandler)
option_handler_registry.register(ServerIdOptionHandler)
option_handler_registry.register(PreferenceOptionHandler)
option_handler_registry.register(ServerUnicastOptionHandler)
