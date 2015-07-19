from abc import abstractmethod
import configparser
import logging
import math

from dhcp.ipv6 import option_registry
from dhcp.ipv6.handlers.base import BaseHandler
from dhcp.ipv6.messages import ClientServerMessage, ReplyMessage, AdvertiseMessage
from dhcp.ipv6.options import OptionRequestOption, ServerIdOption, ClientIdOption, IANAOption, IATAOption, \
    RapidCommitOption, IAAddressOption, StatusCodeOption, STATUS_NOADDRSAVAIL
from ipv6 import INFINITY
from ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from ipv6.handlers.base import TransactionBundle
from ipv6.messages import RenewMessage, RebindMessage

logger = logging.getLogger(__name__)


class StandardHandler(BaseHandler):
    """
    This is the base class for standard handlers. It implements the standard handling of the DHCP protocol. Subclasses
    only need to provide the right addresses and options.
    """

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_non_temporary_addresses(self, bundle: TransactionBundle) -> list:
        """
        Which IA-NA addresses to give to this client?

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: A list of IAAddressOptions
        """
        return []

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_temporary_addresses(self, bundle: TransactionBundle) -> list:
        """
        Which IA-TA addresses to give to this client?

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: A list of IAAddressOptions
        """
        return []

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_delegated_prefixes(self, bundle: TransactionBundle) -> list:
        """
        Which IA-PD prefixes to give to this client?

        :param bundle: The transaction bundle that carries all data about this transaction
        :returns: A list of IAPrefixOptions
        """
        return []

    # noinspection PyUnusedLocal
    @abstractmethod
    def get_options(self, bundle: TransactionBundle) -> list:
        """
        Which options to give to this client? The provided list might be filtered if the client provided an
        OptionRequestOption.

        :param bundle: The transaction bundle that carries all data about this transaction
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
    def set_t1_t2_status(option):
        """
        Utility method to set T1 and T2 of IANAOption/IAPDOption based on the lifetimes of its addresses

        :param option:
        """
        if option.options:
            # Set T1 and T2 based on the addresses' prefixes' lifetimes
            shortest_preferred = min([INFINITY] + [option.preferred_lifetime
                                                   for option in option.options
                                                   if isinstance(option, (IAAddressOption, IAPrefixOption))])

            if shortest_preferred == INFINITY:
                # If the "shortest" preferred lifetime is 0xffffffff ("infinity"), the recommended T1 and T2 values
                # are also 0xffffffff.
                option.t1 = INFINITY
                option.t2 = INFINITY
            else:
                # Recommended values for T1 and T2 are .5 and .8 times the shortest preferred lifetime of the
                # addresses in the IA that the server is willing to extend, respectively.
                option.t1 = math.floor(shortest_preferred * 0.5)
                option.t2 = math.floor(shortest_preferred * 0.8)
        else:
            # Set a status if we didn't provide any addresses
            option.options.append(
                StatusCodeOption(
                    STATUS_NOADDRSAVAIL,
                    "We have no (more) {} to give to you".format(isinstance(option, IAPDOption)
                                                                 and 'prefixes' or 'addresses')
                )
            )

    def construct_ia_na_options(self, bundle: TransactionBundle) -> list:
        """
        Construct a list of IANAOptions based on what the client requested and what get_non_temporary_addresses
        provides.

        :param bundle: The transaction bundle that carries all data about this transaction
        :return: The list of IANAOptions to respond with
        """

        # Assigned addresses
        assigned_addresses = self.get_non_temporary_addresses(bundle)

        # We have to respond with one IANAOption for each IANAOption sent by the client
        response_options = []
        for requested_option in bundle.request.get_options_of_type(IANAOption):
            response_option = IANAOption(iaid=requested_option.iaid)

            # Process any requested addresses
            for requested_address in requested_option.options:
                if not isinstance(requested_address, IAAddressOption):
                    continue

                gave_assigned = False
                for i in range(len(assigned_addresses)):
                    assigned_address = assigned_addresses[i]
                    if requested_address.address == assigned_address.address:
                        # This address was asked for: give it
                        response_option.options.append(assigned_address)
                        gave_assigned = True

                        # Deleting on index is safe because we break the loop anyway
                        del assigned_addresses[i]
                        break

                respond_zero = isinstance(bundle.request, (RenewMessage, RebindMessage))
                if not gave_assigned and respond_zero:
                    # Tell the client to stop using this address
                    response_option.options.append(IAAddressOption(address=requested_address.address,
                                                                   preferred_lifetime=0, valid_lifetime=0))

            response_options.append(response_option)

        # If there are addresses left add them to the first option if there is one
        if response_options:
            response_options[0].extend(assigned_addresses)

        # Post-processing: set T1/T2 or add a status option
        for response_option in response_options:
            self.set_t1_t2_status(response_option)

        return response_options

    def construct_ia_ta_options(self, bundle: TransactionBundle) -> list:
        """
        Construct a list of IATAOptions based on what the client requested and what get_temporary_addresses
        provides.

        :param bundle: The transaction bundle that carries all data about this transaction
        :return: The list of IATAOptions to respond with
        """

        # Assigned addresses
        assigned_addresses = self.get_temporary_addresses(bundle)

        # We have to respond with one IATAOption for each IATAOption sent by the client
        response_options = []
        for requested_option in bundle.request.get_options_of_type(IANAOption):
            response_option = IATAOption(iaid=requested_option.iaid)

            # Process any requested addresses
            for requested_address in requested_option.options:
                if not isinstance(requested_address, IAAddressOption):
                    continue

                gave_assigned = False
                for i in range(len(assigned_addresses)):
                    assigned_address = assigned_addresses[i]
                    if requested_address.address == assigned_address.address:
                        # This address was asked for: give it
                        response_option.options.append(assigned_address)
                        gave_assigned = True

                        # Deleting on index is safe because we break the loop anyway
                        del assigned_addresses[i]
                        break

                respond_zero = isinstance(bundle.request, (RenewMessage, RebindMessage))
                if not gave_assigned and respond_zero:
                    # Tell the client to stop using this address
                    response_option.options.append(IAAddressOption(address=requested_address.address,
                                                                   preferred_lifetime=0, valid_lifetime=0))

            response_options.append(response_option)

        # If there are addresses left add them to the first option if there is one
        if response_options:
            response_options[0].extend(assigned_addresses)

        # Post-processing: add a status option is necessary
        for response_option in response_options:
            # Set a status if we didn't provide any addresses
            if not response_option.options:
                response_option.options.append(StatusCodeOption(STATUS_NOADDRSAVAIL,
                                                                "We have no (more) temporary addresses to give to you"))

        return response_options

    def construct_ia_pd_options(self, bundle: TransactionBundle) -> list:
        """
        Construct a list of IAPDOptions based on what the client requested and what get_delegated_prefixes provides.

        :param bundle: The transaction bundle that carries all data about this transaction
        :return: The list of IAPDOptions to respond with
        """

        # Assigned prefixes
        assigned_prefixes = self.get_delegated_prefixes(bundle)

        # We have to respond with one IAPDOption for each IAPDOption sent by the client
        response_options = []
        for requested_option in bundle.request.get_options_of_type(IAPDOption):
            response_option = IAPDOption(iaid=requested_option.iaid)

            # Process any requested addresses
            for requested_prefix in requested_option.options:
                if not isinstance(requested_prefix, IAPrefixOption):
                    continue

                gave_assigned = False
                for i in range(len(assigned_prefixes)):
                    assigned_prefix = assigned_prefixes[i]
                    if requested_prefix.prefix == assigned_prefix.prefix:
                        # This address was asked for: give it
                        response_option.options.append(assigned_prefix)
                        gave_assigned = True

                        # Deleting on index is safe because we break the loop anyway
                        del assigned_prefixes[i]
                        break

                respond_zero = isinstance(bundle.request, (RenewMessage, RebindMessage))
                if not gave_assigned and respond_zero:
                    # Tell the client to stop using this address
                    response_option.options.append(IAPrefixOption(prefix=requested_prefix.prefix,
                                                                  preferred_lifetime=0, valid_lifetime=0))

            response_options.append(response_option)

        # If there are addresses left add them to the first option if there is one
        if response_options:
            response_options[0].extend(assigned_prefixes)

        # Post-processing: set T1/T2 or add a status option
        for response_option in response_options:
            self.set_t1_t2_status(response_option)

        return response_options

    def commit_assignments(self, bundle: TransactionBundle):
        """
        Make sure we store which client uses which addresses, if necessary.
        """
        for option in bundle.response.options:
            if isinstance(option, (IANAOption, IATAOption, IAPDOption)):
                self.commit_ia_na_assignment(bundle, option)

            if isinstance(option, (IANAOption, IATAOption, IAPDOption)):
                self.commit_ia_ta_assignment(bundle, option)

            if isinstance(option, (IANAOption, IATAOption, IAPDOption)):
                self.commit_ia_pd_assignment(bundle, option)

    # noinspection PyMethodMayBeStatic
    def commit_ia_na_assignment(self, request: ClientServerMessage, relay_messages: list, option: IANAOption):
        """
        Make sure we store which client uses which addresses, if necessary. Subclasses overwrite this if/when they
        want to know that an IANA will be sent in a reply to the client giving it these addresses.

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param option: The IANAOption
        """
        pass

    # noinspection PyMethodMayBeStatic
    def commit_ia_ta_assignment(self, request: ClientServerMessage, relay_messages: list, option: IATAOption):
        """
        Make sure we store which client uses which addresses, if necessary. Subclasses overwrite this if/when they
        want to know that an IANA will be sent in a reply to the client giving it these addresses.

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param option: The IANAOption
        """
        pass

    # noinspection PyMethodMayBeStatic
    def commit_ia_pd_assignment(self, request: ClientServerMessage, relay_messages: list, option: IAPDOption):
        """
        Make sure we store which client uses which addresses, if necessary. Subclasses overwrite this if/when they
        want to know that an IANA will be sent in a reply to the client giving it these addresses.

        :param request: The incoming ClientServerMessage
        :param relay_messages: The list of RelayServerMessages, relay closest to the client first
        :param option: The IANAOption
        """
        pass

    # noinspection PyDocstring
    def handle_solicit_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        # Start building the response
        if self.allow_rapid_commit and bundle.request.get_option_of_type(RapidCommitOption) is not None:
            response = ReplyMessage(bundle.request.transaction_id)
        else:
            response = AdvertiseMessage(bundle.request.transaction_id)

        # ServerIdOption is a special case, so we handle it here
        response.options.append(ServerIdOption(duid=self.server_duid))

        # The options we are going to return
        response_options = [
            ServerIdOption(duid=self.server_duid),
            bundle.request.get_option_of_type(ClientIdOption),
        ]

        # Add built-in options filtered on the client's ORO (if any)
        response_options.extend(self.filter_options_on_oro(
            options=self.get_options(bundle),
            oro=bundle.request.get_option_of_type(OptionRequestOption)
        ))

        # Reply to IA_NA/IA_TA/IA_PD
        response_options.extend(self.construct_ia_na_options(bundle))
        response_options.extend(self.construct_ia_ta_options(bundle))
        response_options.extend(self.construct_ia_pd_options(bundle))

        # Return response
        if self.allow_rapid_commit and bundle.request.get_option_of_type(RapidCommitOption) is not None:
            self.commit_assignments(request, relay_messages, response_options)
            return ReplyMessage(request.transaction_id, response_options)
        else:
            return AdvertiseMessage(request.transaction_id, response_options)

    # noinspection PyDocstring
    def handle_request_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass

    # noinspection PyDocstring
    def handle_confirm_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass

    # noinspection PyDocstring
    def handle_renew_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass

    # noinspection PyDocstring
    def handle_rebind_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass

    # noinspection PyDocstring
    def handle_release_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass

    # noinspection PyDocstring
    def handle_decline_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass

    # noinspection PyDocstring
    def handle_information_request_message(self, bundle: TransactionBundle) -> ClientServerMessage:
        pass
