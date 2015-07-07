import configparser
import csv
from ipaddress import IPv6Network, IPv6Address
import logging
import os

from dhcp.ipv6 import extensions
from dhcp.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import Message, ClientServerMessage, ReplyMessage, AdvertiseMessage
from dhcp.ipv6.options import InterfaceIdOption, RapidCommitOption, IANAOption, IAAddressOption, StatusCodeOption, \
    STATUS_NOADDRSAVAIL, ServerIdOption, ClientIdOption, OptionRequestOption
from dhcp.rwlock import RWLock

logger = logging.getLogger(__name__)

# Load all extensions so we can handle them
extensions.load_all()


class InterfaceIdPrefixDelegationHandler(Handler):
    def __init__(self, config: configparser.ConfigParser):
        super().__init__(config)
        self.assignments = {}  # type: {bytes: (IPv6Address, IPv6Network)}
        self.options = {}  # type: {int: Option}
        self._lock = RWLock()
        self.read_csv()
        self.create_options()

    def reload(self):
        self.read_csv()

    def read_csv(self):
        """
        Read the assignemnts from the file specified in the configuration
        :return:
        """
        csv_rel_filename = self.config.get('handler', 'assignments-file')

        # Find the CSV file
        if os.path.isabs(csv_rel_filename):
            csv_filename = csv_rel_filename
        else:
            config_filename = self.config['config']['filename']
            config_dir = os.path.dirname(config_filename)
            csv_filename = os.path.realpath(os.path.join(config_dir, csv_rel_filename))

        # Get the write lock before we update the assignments
        with self._lock.write_lock():
            if self.assignments:
                logger.debug("Reloading assignments from {}".format(csv_filename))
            else:
                logger.debug("Loading assignments from {}".format(csv_filename))

            self.assignments = {}
            with open(csv_filename) as csv_file:
                reader = csv.DictReader(csv_file)

                # First line is column headings
                line = 1
                for row in reader:
                    line += 1
                    try:
                        self.assignments[row['interface-id'].encode('utf8')] = (IPv6Address(row['address']),
                                                                                IPv6Network(row['prefix']))
                    except KeyError:
                        raise configparser.Error("Assignment CSV must have columns "
                                                 "'interface-id', 'address' and 'prefix'")
                    except ValueError as e:
                        logger.error("Ignoring line {} with invalid value: {}".format(line, e))

        logger.info("Loaded {} assignments from CSV".format(len(self.assignments)))

    def find_clostest_interface_id(self, relay_messages: list) -> bytes or None:
        """
        Find the interface id option in the first (closest to the client) relay message

        :param relay_messages: The chain of relay messages
        :return: The interface id
        """
        if not relay_messages:
            # No relay message -> no interface
            return None

        # Return the interface is from the first relay, which is the one closest to the client
        for option in relay_messages[-1].options:
            if isinstance(option, InterfaceIdOption):
                return option.interface_id

        # Nothing found
        return None

    def get_addresses_for_interface_id(self, relay_messages: list) -> (IPv6Address or None, IPv6Network or None):
        """
        Determine the interface id and look up the assignment for it

        :param relay_messages: The chain of relay messages
        :return: IANA address and IAPD prefix
        """
        interface_id = self.find_clostest_interface_id(relay_messages)
        if not interface_id:
            logger.warning("Received a request without a relay interface id: cannot assign addresses")
            return None, None

        # Get the read lock
        with self._lock.read_lock():
            result = self.assignments.get(interface_id)
            if result:
                return result
            else:
                logger.warning("Received a request with unknown relay interface id {}: "
                               "cannot assign addresses".format(interface_id))
                return None, None

    def create_options(self):
        """
        Get a list of all the extra DHCP options we can return to the client

        :return: A dict mapping option id to option object
        """
        with self._lock.write_lock():
            self.options = self.get_options_from_config()

    def construct_answer(self, request: ClientServerMessage, relay_messages: list, send_reply: bool) -> None or Message:
        # The options we are going to return
        response_options = []
        response_options.append(ServerIdOption(duid=self.server_duid))
        response_options.append(request.get_option_of_type(ClientIdOption))

        # Add built-in options filtered on the client's ORO (if any)
        response_options.extend(self.filter_options_on_oro(
            options=self.get_options_from_config(),
            oro=request.get_option_of_type(OptionRequestOption)
        ))

        # We always give fixed answers so get the addresses
        address, prefix = self.get_addresses_for_interface_id(relay_messages)

        # Reply to IA_NA
        first = True
        for option in request.get_options_of_type(IANAOption):
            if first and address:
                # Give the client the address
                response_options.append(IANAOption(option.iaid, options=[
                    IAAddressOption(address=address, preferred_lifetime=7200, valid_lifetime=7500)
                ]))
            else:
                # We don't hand out multiple addresses
                response_options.append(IANAOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NOADDRSAVAIL)
                ]))

            first = False

        # Reply to IA_PD
        first = True
        for option in request.get_options_of_type(IAPDOption):
            if first and address:
                # Give the client the address
                response_options.append(IAPDOption(option.iaid, options=[
                    IAPrefixOption(prefix=prefix, preferred_lifetime=7200, valid_lifetime=7500)
                ]))
            else:
                # We don't hand out multiple addresses
                response_options.append(IAPDOption(option.iaid, options=[
                    StatusCodeOption(STATUS_NOADDRSAVAIL)
                ]))

            first = False

        # Return response
        if send_reply:
            return ReplyMessage(request.transaction_id, response_options)
        else:
            return AdvertiseMessage(request.transaction_id, response_options)

    # noinspection PyUnusedLocal
    def handle_solicit_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> None or Message or (Message, tuple):

        # Determine if we will answer immediately instead of advertising first
        send_reply = request.get_option_of_type(RapidCommitOption) is not None
        return self.construct_answer(request, relay_messages, send_reply)

    # noinspection PyUnusedLocal
    def handle_request_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> None or Message or (Message, tuple):

        return self.construct_answer(request, relay_messages, send_reply=True)


handler = InterfaceIdPrefixDelegationHandler
