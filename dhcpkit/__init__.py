"""
Basic information about this package
"""
import sys

__version__ = '0.9.0'

# Make sure we have a usable typing module
from dhcpkit import typing
sys.modules['typing'] = typing
