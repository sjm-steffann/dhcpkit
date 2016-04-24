import configparser
import logging
import os
import re
import sys

from dhcpkit.utils import camelcase_to_dash

logger = logging.getLogger()


class ConfigError(Exception):
    pass


BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                  '0': False, 'no': False, 'false': False, 'off': False}


def str_to_bool(value: str or bool) -> bool:
    """
    Convert any valid string representation of a boolean value to a real boolean
    """
    if isinstance(value, bool):
        return value

    if not isinstance(value, str) or not value.lower() in BOOLEAN_STATES:
        raise ValueError("Value needs to be a string representing a boolean value")

    return BOOLEAN_STATES[value.lower()]


class ServerConfigParser(configparser.ConfigParser):
    """
    Special config parser that normalises section names
    """

    class SectionNameNormalisingRegEx:
        """
        Fake regex that normalises its output
        """
        SECTCRE = configparser.ConfigParser.SECTCRE

        def match(self, value: str):
            """
            Fake regex match function that normalises the result and then creates a real match object.

            :param value: the value to match against
            :returns: A match object or None
            """
            # Do matching using the normal re
            matches = self.SECTCRE.match(value)

            # No match: don't change anything
            if not matches:
                return matches

            # Match! Now monkey-patch the result
            header = matches.group('header')
            header = ServerConfigParser.normalise_section_name(header)

            # And recreate
            return self.SECTCRE.match('[{}]'.format(header))

    SECTCRE = SectionNameNormalisingRegEx()

    def optionxform(self, optionstr: str) -> str:
        """
        Transform option names to a standard form. Allow options with underscores and convert those to dashes.

        :param optionstr: The original option name
        :returns: The normalised option name
        """
        return optionstr.lower().replace('_', '-')

    @staticmethod
    def normalise_section_name(section: str) -> str:
        """
        Normalise a section name.

        :param section: The raw name of the section
        :returns: The normalised name
        """
        # Collapse multiple spaces
        section = re.sub(r'[\t ]+', ' ', section)

        # Split
        parts = section.split(' ')
        parts[0] = parts[0].lower()

        # Special section names
        if parts[0] == 'interface':
            # Check name structure
            if len(parts) != 2:
                raise configparser.ParsingError("Interface sections must be named [interface xyz] "
                                                "where 'xyz' is an interface name")

        elif parts[0] == 'option':
            # Check name structure
            if not (2 <= len(parts) <= 3):
                raise configparser.ParsingError("Option sections must be named [option xyz] or [option xyz id]"
                                                "where 'xyz' is an option handler name and 'id' is an identifier "
                                                "to distinguish between multiple handlers of the same type")

            if '-' in parts[1] or '_' in parts[1]:
                parts[1] = parts[1].replace('_', '-').lower()
            else:
                parts[1] = camelcase_to_dash(parts[1])

            # If the name ends with
            if parts[1].endswith('-option-handler'):
                parts[1] = parts[1][:-15]

        elif parts[0] not in ('logging', 'server',):
            raise configparser.ParsingError("Invalid section name: [{}]".format(section))

        # Reconstruct
        return ' '.join(parts)

    def add_section(self, section):
        """
        Also normalise section names that are added by the code.

        :param section: The section name
        """
        section = self.normalise_section_name(section)
        super().add_section(section)


def load_config(config_filename: str) -> dict:
    """
    Load the given configuration file.

    :param config_filename: The configuration file
    :return: The parsed config
    """
    logger.debug("Loading configuration file {}".format(config_filename))
    config_filename = os.path.realpath(config_filename)

    config = ServerConfigParser()

    # Create mandatory sections and options
    config.add_section('logging')
    config['logging']['facility'] = 'daemon'

    config.add_section('server')
    config['server']['duid'] = 'auto'
    config['server']['message-handler'] = 'standard'
    config['server']['user'] = 'nobody'
    config['server']['group'] = ''
    config['server']['exception-window'] = '1.0'
    config['server']['max-exceptions'] = '10'
    config['server']['threads'] = '10'
    config['server']['working-directory'] = os.path.dirname(config_filename)

    try:
        config_file = open(config_filename, mode='r', encoding='utf-8')
        config.read_file(config_file)
    except FileNotFoundError:
        logger.error("Configuration file {} not found".format(config_filename))
        sys.exit(1)

    # Convert to a dictionary so that it will be easier to switch to a different parser
    config = {section: {option: config[section][option] for option in config[section]} for section in config}

    return config
