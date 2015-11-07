"""
Base class for pkg_resources based registries
"""
import collections
import logging

import pkg_resources

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
                self.data[name] = entry_point.load()
            except ImportError:
                # Ok, this one isn't working, skip it
                logger.error("Entry points {} for {} could not be loaded".format(
                    entry_point, self.__class__.__name__))
                continue
