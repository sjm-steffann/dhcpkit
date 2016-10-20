"""
Basic console logging based on verbosity
"""
import logging
import logging.handlers

from ZConfig.matcher import SectionValue
from dhcpkit.common.server.logging import DEBUG_HANDLING, DEBUG_PACKETS
from dhcpkit.common.server.logging.config_datatypes import logging_level


def set_verbosity_logger(logger: logging.Logger, verbosity: int, existing_console: logging.Handler = None):
    """
    Install a console based logger based based on the given verbosity.

    :param logger: The logger to add the handlers to
    :param verbosity: The verbosity level given as command line argument
    :param existing_console: The existing console handler
    """
    # Don't filter on level in the base logger
    logger.setLevel(logging.NOTSET)

    if existing_console:
        console = existing_console
    else:
        # No console configured but verbosity asked: add a console handler
        from dhcpkit.common.server.logging.config_elements import ConsoleHandlerFactory
        fake_section = SectionValue(name='',
                                    values={'level': logging_level('error'), 'color': None},
                                    matcher=None)
        console_factory = ConsoleHandlerFactory(fake_section)
        console = console_factory()
        logger.addHandler(console)

    # Set level according to verbosity
    if verbosity >= 5 and console.level > DEBUG_PACKETS:
        console.setLevel(DEBUG_PACKETS)
    if verbosity >= 4 and console.level > DEBUG_HANDLING:
        console.setLevel(DEBUG_HANDLING)
    if verbosity >= 3 and console.level > logging.DEBUG:
        console.setLevel(logging.DEBUG)
    elif verbosity == 2 and console.level > logging.INFO:
        console.setLevel(logging.INFO)
    elif verbosity >= 1 and console.level > logging.WARNING:
        console.setLevel(logging.WARNING)
    elif console.level > logging.CRITICAL:
        console.setLevel(logging.CRITICAL)
