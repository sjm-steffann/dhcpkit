"""
This provides a backwards-compatibility layer for the Python typing system as described in PEP484
"""

try:
    # Try importing from Python's typing module.
    # Versions before 3.5.2 however don't support Type[], so test for that one explicitly.
    from typing import Type
    from typing import *
except ImportError:
    # Fall back to the version distributed with DHCPKit, either because:
    # - the typing module didn't exist
    # - Type[] was missing
    from .py352_typing import Type
    from .py352_typing import *
