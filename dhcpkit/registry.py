"""
Base class for pkg_resources based registries
"""
import collections
import logging

import pkg_resources
from dhcpkit.utils import camelcase_to_dash

logger = logging.getLogger(__name__)


class Registry(collections.UserDict):
    """
    Base class for registries
    """

    entry_point = 'dhcpkit.NONE'
    """The name of the entry_point group"""

    def __init__(self):
        """
        A custom dictionary that initialises itself with the entry points from pkg_resources
        """
        super().__init__()

        # A name-based alternative
        self.by_name = {}
        """An alternative name-based mapping"""

        # Try all the entry points
        entry_points = pkg_resources.iter_entry_points(group=self.entry_point)
        for entry_point in entry_points:
            # If the name is a string with an integer then convert it to a real integer
            try:
                name = int(entry_point.name)
            except ValueError:
                name = entry_point.name

            if name in self.data:
                logger.warning("Multiple entry points found for {} {}, using {}".format(
                    self.__class__.__name__, name, self.data[name]))
                continue

            try:
                # Load the entry point and store it
                loaded = entry_point.load()
                self.data[name] = loaded

                # Also store by name
                alternative_name = self.get_name(loaded)
                self.by_name[alternative_name] = loaded
            except pkg_resources.VersionConflict as e:
                # Wrong version, report
                logger.critical("Entry point {} for {} is not compatible: {}".format(
                    entry_point, self.__class__.__name__, e.report()))
                continue
            except ImportError:
                # Ok, this one isn't working, skip it
                logger.exception("Entry point {} for {} could not be loaded".format(
                    entry_point, self.__class__.__name__))
                continue

    def get_name(self, item: object) -> str:
        """
        Get the name for the by_name mapping.

        :param item: The item to determine the name of
        :return: The name to use as key in the mapping
        """
        return camelcase_to_dash(item.__name__)
