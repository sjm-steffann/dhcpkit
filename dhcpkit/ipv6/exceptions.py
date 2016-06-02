"""
All exceptions used when handling IPv6 DHCP
"""


class InvalidPacketError(Exception):
    """
    Signal that an incoming message was invalid

    :type sender: (str, int, int, int)
    """

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender = sender

    def __str__(self):
        return "Invalid packet from {}".format(self.sender)
