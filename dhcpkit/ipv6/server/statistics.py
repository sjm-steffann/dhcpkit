"""
Statistics about the server in shared memory
"""
from collections import OrderedDict
from ctypes import c_uint64
from multiprocessing import Value
from multiprocessing.sharedctypes import Synchronized

from dhcpkit.ipv6.message_registry import message_registry
from dhcpkit.ipv6.messages import ClientServerMessage
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.utils import camelcase_to_underscore
from typing import Dict, Hashable, Iterable, List


def create_update_method(counter_name):
    """
    Create a counting method for a simple counter on the Statistics class

    :param counter_name: The name of the counter to update
    :return: The generated method
    """

    def count_method(self):
        """
        Call the counting method on all statistics objects
        """
        counter = getattr(self, counter_name)
        with counter.get_lock():
            counter.value += 1

    return count_method


def create_update_dict_method(counter_name):
    """
    Create a counting method for a counter in a dictionary on the Statistics class

    :param counter_name: The name of the counter to update
    :return: The generated method
    """

    def count_method(self, key):
        """
        Update the counter for the given key
        """
        counter_dict = getattr(self, counter_name)
        if key in counter_dict:
            counter = counter_dict[key]
            with counter.get_lock():
                counter.value += 1

    return count_method


def create_count_method(method_name: str):
    """
    Create a counting method for the StatisticsSet class

    :param method_name: The name of the method to call on Statistics objects
    :return: The generated method
    """

    def count_method(self):
        """
        Call the counting method on all statistics objects
        """
        for stats in self.statistics_set:
            method = getattr(stats, method_name)
            method()

    return count_method


def create_count_dict_method(method_name: str):
    """
    Create a counting method for the StatisticsSet class

    :param method_name: The name of the method to call on Statistics objects
    :return: The generated method
    """

    def count_method(self, key):
        """
        Call the counting method on all statistics objects
        """
        for stats in self.statistics_set:
            method = getattr(stats, method_name)
            method(key)

    return count_method


