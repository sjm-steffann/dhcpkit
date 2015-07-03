from dhcp.ipv6.handlers import Handler


class DebugHandler(Handler):
    pass


def get_handler(options):
    return DebugHandler(options)
