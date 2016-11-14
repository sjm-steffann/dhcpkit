"""
Config processing for a handler to echo a LinkLayerIdOption back to the relay
"""

import logging

from ZConfig.datatypes import existing_dirpath
from dhcpkit.common.server.config_datatypes import unsigned_int_16
from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6.option_registry import option_registry
from dhcpkit.ipv6.server.extensions.leasequery import LeasequeryHandler
from dhcpkit.ipv6.server.extensions.leasequery.sqlite import LeasequerySqliteStore
from dhcpkit.ipv6.server.handlers import HandlerFactory

logger = logging.getLogger(__name__)


def sensitive_option_name(value: str) -> int:
    """
    If the argument is a number then check if it is a 16-bit unsigned integer and return it. Otherwise see if we have
    an option implementation with the given name, and return its option-type code.

    :param value: The name or number of a DHCPv6 option
    :return: The number of the option
    """
    try:
        return unsigned_int_16(value)
    except ValueError:
        try:
            # Not a valid number, try by name
            return option_registry.by_name[value].option_type
        except KeyError:
            raise ValueError("Option {} is not a valid DHCPv6 option".format(value))


class LeasequeryHandlerFactory(HandlerFactory):
    """
    Config processing for a handler to echo a LinkLayerIdOption back to the relay
    """

    def __init__(self, section):
        super().__init__(section)

    def create(self):
        """
        Create a leasequery handler.

        :return: A leasequery handler
        """
        return LeasequeryHandler(self.store(), self.allow_from, self.sensitive_options)


class LeasequerySqliteStoreFactory(ConfigElementFactory):
    """
    Factory for LeasequerySqliteStore
    """

    name_datatype = staticmethod(existing_dirpath)

    def __init__(self, section):
        super().__init__(section)

    def create(self):
        """
        Create a leasequery store.

        :return: A leasequery store
        """
        return LeasequerySqliteStore(self.name)
