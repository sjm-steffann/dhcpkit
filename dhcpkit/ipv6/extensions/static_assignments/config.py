from dhcpkit.ipv6.extensions.static_assignments.option_handlers.csv import CSVStaticAssignmentOptionHandler
from dhcpkit.ipv6.extensions.static_assignments.option_handlers.shelf import ShelfStaticAssignmentOptionHandler
from dhcpkit.ipv6.extensions.static_assignments.option_handlers.sqlite import SqliteStaticAssignmentOptionHandler
from dhcpkit.ipv6.server.config import ConfigElementFactory


class CSVStaticAssignmentOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> CSVStaticAssignmentOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the lifetimes
        address_preferred_lifetime = self.section.address_preferred_lifetime
        address_valid_lifetime = self.section.address_valid_lifetime
        prefix_preferred_lifetime = self.section.prefix_preferred_lifetime
        prefix_valid_lifetime = self.section.prefix_valid_lifetime

        csv_filename = self.section.assignments_file

        return CSVStaticAssignmentOptionHandler(
            csv_filename,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )


class ShelfStaticAssignmentOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> ShelfStaticAssignmentOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the lifetimes
        address_preferred_lifetime = self.section.address_preferred_lifetime
        address_valid_lifetime = self.section.address_valid_lifetime
        prefix_preferred_lifetime = self.section.prefix_preferred_lifetime
        prefix_valid_lifetime = self.section.prefix_valid_lifetime

        shelf_filename = self.section.assignments_file

        return ShelfStaticAssignmentOptionHandler(
            shelf_filename,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )


class SqliteStaticAssignmentOptionHandlerFactory(ConfigElementFactory):
    def create(self) -> SqliteStaticAssignmentOptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :return: A handler object
        """

        # Get the lifetimes
        address_preferred_lifetime = self.section.address_preferred_lifetime
        address_valid_lifetime = self.section.address_valid_lifetime
        prefix_preferred_lifetime = self.section.prefix_preferred_lifetime
        prefix_valid_lifetime = self.section.prefix_valid_lifetime

        sqlite_filename = self.section.assignments_file

        return SqliteStaticAssignmentOptionHandler(
            sqlite_filename,
            address_preferred_lifetime, address_valid_lifetime,
            prefix_preferred_lifetime, prefix_valid_lifetime
        )
