"""
Configuration elements for the static assignment handlers
"""
import logging

from ZConfig.datatypes import existing_file
from dhcpkit.ipv6.server.extensions.static_assignments.csv import CSVStaticAssignmentHandler
from dhcpkit.ipv6.server.extensions.static_assignments.sqlite import SqliteStaticAssignmentHandler
from dhcpkit.ipv6.server.handlers import HandlerFactory

logger = logging.getLogger(__name__)


class CSVStaticAssignmentHandlerFactory(HandlerFactory):
    """
    Factory for a handler that reads assignments from a CSV file
    """

    name_datatype = staticmethod(existing_file)

    def create(self) -> CSVStaticAssignmentHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the lifetimes
        address_preferred_lifetime = self.address_preferred_lifetime
        address_valid_lifetime = self.address_valid_lifetime
        prefix_preferred_lifetime = self.prefix_preferred_lifetime
        prefix_valid_lifetime = self.prefix_valid_lifetime

        return CSVStaticAssignmentHandler(
            self.name,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )


class SqliteStaticAssignmentHandlerFactory(HandlerFactory):
    """
    Factory for a handler that reads assignments from a SQLite database
    """

    name_datatype = staticmethod(existing_file)

    def create(self) -> SqliteStaticAssignmentHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the lifetimes
        address_preferred_lifetime = self.address_preferred_lifetime
        address_valid_lifetime = self.address_valid_lifetime
        prefix_preferred_lifetime = self.prefix_preferred_lifetime
        prefix_valid_lifetime = self.prefix_valid_lifetime

        return SqliteStaticAssignmentHandler(
            self.name,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )
