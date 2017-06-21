1.0.5 - 2017-06-21
------------------

New features
^^^^^^^^^^^^

- Provide RPM repositories at https://repo.dhcpkit.org/
- Add PD-Exclude option implementation
- Add Client FQDN option implementation
- Add Timezone options implementation
- Add Relay Echo-Request option implementation
- Add Relay Echo-Request option handler implementation

Fixes
^^^^^

- Fixed Python type annotations in many places

Changes for users
^^^^^^^^^^^^^^^^^

- Show LDRA relays when printing :class:`.TransactionBundle`
- The DHCPv6 server will try to keep going when not running as root, it might sometimes work, for example when
  connecting to a VPP instance instead of the usual opening listening sockets on low ports

Changes for developers
^^^^^^^^^^^^^^^^^^^^^^

- Improve DNS handling: be explicit about difference between absolute and relative domain names
- New :class:`.UnknownProtocolElement` available for more generic protocol parsing
- :data:`.All_DHCP_Relay_Agents_and_Servers` and :data:`.All_DHCP_Servers` are now instances of IPv6Address instead of
  strings
- Added an :class:`.IgnoreMessage` exception type so listeners can signal to the server that the received data is to be
  ignored
- The :class:`.IncompleteMessage` exception is now a subclass of :class:`.IgnoreMessage`


1.0.4 - 2016-12-17
------------------

New features
^^^^^^^^^^^^

- Provide debian/ubuntu packaging with init/init.d/systemd scripts
- Provide an extensive default configuration
- Allow the control socket location to be overridden from the command line

Fixes
^^^^^

- Improve ipv6-dhcpd to ipv6-dhcpctl communication when shutting down
- Add missing copyright statement for RFC 7598
- Fix Sphinx RFC reference

Changes for users
^^^^^^^^^^^^^^^^^

- Allow unicast listening on ::1 for testing purposes

Changes for developers
^^^^^^^^^^^^^^^^^^^^^^

- Make python dependencies more accurate
- Make building process for documentation more stable


1.0.3 - 2016-11-17
------------------

Fixes
^^^^^

- Fix leasequery statistics output, also fixes Observium stats


1.0.2 - 2016-11-16
------------------

Why?
^^^^

- Re-release with updated changelog and status


1.0.0 - 2016-11-16
------------------

New features
^^^^^^^^^^^^

- Add rate limit handler to ignore obnoxious clients
- Add implementation for the Leasequery and Bulk Leasequery protocols

Fixes
^^^^^

- Ignore MAC address `00:00:00:00:00:00` when searching for a server-id
- Fix finding the inner relay message in a RelayForwardMessage

Changes for users
^^^^^^^^^^^^^^^^^

- Improve logging for ignored messages
- The default log level now only logs errors, not warnings
- Improve exception handling and logging for errors during worker initialisation

Changes for developers
^^^^^^^^^^^^^^^^^^^^^^

- Sending replies has been moved from the main process to the worker processes
- Therefore :class:`.OutgoingPacketBundle` does no longer exist
- Constants for status codes have been renamed to be more consistent, the old names have been deprecated and will be
  removed in the future
- Tests have been moved under the dhcpkit module to be easier to import from other extensions (for example when they
  need a solicit message and packet to test with)
- Added Leasequery and Bulk Leasequery messages, options and status codes
- Leasequery needs RelayForwardMessages without a contained message, so allow that now
- Code for privilege management have been moved to dhcpkit.common
- Code for console logging has been moved to dhcpkit.common.logging
- Replies are now sent directly from worker processes, not first handed back to the master and then sent from there
- Refactor listeners and message handling to allow for TCP listeners and leasequery extensions
- Open sockets with SO_REUSEADDR so we can restart quickly without having to wait for TIME_WAIT
- Allow for multiple responses in transaction bundle, especially useful for TCP connections


0.9.5 - 2016-08-11
------------------

New features
^^^^^^^^^^^^

- 2.5x speed improvement.

Changes for developers
^^^^^^^^^^^^^^^^^^^^^^

