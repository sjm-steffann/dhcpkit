"""
Datatypes useful for the logging component
"""
import logging
import logging.handlers
import socket

from ZConfig.datatypes import RangeCheckedConversion
from dhcpkit.common.server.logging import DEBUG_HANDLING, DEBUG_PACKETS


def syslog_facility(value: str) -> int:
    """
    Convert the strings representing syslog facilities to their numerical value

    :param value: The string representing the syslog facility
    :return: Numerical syslog facility
    """
    lower_value = value.lower()
    if lower_value not in logging.handlers.SysLogHandler.facility_names:
        raise ValueError("'{}' is not a valid syslog facility name".format(value))
    return logging.handlers.SysLogHandler.facility_names[lower_value]


def logging_level(value: str) -> int:
    """
    Convert the strings representing logging levels to their numerical value

    :param value: The string representing the logging level
    :return: Numerical logging level
    """
    name_to_level = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'debug-packets': DEBUG_PACKETS,
        'debug-handling': DEBUG_HANDLING,
        'notset': logging.NOTSET,
    }

    lookup_value = value.lower().replace('_', '-')
    if lookup_value not in name_to_level:
        raise ValueError("'{}' is not a valid log level".format(value))
    return name_to_level[lookup_value]


def udp_or_tcp(value: str) -> int:
    """
    Convert the strings "udp" and "tcp" to SOCK_DGRAM and SOCK_STREAM respectively

    :param value: The string "udp" or "tcp"
    :return: SOCK_DGRAM or SOCK_STREAM
    """
    lower_value = value.lower()
    if lower_value in ('udp', 'dgram'):
        return socket.SOCK_DGRAM
    elif lower_value in ('tcp', 'stream'):
        return socket.SOCK_STREAM
    else:
        raise ValueError("The protocol must be UDP (or DGRAM) or TCP (or STREAM)")


def rotation_style(value: str) -> str:
    """
    Determine the rotation style.

    :param value: String representation of rotation style
    :return: Normalised rotation style
    """
    lower_value = value.lower()
    # return 's'
    if lower_value in ('hour', 'hourly'):
        return 'h'
    elif lower_value in ('day', 'daily'):
        return 'd'
    elif lower_value in ('week', 'weekly'):
        return 'w'
    elif lower_value == 'size':
        return 'SIZE'
    else:
        raise ValueError("Rotation style must be hourly, daily, weekly or size")


rotation_count = RangeCheckedConversion(int, min=1)
