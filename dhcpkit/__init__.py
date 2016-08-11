"""
DHCPKit internals
"""
import sys

from dhcpkit import typing

__version__ = '0.9.6a1'

# Make sure we have a usable typing module
sys.modules['typing'] = typing
