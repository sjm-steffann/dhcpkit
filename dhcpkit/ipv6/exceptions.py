"""
All exceptions used when handling IPv6 DHCP
"""


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


class ListeningSocketError(Exception):
    """
    Signal that the listening socket could not be created.
    """


class InvalidPacketError(Exception):
    """
    Signal that an incoming message was invalid

    :type sender: (str, int, int, int)
    """

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender = sender
