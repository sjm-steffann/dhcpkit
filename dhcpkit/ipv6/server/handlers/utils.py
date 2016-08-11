"""
Utility functions for handlers
"""
from dhcpkit.ipv6.options import Option, StatusCodeOption
from typing import List


def force_status(options: List[Option], new_status_code: StatusCodeOption):
    """
    If there is a StatusCodeOption with a different status code in the options list then replace it. Leave any option
    with the right status code. Add the given StatusCodeOption if there is none.

    :param options: The list of options to manipulate
    :param new_status_code: The wanted StatusCodeOption
    """

    # Check for any existing status options in the response
    for option in options:
        if not isinstance(option, StatusCodeOption):
            continue

        if option.status_code == new_status_code.status_code:
            # Ok, fine, someone already sent the right response
            return

        # Bad response: replace it
        options.remove(option)

    # Add our option
    options.append(new_status_code)
