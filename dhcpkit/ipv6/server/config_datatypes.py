"""
Extra datatypes for the server configuration
"""

# noinspection PyUnresolvedReferences
from dhcpkit.common.server.config_datatypes import *


def number_of_workers(value: str) -> int:
    """
    The number of worker processes, must be 1 or more
    :param value: The number of processes
    :return: The validated number of processes
    """
    value = int(value)
    if value < 1:
        raise ValueError("Number of workers must be at least 1")
    return value
