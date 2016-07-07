.. _static-sqlite:

Static-sqlite
=============

This section specifies that clients get their address and/or prefix assigned based on the contents of a
SQLite database. The filename of the database is given as the name of the section. Relative paths are
resolved relative to the configuration file.

The main advantages of using a SQLite database instead of a CSV file are:

- The CSV implementation reads all assignments into memory on startup, the SQLite implementation doesn't
- The SQLite file can be modified while the server is running, and the changes are used without the need to
  restart the server.

The SQLite database needs to have a table called ``assignments`` with TEXT columns ``id``, ``address`` and
``prefix``. Their contents use the same structure as the corresponding columns in the
:ref:`CSV file <csv-file-structure>`.

The `ipv6-dhcp-build-sqlite` command can be used to convert a CSV file into the right SQLite database
format.


Example
-------

.. code-block:: dhcpkitconf

    <static-sqlite data/assignments.sqlite>
        address-preferred-lifetime 1d
        address-valid-lifetime 7d
        prefix-preferred-lifetime 3d
        prefix-valid-lifetime 30d
    </static-csv>

.. _static-sqlite_parameters:

Section parameters
------------------

address-preferred-lifetime
    The preferred lifetime of assigned addresses. This is the time that the client should use it as the
    source address for new connections. After the preferred lifetime expires the address remains valid but
    becomes deprecated.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "7d"

address-valid-lifetime
    The valid lifetime of assigned addresses. After this lifetime expires the client is no longer allowed
    to use the assigned address.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "30d"

prefix-preferred-lifetime
    The preferred lifetime of assigned prefixes. This is the time that the client router should use as a
    preferred lifetime value when advertising prefixes to its clients.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "7d"

prefix-valid-lifetime
    The valid lifetime of assigned prefixes. This is the time that the client router should use as a
    valid lifetime value when advertising prefixes to its clients.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "30d"

