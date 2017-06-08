"""
The basic configuration objects for logging
"""
import logging
import logging.handlers
import os
import sys

from ZConfig.datatypes import SocketAddress, existing_dirpath
from ZConfig.matcher import SectionValue
from dhcpkit.common.logging.verbosity import set_verbosity_logger
from dhcpkit.common.server.config_elements import ConfigElementFactory, ConfigSection


class Logging(ConfigSection):
    """
    Class managing the configured logging handlers.
    """

    def validate_config_section(self):
        """
        Check for duplicate handlers
        """
        # Check that we don't have multiple console loggers
        have_console = False
        for handler_factory in self.handlers:
            if isinstance(handler_factory, ConsoleHandlerFactory):
                if have_console:
                    raise ValueError("You cannot log to the console multiple times")
                have_console = True

    def configure(self, logger: logging.Logger, verbosity: int = 0) -> int:
        """
        Add all configured handlers to the supplied logger. If verbosity > 0 then make sure we have a console logger
        and force the level of the console logger based on the verbosity.

        :param logger: The logger to add the handlers to
        :param verbosity: The verbosity level given as command line argument
        :return: The lowest log level that is going to be handled
        """
        # Remove any previously configured loggers, in case we are re-configuring
        # We are deleting, so copy the list first
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

        # Add the handlers, keeping track of console loggers and saving the one with the "best" level.
        console = None
        for handler_factory in self.handlers:
            handler = handler_factory()
            logger.addHandler(handler)

            if isinstance(handler_factory, ConsoleHandlerFactory):
                console = handler

        # Set according to verbosity
        set_verbosity_logger(logger, verbosity, console)

        # Find the lowest log level
        lowest_level = logging.CRITICAL
        for handler in logger.handlers:
            if handler.level < lowest_level:
                lowest_level = handler.level

        # Return the lowest log level we want, so that we can filter lower priority messages earlier (where appropriate)
        return lowest_level


class ConsoleHandlerFactory(ConfigElementFactory):
    """
    Factory for a logging handler that logs to the console, optionally in colour.
    """

    def __init__(self, section: SectionValue):
        self.colorlog = None
        super().__init__(section)

    def validate_config_section(self):
        """
        Validate the colorlog setting
        """
        # Try loading colorlog
        try:
            if self.color is False:
                # Explicitly disabled
                colorlog = None
            else:
                # noinspection PyPackageRequirements
                import colorlog
        except ImportError:
            if self.color is True:
                # Explicitly enabled, and failed
                raise ValueError("Colored logging turned on but the 'colorlog' package is not installed")

            colorlog = None

        self.colorlog = colorlog

    def create(self) -> logging.StreamHandler:
        """
        Create a console handler

        :return: The logging handler
        """
        handler = logging.StreamHandler(sys.stderr)
        if self.colorlog and sys.stderr.isatty():
            formatter = self.colorlog.ColoredFormatter('{yellow}{asctime}{reset} '
                                                       '{purple}{processName}:{reset} '
                                                       '[{log_color}{levelname}{reset}] '
                                                       '{white}{message}{reset}',
                                                       style='{')
        else:
            formatter = logging.Formatter('{asctime} {processName}: [{levelname}] {message}',
                                          style='{')

        handler.setFormatter(formatter)
        handler.setLevel(self.level)

        return handler


class FileHandlerFactory(ConfigElementFactory):
    """
    Factory for a logging handler that logs to a file, optionally rotating it.
    """

    name_datatype = staticmethod(existing_dirpath)

    def __init__(self, section: SectionValue):
        super().__init__(section)

    def validate_config_section(self):
        """
        Validate if the combination of settings is valid
        """
        # Size-based rotation and specifying a size go together
        if self.size and self.rotate != 'SIZE':
            raise ValueError("You can only specify a size when rotating based on size")
        elif not self.size and self.rotate == 'SIZE':
            raise ValueError("When rotating based on size you must specify a size")

        # Rotation and keeping old logs go together
        if self.keep and not self.rotate:
            raise ValueError("You can only specify how many log files to keep when rotation is enabled")
        elif not self.keep and self.rotate:
            raise ValueError("You must specify how many log files to keep when rotation is enabled")

    def create(self) -> logging.StreamHandler:
        """
        Create a console handler

        :return: The logging handler
        """
        if self.section.rotate == 'SIZE':
            # Rotate based on file size
            handler = logging.handlers.RotatingFileHandler(filename=self.name,
                                                           maxBytes=self.section.size,
                                                           backupCount=self.section.keep)
        elif self.section.rotate is not None:
            # Rotate on time
            handler = logging.handlers.TimedRotatingFileHandler(filename=self.name,
                                                                when=self.section.rotate,
                                                                backupCount=self.section.keep)
        else:
            # No rotation specified, used a WatchedFileHandler so that external rotation works
            handler = logging.handlers.WatchedFileHandler(filename=self.section.path)

        formatter = logging.Formatter('{asctime} {processName}: [{levelname}] {message}',
                                      style='{')

        handler.setLevel(self.section.level)
        handler.setFormatter(formatter)
        return handler


class SysLogHandlerFactory(ConfigElementFactory):
    """
    Factory for a logging handler that logs to syslog.
    """
    default_destinations = (
        '/dev/log',
        '/var/run/syslog',
        'localhost:514',
    )

    name_datatype = staticmethod(lambda value: SocketAddress(value))

    def clean_config_section(self):
        """
        Fill in the name automatically if not given
        """
        # The name is the destination
        if not self.name:
            # Fallback in case no destination is specified
            for destination in self.default_destinations:
                if destination.startswith('/'):
                    if os.path.exists(destination):
                        # Destination is a path, check if it exists
                        self.name = SocketAddress(destination)
                        break
                else:
                    # Not a path, just assume it's ok
                    self.name = SocketAddress(destination)
                    break

    def create(self) -> logging.handlers.SysLogHandler:
        """
        Create a syslog handler

        :return: The logging handler
        """
        handler = logging.handlers.SysLogHandler(address=self.name.address,
                                                 facility=self.section.facility,
                                                 socktype=self.section.protocol)
        handler.setLevel(self.section.level)
        return handler
