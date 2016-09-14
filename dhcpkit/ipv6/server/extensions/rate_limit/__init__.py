"""
Handler to rate limit clients that keep rapidly sending requests.
"""
import logging

from dhcpkit.ipv6.server.extensions.rate_limit.key_functions import duid_key
from dhcpkit.ipv6.server.extensions.rate_limit.manager import RateLimitManager
from dhcpkit.ipv6.server.handlers import CannotRespondError, Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

# Create the logger
logger = logging.getLogger(__name__)


class RateLimitHandler(Handler):
    """
    Handler to rate limit clients that keep rapidly sending requests.

    The most common reason that clients keep sending requests is when they get
    an answer they don't like. The best way to slow them down is to just stop
    responding to them.
    """

    def __init__(self, key=duid_key, rate: int = 5, per: int = 30, burst: int = None):
        super().__init__()

        # Create a dictionary that will be shared between child processes
        my_manager = RateLimitManager()
        my_manager.start()

        # noinspection PyUnresolvedReferences
        self.shared_counters = my_manager.RateLimitCounters(rate, per, burst)

        # Set the key extraction function
        self.key = key

    def __str__(self):
        return "{} on {}".format(self.__class__.__name__,
                                 self.key.__name__)

    def pre(self, bundle: TransactionBundle):
        """
        Check the rate of incoming requests from this client and stop processing
        when a client sends too many requests.

        :param bundle: The transaction bundle
        """
        key = self.key(bundle)
        allow = self.shared_counters.check_request(key)
        if not allow:
            raise CannotRespondError("Client {} has exceeded rate limit".format(key))
