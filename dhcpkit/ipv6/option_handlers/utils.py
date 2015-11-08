"""
Utility functions for option handlers
"""
from collections import namedtuple
# A simple structure to store an address and/or prefix assignment in
from dhcpkit.ipv6.options import Option, StatusCodeOption

Assignment = namedtuple('Assignment', ['address', 'prefix'])


def force_status(options: [Option], new_status_code: StatusCodeOption):
    """
    If there is a StatusCodeOption with a different status code in the options list then replace it. Leave any option
    with the right status code. Add the given StatusCodeOption if there is none.

    :param options: The list of options to manipulate
    :param new_status_code: The wanted StatusCodeOption
    """

    # Check for any existing status options in the response
    existing = [option for option in options if isinstance(option, StatusCodeOption)]
    existing = existing[0] if existing else None
    if existing:
        if existing.status_code == new_status_code.status_code:
            # Ok, fine, someone already sent the right response
            return

        # Bad response: replace it
        options.remove(existing)

    # Add our option
    options.append(new_status_code)
