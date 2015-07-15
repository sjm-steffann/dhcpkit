from abc import abstractmethod
import configparser
import logging

from dhcp.ipv6 import option_registry
from dhcp.ipv6.handlers.base import BaseHandler
from dhcp.ipv6.messages import Message, ClientServerMessage
from dhcp.ipv6.options import OptionRequestOption

logger = logging.getLogger(__name__)


class StandardHandler(BaseHandler):
    """
    This is the base class for standard handlers. It implements the standard handling of the DHCP protocol. Subclasses
    only need to provide the right addresses and options.
    """

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_non_temporary_addresses(self, request: ClientServerMessage, relay_messages: list) -> list:
        """
        Which IA-NA addresses to give to this client?

        :param request: The parsed incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :returns: A list of IAAddressOptions
        """
        return []

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_temporary_addresses(self, request: ClientServerMessage, relay_messages: list) -> list:
        """
        Which IA-TA addresses to give to this client?

        :param request: The parsed incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :returns: A list of IAAddressOptions
        """
        return []

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_delegated_prefixes(self, request: ClientServerMessage, relay_messages: list) -> list:
        """
        Which IA-PD prefixes to give to this client?

        :param request: The parsed incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :returns: A list of IAPrefixOptions
        """
        return []

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_options(self, request: ClientServerMessage, relay_messages: list) -> list:
        """
        Which options to give to this client? The provided list might be filtered if the client provided an
        OptionRequestOption.

        :param request: The parsed incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :returns: A list of Options
        """
        return []

    def get_options_from_config(self):
        """
        Look in the config for sections named [option xyz] where xyz is the name of a DHCP option. Create option
        objects from the data in those sections.

        :return: [Option]
        """
        section_names = [section_name.split(' ')[1]
                         for section_name in self.config.sections()
                         if section_name.split(' ')[0] == 'option']

        options = []
        for option_name in section_names:
            option_class = option_registry.name_registry.get(option_name)
            if not option_class:
                raise configparser.ParsingError("Unknown option: {}".format(option_name))

            section_name = 'option {}'.format(option_name)
            option = option_class.from_config_section(self.config[section_name])
            options.append(option)

        return options

    @staticmethod
    def filter_options_on_oro(options: list, oro: OptionRequestOption):
        """
        Only return the options that the client requested

        :param options: The list of options
        :param oro: The OptionRequestOption to use as a filter
        :return: The filtered list of options
        """
        if not oro:
            return options

        return [option for option in options if option.option_type in oro.requested_options]

    def handle_solicit_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle SolicitMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_request_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle RequestMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_confirm_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle ConfirmMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_renew_message(self, request: ClientServerMessage, relay_messages: list,
                             sender: tuple, receiver: tuple) -> Message:
        """
        Handle RenewMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_rebind_message(self, request: ClientServerMessage, relay_messages: list,
                              sender: tuple, receiver: tuple) -> Message:
        """
        Handle RebindMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_release_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle ReleaseMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_decline_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> Message:
        """
        Handle DeclineMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """

    def handle_information_request_message(self, request: ClientServerMessage, relay_messages: list,
                                           sender: tuple, receiver: tuple) -> Message:
        """
        Handle InformationRequestMessages

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param sender: The address of the sender
        :param receiver: The address that the request was received on
        :returns: The message to reply with
        """


        # def construct_answer(self, request: ClientServerMessage, relay_messages: list, send_reply: bool) -> None or Message:
        #     # The options we are going to return
        #     response_options = [
        #         ServerIdOption(duid=self.server_duid),
        #         request.get_option_of_type(ClientIdOption),
        #     ]
        #
        #     # Add built-in options filtered on the client's ORO (if any)
        #     response_options.extend(self.filter_options_on_oro(
        #         options=self.get_options(request, relay_messages),
        #         oro=request.get_option_of_type(OptionRequestOption)
        #     ))
        #
        #     # We always give fixed answers so get the addresses
        #     address, prefix = self.get_addresses_for_interface_id(relay_messages)
        #
        #     # Reply to IA_NA
        #     first = True
        #     for option in request.get_options_of_type(IANAOption):
        #         if first and address:
        #             # Give the client the address
        #             response_options.append(IANAOption(option.iaid, options=[
        #                 IAAddressOption(address=address, preferred_lifetime=7200, valid_lifetime=7500)
        #             ]))
        #         else:
        #             # We don't hand out multiple addresses
        #             response_options.append(IANAOption(option.iaid, options=[
        #                 StatusCodeOption(STATUS_NOADDRSAVAIL)
        #             ]))
        #
        #         first = False
        #
        #     # Reply to IA_PD
        #     first = True
        #     for option in request.get_options_of_type(IAPDOption):
        #         if first and address:
        #             # Give the client the address
        #             response_options.append(IAPDOption(option.iaid, options=[
        #                 IAPrefixOption(prefix=prefix, preferred_lifetime=7200, valid_lifetime=7500)
        #             ]))
        #         else:
        #             # We don't hand out multiple addresses
        #             response_options.append(IAPDOption(option.iaid, options=[
        #                 StatusCodeOption(STATUS_NOADDRSAVAIL, status_message='')
        #             ]))
        #
        #         first = False
        #
        #     # Return response
        #     if send_reply:
        #         return ReplyMessage(request.transaction_id, response_options)
        #     else:
        #         return AdvertiseMessage(request.transaction_id, response_options)
