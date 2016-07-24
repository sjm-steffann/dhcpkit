0.9.1 - Unreleased
------------------

Added
^^^^^

- Added support for Internationalized Domain Names (IDN) in :meth:`~dhcpkit.utils.parse_domain_bytes` and
  :meth:`~dhcpkit.utils.encode_domain`. This makes it possible to use IDN everywhere in DHCPKit, including configuration
  files.

Changed
^^^^^^^

- Created ForOtherServerError as a subclass of CannotRespondError, to enable more accurate logging, and to make it
  possible to gather better statistics.

Deprecated
^^^^^^^^^^

Removed
^^^^^^^

Fixed
^^^^^

Security
^^^^^^^^


0.9.0 - 2016-07-16
------------------

- A complete rewrite of the DHCPv6 server with a new configuration style.
