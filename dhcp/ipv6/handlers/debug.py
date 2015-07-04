import configparser

from dhcp.ipv6.handlers import Handler


class DebugHandler(Handler):
    pass


def get_handler(config: configparser.ConfigParser):
    return DebugHandler(config)
