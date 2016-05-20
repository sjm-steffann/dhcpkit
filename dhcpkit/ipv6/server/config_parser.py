import inspect
import logging
import os
import sys

from ZConfig.datatypes import Registry
from ZConfig.loader import SchemaLoader, ConfigLoader

from dhcpkit.ipv6.server.datatypes import register_relative_path_datatypes, register_domain_datatypes

logger = logging.getLogger()


def test_zconfig():
    # We can't load the option handler registry on boot, so import it here
    from dhcpkit.ipv6.server.extension_registry import server_extension_registry

    # Construct the paths to all necessary files
    schema_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_schema.xml"))
    config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../etc/test.conf"))

    # Build the registry with available datatypes
    registry = Registry()
    config_file_path = os.path.dirname(config_file)
    register_relative_path_datatypes(registry, basedir=config_file_path)
    register_domain_datatypes(registry)

    # Load the schema with this registry
    schema_loader = SchemaLoader(registry=registry)
    schema = schema_loader.loadURL(url=schema_file)

    # Build the config loader based on the schema, extended with the schemas of option handlers
    config_loader = ConfigLoader(schema=schema)

    # Iterate over all option handlers
    for extension_name, extension in server_extension_registry.items():
        # Option handlers that refer to packages contain components
        if inspect.ismodule(extension) and hasattr(extension, '__path__'):
            # It's a package!
            config_loader.importSchemaComponent(extension.__name__)

    config, handlers = config_loader.loadURL(config_file)

    return config, handlers


def load_config(config_filename: str) -> dict:
    """
    Load the given configuration file.

    :param config_filename: The configuration file
    :return: The parsed config
    """
    logger.debug("Loading configuration file {}".format(config_filename))
    config_filename = os.path.realpath(config_filename)

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
