"""
Worker process for handling requests using multiprocessing.
"""
import logging
import logging.handlers
import signal
from logging.handlers import QueueHandler
from multiprocessing import Queue, current_process

import re

from dhcpkit.ipv6.messages import RelayServerMessage
from dhcpkit.ipv6.server.message_handler import MessageHandler

# These globals will be set by setup_worker()

logger = None
""":type: logging.Logger"""

current_message_handler = None
""":type: MessageHandler"""


def setup_worker(message_handler: MessageHandler, logging_queue: Queue):
    """
    This function will be called after a new worker process has been created. Its purpose is to set the global
    variables in this specific worker process so that they can be reused across multiple requests. Otherwise we would
    have to pickle them each and every time, and because they are static that would be a waste.

    :param message_handler: The message handler for the incoming requests
    :param logging_queue: The queue where we can deposit log messages so the main process can log them
    """
    # Let's shorten the process name a bit by removing everything except the "Worker-x" bit at the end
    this_process = current_process()
    this_process.name = re.sub(r'^.*(Worker-\d+)$', r'\1', this_process.name)

    # Ignore normal signal handling
    signal.signal(signal.SIGINT, lambda signum, frame: None)
    signal.signal(signal.SIGTERM, lambda signum, frame: None)
    signal.signal(signal.SIGHUP, lambda signum, frame: None)

    # Save the logger, don't let it filter, send everything to the queue
    global logger

    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)

    logging_handler = QueueHandler(logging_queue)
    logger.addHandler(logging_handler)

    # Save the message handler
    global current_message_handler
    current_message_handler = message_handler

    # Run the per-process startup code for the message handler and its children
    message_handler.worker_init()


def handle_message(incoming_message: RelayServerMessage, received_over_multicast: bool, marks: [str]):
    """
    Handle a single incoming request. This is supposed to be called in a separate worker thread that has been
    initialised with setup_worker().

    :param incoming_message: The incoming message
    :param received_over_multicast: Whether the packet was received over multicast
    :param marks: A list of marks, usually set by the listener
    :return: The outgoing packet, if any
    """
    try:
        return current_message_handler.handle(incoming_message, received_over_multicast, marks)
    except Exception as e:
        logger.error("Caught unexpected exception {!r}".format(e))
