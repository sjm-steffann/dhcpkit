"""
A custom manager that manages the shared rate limit counters
"""
import logging
import multiprocessing
import time
from multiprocessing.managers import BaseManager

logger = logging.getLogger(__name__)


class RateLimitCounters:
    """
    Counters for rate limiting of DHCPv6 requests
    """

    def __init__(self, rate: int, per: int, burst: int = None):
        self.counters = {}
        self.rate_per_second = rate / per
        self.burst = burst or rate

    def check_request(self, key: str) -> bool:
        """
        Check whether this request is within limits. This method uses the algorithm described on
        http://stackoverflow.com/questions/667508/whats-a-good-rate-limiting-algorithm#668327

        :param key: The key for this client
        :return: Whether we should allow this
        """
        now = time.time()

        # Get the stored state, or initialise a new one
        allowance, last_check = self.counters.setdefault(key, (self.burst, now))

        # Calculate the number of seconds since the last request
        time_passed = now - last_check

        # Add extra allowance for the time waited since the last request
        allowance += time_passed * self.rate_per_second
        if allowance > self.burst:
            # Don't allow more than the specified rate as burst size. No saving up!
            allowance = self.burst

        logger.debug('{}: {} allowance = {:0.2f}'.format(
            multiprocessing.current_process().name, key, allowance)
        )

        if allowance < 1:
            # Allowance exceeded, reject
            allow = False
        else:
            # Still enough allowance, accept and deduct message from allowance
            allow = True
            allowance -= 1

        # Store the new state
        self.counters[key] = allowance, now

        return allow


def init_manager_process(parent_logger, initializer=None, initargs=()):
    """
    Migrate the logger of the parent to the child. It will be a queue logger anyway.

    :param parent_logger: The logger from the parent
    :param initializer: Optional extra initializer
    :param initargs: Optional initializer arguments
    """
    global logger
    logger = parent_logger

    if initializer:
        initializer(*initargs)


class RateLimitManager(BaseManager):
    """
    A custom manager that manages the shared rate limit counters
    """

    def start(self, initializer=None, initargs=()):
        """
        Start the rate limit counter manager
        """
        super().start(initializer=init_manager_process, initargs=(logger,))


RateLimitManager.register('RateLimitCounters', RateLimitCounters)