class Statistics:
    """
    A set of statistics about DHCPv6

    :type incoming_packets: Synchronized
    :type outgoing_packets: Synchronized

    :type unparsable_packets: Synchronized
    :type handling_errors: Synchronized

    :type for_other_server: Synchronized
    :type do_not_respond: Synchronized
    :type use_multicast: Synchronized
    :type unknown_query_type: Synchronized
    :type malformed_query: Synchronized
    :type not_allowed: Synchronized
    :type other_error: Synchronized

    :type messages_in: Dict[int, Synchronized]
    :type messages_out: Dict[int, Synchronized]
    """

    def __init__(self):
        # Packet counts
        self.incoming_packets = Value(c_uint64)
        self.outgoing_packets = Value(c_uint64)

        # Errors
        self.unparsable_packets = Value(c_uint64)
        self.handling_errors = Value(c_uint64)

        # Special replies
        self.for_other_server = Value(c_uint64)
        self.do_not_respond = Value(c_uint64)
        self.use_multicast = Value(c_uint64)
        self.unknown_query_type = Value(c_uint64)
        self.malformed_query = Value(c_uint64)
        self.not_allowed = Value(c_uint64)
        self.other_error = Value(c_uint64)

        # Counters per message type
        self.messages_in = OrderedDict()
        self.messages_out = OrderedDict()

        # Which message types do we know about?
        message_registry_keys = list(message_registry.keys())
        message_registry_keys.sort()

        for key in message_registry_keys:
            message_class = message_registry[key]
            if message_class.from_client_to_server and issubclass(message_class, ClientServerMessage):
                self.messages_in[message_class.message_type] = Value(c_uint64)

            if message_class.from_server_to_client and issubclass(message_class, ClientServerMessage):
                self.messages_out[message_class.message_type] = Value(c_uint64)

    def __str__(self):
        lines = [
            "Packets",
            "- Incoming packets: {}".format(self.incoming_packets.value),
            "- Outgoing packets: {}".format(self.outgoing_packets.value),
            "Errors",
            "- Unparsable packets: {}".format(self.unparsable_packets.value),
            "- Handling errors: {}".format(self.handling_errors.value),
            "Special replies",
            "- For other server: {}".format(self.for_other_server.value),
            "- Do not respond: {}".format(self.do_not_respond.value),
            "- Use multicast: {}".format(self.use_multicast.value),
            "- Unknown query type: {}".format(self.unknown_query_type.value),
            "- Malformed query: {}".format(self.malformed_query.value),
            "- Not allowed: {}".format(self.not_allowed.value),
            "- Other error: {}".format(self.other_error.value),
            "Incoming messages",
        ]

        for message_type, counter in self.messages_in.items():
            message_type_name = message_registry[message_type].__name__
            if message_type_name.endswith('Message'):
                message_type_name = message_type_name[:-7]
            lines += ['- {}: {}'.format(message_type_name, counter.value)]

        lines += ['Outgoing messages']

        for message_type, counter in self.messages_out.items():
            message_type_name = message_registry[message_type].__name__
            if message_type_name.endswith('Message'):
                message_type_name = message_type_name[:-7]
            lines += ['- {}: {}'.format(message_type_name, counter.value)]

        return '\n'.join(lines)

    def export(self) -> Dict[str, int]:
        """
        Export the counters

        :return: The counters in a processable format
        """
        out = OrderedDict()
        out['incoming_packets'] = self.incoming_packets.value
        out['outgoing_packets'] = self.outgoing_packets.value
        out['unparsable_packets'] = self.unparsable_packets.value
        out['handling_errors'] = self.handling_errors.value
        out['for_other_server'] = self.for_other_server.value
        out['do_not_respond'] = self.do_not_respond.value
        out['use_multicast'] = self.use_multicast.value
        out['unknown_query_type'] = self.unknown_query_type.value
        out['malformed_query'] = self.malformed_query.value
        out['not_allowed'] = self.not_allowed.value
        out['other_error'] = self.other_error.value

        out['messages_in'] = OrderedDict()
        for message_type, counter in self.messages_in.items():
            message_type_name = message_registry[message_type].__name__
            message_type_name = camelcase_to_underscore(message_type_name)
            if message_type_name.endswith('_message'):
                message_type_name = message_type_name[:-8]
            out['messages_in'][message_type_name] = counter.value

        out['messages_out'] = OrderedDict()
        for message_type, counter in self.messages_out.items():
            message_type_name = message_registry[message_type].__name__
            message_type_name = camelcase_to_underscore(message_type_name)
            if message_type_name.endswith('_message'):
                message_type_name = message_type_name[:-8]
            out['messages_out'][message_type_name] = counter.value

        return out

    count_incoming_packet = create_update_method('incoming_packets')
    count_outgoing_packet = create_update_method('outgoing_packets')
    count_unparsable_packet = create_update_method('unparsable_packets')
    count_handling_error = create_update_method('handling_errors')
    count_for_other_server = create_update_method('for_other_server')
    count_do_not_respond = create_update_method('do_not_respond')
    count_use_multicast = create_update_method('use_multicast')
    count_unknown_query_type = create_update_method('unknown_query_type')
    count_malformed_query = create_update_method('malformed_query')
    count_not_allowed = create_update_method('not_allowed')
    count_other_error = create_update_method('other_error')
    count_message_in = create_update_dict_method('messages_in')
    count_message_out = create_update_dict_method('messages_out')


class StatisticsSet:
    """
    A set of statistics objects that are updated together. The metaclass will create all methods for us.
    """

    def __init__(self, statistics_set: Iterable[Statistics] = None):
        self.statistics_set = set(statistics_set or [])

    count_incoming_packet = create_count_method('count_incoming_packet')
    count_outgoing_packet = create_count_method('count_outgoing_packet')
    count_unparsable_packet = create_count_method('count_unparsable_packet')
    count_handling_error = create_count_method('count_handling_error')
    count_for_other_server = create_count_method('count_for_other_server')
    count_do_not_respond = create_count_method('count_do_not_respond')
    count_use_multicast = create_count_method('count_use_multicast')
    count_unknown_query_type = create_count_method('count_unknown_query_type')
    count_malformed_query = create_count_method('count_malformed_query')
    count_not_allowed = create_count_method('count_not_allowed')
    count_other_error = create_count_method('count_other_error')
    count_message_in = create_count_dict_method('count_message_in')
    count_message_out = create_count_dict_method('count_message_out')


