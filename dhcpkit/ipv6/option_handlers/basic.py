"""
Option handlers for the basic :rfc:`3315` options
"""

import logging
from ipaddress import IPv6Address

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.exceptions import CannotRespondError
from dhcpkit.ipv6.messages import ConfirmMessage, ReleaseMessage, DeclineMessage
from dhcpkit.ipv6.option_handlers import CopyOptionHandler, OverwritingOptionHandler, SimpleOptionHandler, \
    OptionHandler
from dhcpkit.ipv6.options import ClientIdOption, ServerIdOption, PreferenceOption, ServerUnicastOption, \
    StatusCodeOption, STATUS_SUCCESS
from dhcpkit.ipv6.server.config_parser import ConfigError
from dhcpkit.ipv6.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


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

    :type option: ServerIdOption
    """

    option = None

    def __init__(self, duid: DUID):
        """
        Create a handler function based on the provided DUID

        :param duid: The DUID of this server
        """
        option = ServerIdOption(duid)
        option.validate()

        super().__init__(option, always_send=True)

    def pre(self, bundle: TransactionBundle):
        """
        Check if there is a ServerId in the request

        :param bundle: The transaction bundle
        """
        server_id = bundle.request.get_option_of_type(ServerIdOption)
        if server_id and server_id.duid != self.option.duid:
            # This message is not for this server
            raise CannotRespondError


class PreferenceOptionHandler(SimpleOptionHandler):
    """
    The handler for PreferenceOption which adds a preference option to appropriate responses
    """

    def __init__(self, preference: int):
        # This option remains constant, so create a singleton that can be re-used
        option = PreferenceOption(preference=preference)
        option.validate()

        super().__init__(option, always_send=True)

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        preference = section.get('preference')
        if preference is None:
            raise ConfigError('PreferenceOption needs preference')

        return cls(int(preference))


class ServerUnicastOptionHandler(SimpleOptionHandler):
    """
    The handler for inserting ServerUniCastOptions into responses
    """

    def __init__(self, address: IPv6Address):
        # This option remains constant, so create a singleton that can be re-used
        option = ServerUnicastOption(server_address=address)
        option.validate()

        super().__init__(option, always_send=True)

    @classmethod
    def from_config(cls, section: dict, option_handler_id: str = None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        address = section.get('server-address')
        if address is None:
            raise ConfigError('ServerUnicastOption needs server-address')

        address = IPv6Address(address)

        return cls(address)


class ConfirmStatusOptionHandler(OptionHandler):
    """
    The handler that makes sure that replies to confirm messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.ConfirmMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, ConfirmMessage):
            existing = bundle.response.get_option_of_type(StatusCodeOption)
            if not existing:
                bundle.response.options.append(
                    StatusCodeOption(STATUS_SUCCESS, "Assignments confirmed")
                )


class ReleaseStatusOptionHandler(OptionHandler):
    """
    The handler that makes sure that replies to release messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.ReleaseMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, ReleaseMessage):
            existing = bundle.response.get_option_of_type(StatusCodeOption)
            if not existing:
                bundle.response.options.append(
                    StatusCodeOption(STATUS_SUCCESS,
                                     "Thank you for releasing your resources")
                )


class DeclineStatusOptionHandler(OptionHandler):
    """
    The handler that makes sure that replies to decline messages have a status code. When we reach the end without any
    status code being set we assume success. Other option handlers set the status to something else if they cannot
    confirm their part.
    """

    def handle(self, bundle: TransactionBundle):
        """
        Update the status of the reply to :class:`.DeclineMessage`.

        :param bundle: The transaction bundle
        """
        if isinstance(bundle.request, DeclineMessage):
            existing = bundle.response.get_option_of_type(StatusCodeOption)
            if not existing:
                bundle.response.options.append(
                    StatusCodeOption(STATUS_SUCCESS,
                                     "Our apologies for assigning you unusable addresses")
                )
