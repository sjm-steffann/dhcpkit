"""
Adapt the QueueListener so that it respects the log levels of the handlers. Based on the Python 3.5 implementation.
"""
from logging.handlers import QueueListener


class QueueLevelListener(QueueListener):
    """
    QueueListener that respects log levels
    """

    def handle(self, record):
        """
        Handle a record.

        This just loops through the handlers offering them the record to handle.
        """
        record = self.prepare(record)
        for handler in self.handlers:
            if record.levelno >= handler.level:
                handler.handle(record)

    # noinspection PyPep8Naming
    def addHandler(self, handler):
        """
        Add the specified handler to this logger.
        """
        if handler not in self.handlers:
            self.handlers.append(handler)

    # noinspection PyPep8Naming
    def removeHandler(self, handler):
        """
        Remove the specified handler from this logger.
        """
        if handler in self.handlers:
            self.handlers.remove(handler)
