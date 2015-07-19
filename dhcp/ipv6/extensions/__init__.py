"""
Module containing extensions to the basic DHCPv6 RFC.
"""

import importlib
import pkgutil


def load_all():
    """
    Load all extensions
    """
    for module_finder, name, is_pkg in pkgutil.iter_modules(__path__):
        # Make sure we import all extensions we know about
        importlib.import_module('{}.{}'.format(__name__, name))
