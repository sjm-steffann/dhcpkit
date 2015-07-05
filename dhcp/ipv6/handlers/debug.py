import configparser

from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import ClientServerMessage, AdvertiseMessage


class DebugHandler(Handler):
    def handle_solicit_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple):
        return AdvertiseMessage()


def get_handler(config: configparser.ConfigParser):
    return DebugHandler(config)
