"""
Handlers to apply to transaction bundles
"""

import logging

from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class HandlerException(Exception):
    """
    Base class for handler exceptions
    """


class CannotRespondError(HandlerException):
    """
    This exception signals that we cannot reply to this client.
    """


class UseMulticastError(HandlerException):
    """
    This exception signals that a STATUS_USEMULTICAST should be returned to the client.
    """


class Handler:
    """
    Base class for handlers
    """

    def __init__(self):
        """
        The main initialisation will be done in the master process. After initialisation the master process will create
        worker processes using the multiprocessing module. Things that can't be pickled and transmitted to the worker
        processes (think database connections etc) have to be initialised separately. Each worker process will call
        worker_init() to do so. Filters that don't need per-worker initialisation can do everything here in __init__().
        """

    # noinspection PyMethodMayBeStatic
    def worker_init(self):
        """
        Separate initialisation that will be called in each worker process that is created. Things that can't be forked
        (think database connections etc) have to be initialised here.
        """

    # noinspection PyMethodMayBeStatic
    def pre(self, bundle: TransactionBundle):
        """
        Pre-process the data in the bundle. Subclasses can update bundle state here or abort processing of the request
        by raising a CannotRespondError.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def handle(self, bundle: TransactionBundle):
        """
        Handle the data in the bundle. Subclasses should do their main work here.

        :param bundle: The transaction bundle
        """

    # noinspection PyMethodMayBeStatic
    def post(self, bundle: TransactionBundle):
        """
        Post-process the data in the bundle. Subclasses can e.g. clean up state. Subclasses assigning addresses should
        check whether the bundle.response is an AdvertiseMessage or a ReplyMessage. The class can change between
        handle() and post() when the server is using rapid-commit.

        :param bundle: The transaction bundle
        """
