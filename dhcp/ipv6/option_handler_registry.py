"""
The registry that keeps track of which class implements which option handler
"""

# Name Registry
# type: {str: OptionHandler}
name_registry = {}


def register(subclass: type):
    """
    Register a new option handler in the option handler registry.

    :param subclass: A subclass of OptionHandler that implements the handler
    """
    from dhcp.ipv6.option_handlers import OptionHandler
    from dhcp.utils import camelcase_to_dash

    if not issubclass(subclass, OptionHandler):
        raise TypeError('Only OptionHandlers can be registered')

    # Store based on name
    name = subclass.__name__
    if name.endswith('Handler'):
        name = name[:-7]
    if name.endswith('Option'):
        name = name[:-6]
    name = camelcase_to_dash(name)
    name_registry[name] = subclass