- :meth:`.ProtocolElement.parse` and the :meth:`~.ProtocolElement.load_from` methods it uses no longer call
  :meth:`.ProtocolElement.validate` because every (nested) element validating everything all the time is rather
  inefficient. Now callers are supposed to call :meth:`.ProtocolElement.validate` themselves (if they want to).
- We no longer use :mod:`abc` and :class:`~abc.ABCMeta`. It turned out that all the run-time validation it did caused a
  ±20% slow down.


0.9.4 - 2016-08-04
------------------

New features
^^^^^^^^^^^^

- Added support for the :rfc:`6939` client link-layer address relay option
- Added support for the :rfc:`4580` subscriber-id relay option
- Added support for the :rfc:`6334` DS-Lite AFTR tunnel endpoint name option
- Added support for the :rfc:`7598` MAP options
- Added support for :mod:`~dhcpkit.ipv6.extensions.linklayer_id` and :mod:`~dhcpkit.ipv6.extensions.subscriber_id` in
  :ref:`static-csv` and :ref:`static-sqlite`

Fixes
^^^^^

- Fix error where command line log-level argument was ignored.
- Fix error that caused every message to be interpreted as received-over-multicast
- Don't block when the inbound queue is full, just drop the message and continue
- Fixed an interface-id parsing bug in :ref:`static-csv` and :ref:`static-sqlite`
- Allow UnknownOption in all options, otherwise we reject messages with options that contain unknown sub-options


0.9.3 - 2016-07-27
------------------

Fixes
^^^^^

- Not all systems have a ``wheel`` group anymore, so don't use that as a default group for the control socket.
- Linux doesn't support SIGINFO, and its functionality has become redundant with the new control socket functionality,
  so remove SIGINFO handling.

Changes for users
^^^^^^^^^^^^^^^^^

- Critical errors are now always shown on `stderr`. Otherwise the server could crash without the user seeing the reason.


0.9.2 - 2016-07-27
------------------

Fixes
^^^^^

- A packaging error slipped through the checks, and it turns out that crucial XML files weren't packaged in previous
  0.9.x versions. This has now been fixed.


0.9.1 - 2016-07-27
------------------

New features
^^^^^^^^^^^^

- It is now possible to use IDNs everywhere in DHCPKit, including configuration files.
- Implement a domain socket to control the server process.
- Added :ref:`ipv6-dhcpctl` to control the server process through the domain socket.
- Added a configuration section ``<statistics>`` to specify categories that you would like statistics on. Currently it is
  possible to gather statistics per interface, client subnet or relay.
- Added ``stats`` and ``stats-json`` commands for `ipv6-dhcpctl`.

Changes for users
^^^^^^^^^^^^^^^^^

- Create PID file /var/run/ipv6-dhcpd.pid by default.
- Create domain socket /var/run/ipv6-dhcpd.sock control the server by default.

Changes for developers
^^^^^^^^^^^^^^^^^^^^^^

- Added support for Internationalized Domain Names (IDN) in :meth:`~dhcpkit.utils.parse_domain_bytes` and
  :meth:`~dhcpkit.utils.encode_domain`.
- Created ForOtherServerError as a subclass of CannotRespondError, to enable more accurate logging, and to make it
  possible to gather better statistics.
- Replaced :attr:`.IncomingPacketBundle.interface_id` ``bytes``
  with :attr:`~.IncomingPacketBundle.interface_name` ``str``,
  providing :attr:`~.IncomingPacketBundle.interface_id` for backwards compatibility.
- Added :attr:`~.TransactionBundle.relays` property to more easily enumerate all the relays a message went through.
- Moved responsibility of creating the :class:`.TransactionBundle` from the :class:`.MessageHandler` to :mod:`.worker`.
  It gives a cleaner API and helps with statistics counting.
- Added :mod:`.statistics` and updated :mod:`.worker` and :class:`.MessageHandler` to update relevant counters.


0.9.0 - 2016-07-16
------------------

- A complete rewrite of the DHCPv6 server with a new configuration style.
