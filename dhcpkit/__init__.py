"""
DHCPKit internals
"""
import sys

from dhcpkit import typing

__version__ = '0.9.0'

# Make sure we have a usable typing module
sys.modules['typing'] = typing
