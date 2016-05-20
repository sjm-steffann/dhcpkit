from ZConfig.matcher import SectionValue

from .datatypes import *
from .handler_factories import *


class Logging:
    """
    Class managing the configured logging handlers.
    """

    def __init__(self, section):
        self.section = section

        # Check that we don't have multiple console loggers
        have_console = False
        for handler_factory in self.section.handlers:
            if isinstance(handler_factory, ConsoleHandlerFactory):
                if have_console:
                    raise ValueError("You cannot log to the console multiple times")
                have_console = True

    def configure(self, logger: logging.Logger, verbosity: int = 0):
        """
        Add all configured handlers to the supplied logger. If verbosity > 0 then make sure we have a console logger
        and force the level of the console logger based on the verbosity.

        :param logger: The logger to add the handlers to
        :param verbosity: The verbosity level given as command line argument
        """
        # Don't filter on level in the base logger
        logger.setLevel(logging.NOTSET)

        # Add the handlers, keeping track of console loggers and saving the one with the "best" level.
        console = None
        for handler_factory in self.section.handlers:
            handler = handler_factory()
            logger.addHandler(handler)

            if isinstance(handler_factory, ConsoleHandlerFactory):
                console = handler

        # If verbosity is 0 then leave it as it is
        if verbosity == 0:
            return

        if not console:
            # No console configured but verbosity asked: add a console handler
            fake_section = SectionValue(name='',
                                        values={'level': logging_level('notset'), 'color': ''},
                                        matcher=None)
            console_factory = ConsoleHandlerFactory(fake_section)
            console = console_factory()
            logger.addHandler(console)

        # Override level according to verbosity
        if verbosity >= 3:
            console.setLevel(logging.DEBUG)
        elif verbosity == 2:
            console.setLevel(logging.INFO)
        elif verbosity >= 1:
            console.setLevel(logging.WARNING)
