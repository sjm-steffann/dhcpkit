"""
The basic configuration objects
"""

import logging

import abc
from ZConfig.matcher import SectionValue

logger = logging.getLogger(__name__)


class ConfigSection:
    """
    Basic configuration section
    """

    def __init__(self, section: SectionValue):
        self.section = section
        self.clean_config_section()
        self.validate_config_section()

    # noinspection PyMethodMayBeStatic
    def clean_config_section(self):
        """
        Clean up the config, calculating defaults etc.
        """

    # noinspection PyMethodMayBeStatic
    def validate_config_section(self):
        """
        Validate if the information in the config section is acceptable
        """

    def __str__(self):
        return self.to_str()

    def to_str(self, indent: int = 0) -> str:
        """
        Return a readable string representation of this element. Because it is not in the real configuration file format
        we don't attempt to make it look like one. We intentionally make it look different.

        :param indent: How much indentation at the start of this element
        :return: The formatted representation
        """
        # Build output in here
        output = ''

        # Section type name, or None for the root
        section_type = self.section.getSectionType()

        # Opening line, unless this is the root
        if section_type:
            name = self.section.getSectionName()
            if name:
                output += '  ' * indent + '{} {}:\n'.format(section_type, name)
            else:
                output += '  ' * indent + '{}:\n'.format(section_type)

            indent += 1

        # Attributes
        attributes = self.section.getSectionAttributes()
        for key in attributes:
            # Get the value, and always make it a list, even if there is only one value, for easier formatting
            value = getattr(self.section, key)
            if isinstance(value, list):
                values = value
            else:
                values = [value]

            for value in values:
                if isinstance(value, ConfigSection):
                    # Config sections can format themselves
                    output += value.to_str(indent)
                else:
                    # For other types we just use their string representation
                    output += '  ' * indent + '{} = {}\n'.format(key, str(value))

        return output


class ConfigElementFactory(ConfigSection, metaclass=abc.ABCMeta):
    """
    Base class for factories to create elements from configuration
    """

    def __init__(self, section: SectionValue):
        self._element = None
        super().__init__(section)

    @abc.abstractmethod
    def create(self) -> object:
        """
        Override this method to create the element.

        :return: The element
        """
        return None

    def __call__(self) -> object:
        """
        Create the handler on demand and return it.

        :return: The option handler
        """
        # Create the handler if we haven't done so yet
        if self._element is None:
            self._element = self.create()

        return self._element
