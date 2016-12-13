"""
Extensions to Pygments to correctly parse DHCPKit config files
"""
import re

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Comment, Keyword, Name, String, Text

__all__ = ['DHCPKitConfLexer']


class DHCPKitConfLexer(RegexLexer):
    """
    Lexer for configuration files following the DHCPKit config file format.
    """

    name = 'DHCPKitConf'
    aliases = ['dhcpkitconf', 'dhcpkit']
    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'(#.*?)$', Comment),
            (r'(<[^\s>]+)(?:(\s+)(.*?))?(>)',
             bygroups(Name.Tag, Text, String, Name.Tag)),
            (r'([a-z][\w-]*)(\s+)',
             bygroups(Name.Builtin, Text), 'value'),
            (r'\.+', Text),
        ],
        'value': [
            (r'\\\n', Text),
            (r'$', Text, '#pop'),
            (r'\\', Text),
            (r'[^\S\n]+', Text),
            (r'/([a-z0-9][\w./-]+)', String.Other),
            (r'(on|off|yes|no|true|false|'
             r'critical|error|warn|warning|info|debug-packets|debug-handling|debug|notset|'
             r'authpriv|auth|cron|daemon|ftp|kern|lpr|mail|news|security|syslog|uucp|local[0-7]|'
             r'udp|dgram|tcp|stream|'
             r'hourly|hour|daily|day|weekly|week|size|'
             r'user|group)\b', Keyword),
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', String.Double),
            (r'[^\s"\\]+', Text)
        ],
    }
