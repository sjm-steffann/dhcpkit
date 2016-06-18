"""
Configuration elements for the static assignment handlers
"""
import logging
import os

from ZConfig.datatypes import existing_file
from ZConfig.matcher import SectionValue

from dhcpkit.common.server.config_elements import ConfigElementFactory
from dhcpkit.ipv6.server.extensions.static_assignments.csv import CSVStaticAssignmentHandler
from dhcpkit.ipv6.server.extensions.static_assignments.shelf import ShelfStaticAssignmentHandler
from dhcpkit.ipv6.server.extensions.static_assignments.sqlite import SqliteStaticAssignmentHandler

logger = logging.getLogger(__name__)


class CSVStaticAssignmentHandlerFactory(ConfigElementFactory):
    """
    Factory for a handler that reads assignments from a CSV file
    """

    def __init__(self, section: SectionValue):
        self.csv_filename = None
        super().__init__(section)

    def validate_config_section(self):
        """
        Validate if the combination of settings is valid
        """
        self.csv_filename = os.path.realpath(existing_file(self._section.getSectionName()))

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
            self.csv_filename,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )


class ShelfStaticAssignmentHandlerFactory(ConfigElementFactory):
    """
    Factory for a handler that reads assignments from a Shelf
    """

    def __init__(self, section: SectionValue):
        self.shelf_filename = None
        super().__init__(section)

    def validate_config_section(self):
        """
        Validate if the combination of settings is valid
        """
        self.shelf_filename = os.path.realpath(existing_file(self._section.getSectionName()))

    def create(self) -> ShelfStaticAssignmentHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the lifetimes
        address_preferred_lifetime = self.address_preferred_lifetime
        address_valid_lifetime = self.address_valid_lifetime
        prefix_preferred_lifetime = self.prefix_preferred_lifetime
        prefix_valid_lifetime = self.prefix_valid_lifetime

        return ShelfStaticAssignmentHandler(
            self.shelf_filename,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )


class SqliteStaticAssignmentHandlerFactory(ConfigElementFactory):
    """
    Factory for a handler that reads assignments from a SQLite database
    """

    def __init__(self, section: SectionValue):
        self.sqlite_filename = None
        super().__init__(section)

    def validate_config_section(self):
        """
        Validate if the combination of settings is valid
        """
        self.sqlite_filename = os.path.realpath(existing_file(self._section.getSectionName()))

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
            self.sqlite_filename,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )
