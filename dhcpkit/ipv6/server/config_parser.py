"""
Configuration file definition and parsing
"""
import inspect
import logging
import os

from ZConfig import SchemaResourceError
from ZConfig.loader import SchemaLoader, ConfigLoader

from dhcpkit.ipv6.server.config_elements import MainConfig
from dhcpkit.ipv6.server.extension_registry import server_extension_registry

logger = logging.getLogger()


def load_config(config_filename: str) -> MainConfig:
    """
    Load the given configuration file.

    :param config_filename: The configuration file
    :return: The parsed config
    """
    logger.debug("Loading configuration file {}".format(config_filename))

    # Construct the paths to all necessary files
    schema_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config_schema.xml"))
    config_filename = os.path.realpath(config_filename)

    # Load the schema with this registry
    schema_loader = SchemaLoader()
    schema = schema_loader.loadURL(url=schema_file)

    # Build the config loader based on the schema, extended with the schemas of option handlers
    config_loader = ConfigLoader(schema=schema)

    # Iterate over all server extensions
    for extension_name, extension in server_extension_registry.items():
        # Option handlers that refer to packages contain components
        if inspect.ismodule(extension) and hasattr(extension, '__path__'):
            # It's a package! Try to import
            try:
                config_loader.importSchemaComponent(extension.__name__)
                logger.debug("Configuration extension {} loaded".format(extension_name))
            except SchemaResourceError:
                # Component missing, assume it's a package without a config component
                pass

    config, handlers = config_loader.loadURL(config_filename)

    return config
