import configparser

from dhcp.ipv6.handlers import Handler
from dhcp.ipv6.messages import ClientServerMessage, AdvertiseMessage, Message


class DebugHandler(Handler):
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def handle_solicit_message(self, request: ClientServerMessage, relay_messages: list,
                               sender: tuple, receiver: tuple) -> (Message, tuple) or Message or None:
        return AdvertiseMessage()


def get_handler(config: configparser.ConfigParser):
    return DebugHandler(config)
