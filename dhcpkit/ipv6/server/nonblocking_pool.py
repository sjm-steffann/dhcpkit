"""
A multiprocessing pool that doesn't block when full. If we don't do this then the queue fills up with old messages and
the workers keep answering those while the client has probably already given up, instead of answering recent messages.
"""
from multiprocessing.pool import ApplyResult, Pool, RUN
from queue import Full

from dhcpkit.ipv6.server.listeners import IncomingPacketBundle, Replier
from typing import Any, Callable, Dict, Tuple


class NonBlockingPool(Pool):
    """
    A multiprocessing pool that doesn't block when full
    """

    # noinspection PyProtectedMember
    def apply_async(self, func: Callable, args: Tuple[IncomingPacketBundle, Replier] = (), kwds: Dict[str, Any] = None,
                    callback: Callable[[Any], None] = None, error_callback: Callable[[Exception], None] = None):
        """
        Asynchronous version of `apply()` method.
        """
        if self._state != RUN:
            raise ValueError("Pool not running")

        try:
            result = ApplyResult(self._cache, callback, error_callback)
            self._taskqueue.put(([(result._job, None, func, args, kwds or {})], None), block=False)
        except Full:
            return None

        return result

    def __reduce__(self):
        raise NotImplementedError(
            'pool objects cannot be passed between processes or pickled'
        )
