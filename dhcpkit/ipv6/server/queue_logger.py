"""
Adapt the QueueListener so that it respects the log levels of the handlers. Based on the Python 3.5 implementation.
"""
from logging.handlers import QueueHandler, QueueListener
from multiprocessing.queues import Full, Queue


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

    def dequeue(self, block):
        """
        Dequeue a record and return it, optionally blocking. Return the sentinel on EOF because otherwise there are
        strange errors after a reload.
        """
        try:
            return self.queue.get(block)
        except EOFError:
            return self._sentinel


class WorkerQueueHandler(QueueHandler):
    """
    A logging handler that queues messages and doesn't cause exceptions when the queue is full.
    """

    def __init__(self, queue: Queue):
        super().__init__(queue)
        self.log_id = None

    def prepare(self, record):
        """
        Prepares a record for queuing. The object returned by this method is
        enqueued. This implementation adds the log_id if it is set.
        """
        record = super().prepare(record)

        # Put in the log_id if it is set
        if self.log_id is not None:
            log_id = str(self.log_id)
            record.message = log_id + ': ' + record.message
            record.msg = record.message

        return record

    def enqueue(self, record):
        """
        Enqueue a record.

        Try three times rapidly, then just drop it.
        """
        for _ in (1, 2, 3):
            try:
                self.queue.put_nowait(record)
                return
            except Full:
                pass
