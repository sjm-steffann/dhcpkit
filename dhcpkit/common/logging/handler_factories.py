import abc
import logging
import logging.handlers
import os

from ZConfig.datatypes import SocketAddress


class HandlerFactory(metaclass=abc.ABCMeta):
    """
    Abstract Base Class for handler factories. Subclasses must provide a create() method that creates a new handler.
    Calling the object will create a new handler when necessary and return the handler.
    """

    def __init__(self, section):
        self._handler = None
        self.section = section

    @abc.abstractmethod
    def create(self) -> logging.Handler:
        """
        Override this method to create the handler.

        :return: The logging handler
        """
        pass

    def __call__(self) -> logging.Handler:
        """
        Create the handler on demand and return it.

        :return: The logging handler
        """
        # Create the handler if we haven't done so yet
        if self._handler is None:
            self._handler = self.create()
            self._handler.setLevel(self.section.level)

        return self._handler


class ConsoleHandlerFactory(HandlerFactory):
    def __init__(self, section):
        super().__init__(section)

        # Try loading colorlog
        try:
            if self.section.color is False:
                # Explicitly disabled
                colorlog = None
            else:
                # noinspection PyPackageRequirements
                import colorlog
        except ImportError:
            if self.section.color is True:
                # Explicitly enabled, and failed
                raise ValueError("Colored logging turned on but the 'colorlog' package is not installed")

            colorlog = None

        self.colorlog = colorlog

    def create(self) -> logging.Handler:
        """
        Create a console handler

        :return: The logging handler
        """
        handler = logging.StreamHandler()

        if self.colorlog:
            formatter = self.colorlog.ColoredFormatter('{yellow}{asctime}{reset} '
                                                       '[{log_color}{levelname}{reset}] '
                                                       '{message}',
                                                       datefmt=logging.Formatter.default_time_format,
                                                       style='{')
        else:
            formatter = logging.Formatter('{asctime} [{levelname}] {message}',
                                          datefmt=logging.Formatter.default_time_format,
                                          style='{')

        handler.setFormatter(formatter)

        return handler


class FileHandlerFactory(HandlerFactory):
    def __init__(self, section):
        super().__init__(section)

        # Save the path. Cheat by accessing the matcher directly.
        # We need the real thing because it works relative to the config directory.
        # noinspection PyProtectedMember
        self.path = self.section._matcher.type.registry.get('existing-relative-dirpath')(section.getSectionName())

        # Size-based rotation and specifying a size go together
        if self.section.size and self.section.rotate != 'SIZE':
            raise ValueError("You can only specify a size when rotating based on size")
        elif not self.section.size and self.section.rotate == 'SIZE':
            raise ValueError("When rotating based on size you must specify a size")

        # Rotation and keeping old logs go together
        if self.section.keep and not self.section.rotate:
            raise ValueError("You can only specify how many log files to keep when rotation is enabled")
        elif not self.section.keep and self.section.rotate:
            raise ValueError("You must specify how many log files to keep when rotation is enabled")

    def create(self) -> logging.StreamHandler:
        """
        Create a console handler

        :return: The logging handler
        """
        if self.section.rotate == 'SIZE':
            # Rotate based on file size
            return logging.handlers.RotatingFileHandler(filename=self.path,
                                                        maxBytes=self.section.size,
                                                        backupCount=self.section.keep)
        elif self.section.rotate is not None:
            # Rotate on time
            return logging.handlers.TimedRotatingFileHandler(filename=self.path,
                                                             when=self.section.rotate,
                                                             backupCount=self.section.keep)
        else:
            # No rotation specified, used a WatchedFileHandler so that external rotation works
            return logging.handlers.WatchedFileHandler(filename=self.section.path)


class SysLogHandlerFactory(HandlerFactory):
    default_destinations = (
        '/dev/log',
        '/var/run/syslog',
        'localhost:514',
    )

    def __init__(self, section):
        super().__init__(section)

        # The name is the destination
        self.destination = section.getSectionName()

        if self.destination:
            # Apply the correct datatype
            self.destination = SocketAddress(self.destination)
        else:
            # Fallback in case no destination is specified
            for destination in self.default_destinations:
                if destination.startswith('/'):
                    if os.path.exists(destination):
                        # Destination is a path, check if it exists
                        self.destination = SocketAddress(destination)
                        break
                else:
                    # Not a path, just assume it's ok
                    self.destination = SocketAddress(destination)
                    break

    def create(self) -> logging.handlers.SysLogHandler:
        """
        Create a syslog handler

        :return: The logging handler
        """
        return logging.handlers.SysLogHandler(address=self.destination.address,
                                              facility=self.section.facility,
                                              socktype=self.section.protocol)