class ServerStatistics:
    """
    A set of statistics about the DHCPv6 server

    :type global_stats: Statistics
    :type interface_stats: Dict[str, Statistics]
    :type subnet_stats: Dict[IPv6Network, Statistics]
    :type relay_stats: Dict[IPv6Address, Statistics]
    """

    def __init__(self):
        self.global_stats = Statistics()

        # On-demand categories
        self.interface_stats = {}
        self.subnet_stats = {}
        self.relay_stats = {}

    def set_categories(self, category_settings):
        """
        Create space for the given interfaces

        :param category_settings: Configuration setting for categories
        """
        if not category_settings:
            return

        def update_categories(container: Dict[Hashable, Statistics], categories: Iterable[Hashable]):
            """
            Update a category dictionary based on the provided list of wanted categories

            :param container: The container to update
            :param categories: The list of wanted categories
            """
            # Keep track of existing categories that we don't want anymore
            remaining = set(container.keys())

            # Create categories
            for key in categories:
                if key not in container:
                    container[key] = Statistics()

                    if key in remaining:
                        remaining.remove(key)

            # Remove unwanted categories
            for key in remaining:
                del container[key]

        update_categories(self.interface_stats, category_settings.interfaces)
        update_categories(self.subnet_stats, category_settings.subnets)
        update_categories(self.relay_stats, category_settings.relays)

    def get_update_set(self, interface_name: str = None, bundle: TransactionBundle = None) -> StatisticsSet:
        """
        Return all statistics objects that need to be updated.

        :param interface_name: The name of the interface that we received the packet on
        :param bundle: The transaction bundle to base the selection on
        :return: The set to call count methods on
        """
        stats_set = [self.global_stats]

        if interface_name and interface_name in self.interface_stats:
            stats_set.append(self.interface_stats[interface_name])

        if bundle:
            link_address = bundle.link_address
            for subnet, stats in self.subnet_stats.items():
                if link_address in subnet:
                    stats_set.append(stats)

            relays = bundle.relays
            for address, stats in self.relay_stats.items():
                if address in relays:
                    stats_set.append(stats)

        return StatisticsSet(stats_set)

    def __str__(self):
        lines = ['Global']
        lines += [('- ' if not line.startswith('- ') else '  ') + line
                  for line in str(self.global_stats).split('\n')]

        def get_category_lines(type_name: str, category_data: Dict[Hashable, Statistics]) -> List[str]:
            """
            Get lines for a category

            :param type_name: A descriptive type name for the categories
            :param category_data: A dictionary for categories
            :return: The lines for the provided category
            """
            sub_lines = []

            keys = list(category_data.keys())
            keys.sort()

            for name in keys:
                sub_lines += ['', '{} {}'.format(type_name, name)]
                sub_lines += [('- ' if not line.startswith('- ') else '  ') + line
                              for line in str(category_data[name]).split('\n')]

            return sub_lines

        lines += get_category_lines('Interface', self.interface_stats)
        lines += get_category_lines('Subnet', self.subnet_stats)
        lines += get_category_lines('Relay', self.relay_stats)

        return '\n'.join(lines)

    def export(self) -> Dict[str, int]:
        """
        Export the counters

        :return: The counters in a processable format
        """
        out = OrderedDict()
        out['global'] = self.global_stats.export()

        def get_category_data(category_data: Dict[Hashable, Statistics]) -> Dict[str, dict]:
            """
            Get data for a category

            :param category_data: A dictionary for categories
            :return: The data for the provided categories
            """
            data = OrderedDict()

            keys = list(category_data.keys())
            keys.sort()

            for name in keys:
                data[str(name)] = category_data[name].export()

            return data

        out['interfaces'] = get_category_data(self.interface_stats)
        out['subnets'] = get_category_data(self.subnet_stats)
        out['relays'] = get_category_data(self.relay_stats)

        return out
